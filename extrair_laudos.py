"""Extrai campos dos laudos usando a API da OpenAI e o esquema do projeto."""

import json
import os
from pathlib import Path


PASTA_PROJETO = Path(__file__).resolve().parent
PASTA_LAUDOS = PASTA_PROJETO / "laudos_avaliacao"
ARQUIVO_ESQUEMA = PASTA_PROJETO / "esquema_laudos.json"
ARQUIVO_SAIDA = PASTA_PROJETO / "saida" / "laudos_extraidos.json"
ARQUIVO_AVISOS = PASTA_PROJETO / "saida" / "avisos_laudos.json"


def carregar_json(caminho):
    with caminho.open("r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def preparar_esquema_api(esquema):
    """Expande referências locais e remove metadados não necessários à API."""
    definicoes = esquema.get("$defs", {})

    def expandir(no):
        if isinstance(no, list):
            return [expandir(item) for item in no]
        if not isinstance(no, dict):
            return no

        if "$ref" in no:
            referencia = no["$ref"]
            prefixo = "#/$defs/"
            if not referencia.startswith(prefixo):
                raise ValueError(f"Referência de esquema não suportada: {referencia}")
            nome = referencia.removeprefix(prefixo)
            return expandir(definicoes[nome])

        resultado = {}
        for chave, valor in no.items():
            if chave in {"$schema", "$id", "$defs", "title", "description", "format", "minimum"}:
                continue
            resultado[chave] = expandir(valor)
        # JSON Schema permite enum sem declarar type; o formato estrito da API
        # fica mais explícito quando toda enumeração de texto declara string.
        if "enum" in resultado and "type" not in resultado:
            resultado["type"] = "string"
        return resultado

    resultado = expandir(esquema)
    resultado["additionalProperties"] = False
    return resultado


def evidencias_fora_do_texto(dados, texto):
    """Localiza evidências citadas pelo modelo que não aparecem no laudo."""
    avisos = []

    def percorrer(valor, caminho=""):
        if isinstance(valor, dict):
            for chave, conteudo in valor.items():
                caminho_atual = f"{caminho}.{chave}" if caminho else chave
                if chave == "evidencias" and isinstance(conteudo, list):
                    for evidencia in conteudo:
                        if evidencia and evidencia not in texto:
                            avisos.append({"campo": caminho_atual, "evidencia": evidencia})
                else:
                    percorrer(conteudo, caminho_atual)
        elif isinstance(valor, list):
            for indice, item in enumerate(valor):
                percorrer(item, f"{caminho}[{indice}]")

    percorrer(dados)
    return avisos


def salvar_json(caminho, conteudo):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_suffix(caminho.suffix + ".tmp")
    temporario.write_text(
        json.dumps(conteudo, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporario.replace(caminho)


def main():
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit(
            "Configure OPENAI_API_KEY no terminal antes de executar. "
            "A chave não deve ser colocada no código nem enviada ao Git."
        )

    try:
        from openai import OpenAI
    except ImportError as erro:
        raise SystemExit(
            "Pacote ausente. No ambiente virtual do projeto, execute: "
            "python -m pip install openai"
        ) from erro

    modelo = os.environ.get("OPENAI_MODEL", "gpt-6-astra")
    esquema = preparar_esquema_api(carregar_json(ARQUIVO_ESQUEMA))
    arquivos = sorted(PASTA_LAUDOS.glob("laudo_*.txt"))
    if not arquivos:
        raise SystemExit(f"Nenhum arquivo laudo_*.txt encontrado em {PASTA_LAUDOS}")

    cliente = OpenAI()
    resultados = []
    avisos = []
    instrucao = (
        "Extraia dos laudos imobiliários somente informações explícitas no texto. "
        "Não complete lacunas com conhecimento externo nem deduza valores. "
        "Use status ausente quando o campo não estiver informado, nao_aplicavel "
        "quando o texto disser que não se aplica, ambiguo quando não der para "
        "determinar um único valor e conflitante quando o próprio laudo trouxer "
        "informações incompatíveis. Para cada valor encontrado, copie em evidencias "
        "um trecho literal curto do laudo. Converta valores monetários para número "
        "em reais e datas para AAAA-MM-DD. Não classifique ausência de menção como "
        "certidão sem ônus. Responda no formato JSON exigido pelo esquema."
    )

    for indice, caminho in enumerate(arquivos, start=1):
        texto = caminho.read_text(encoding="utf-8")
        try:
            resposta = cliente.responses.create(
                model=modelo,
                store=False,
                input=[
                    {"role": "system", "content": instrucao},
                    {
                        "role": "user",
                        "content": f"Arquivo de origem: {caminho.name}\n\nLaudo:\n{texto}",
                    },
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "laudo_imobiliario",
                        "strict": True,
                        "schema": esquema,
                    }
                }
            )
        except Exception as erro:
            avisos.append(
                {
                    "arquivo": caminho.name,
                    "erro_api": f"{type(erro).__name__}: {erro}",
                }
            )
            salvar_json(ARQUIVO_SAIDA, resultados)
            salvar_json(ARQUIVO_AVISOS, avisos)
            print(f"[{indice}/{len(arquivos)}] Falha na chamada: {caminho.name}")
            continue

        if not resposta.output_text:
            avisos.append({"arquivo": caminho.name, "erro": "A API não retornou conteúdo estruturado."})
            salvar_json(ARQUIVO_SAIDA, resultados)
            salvar_json(ARQUIVO_AVISOS, avisos)
            print(f"[{indice}/{len(arquivos)}] Sem resultado: {caminho.name}")
            continue

        try:
            dados = json.loads(resposta.output_text)
        except json.JSONDecodeError:
            avisos.append({"arquivo": caminho.name, "erro": "A resposta não pôde ser lida como JSON."})
            salvar_json(ARQUIVO_SAIDA, resultados)
            salvar_json(ARQUIVO_AVISOS, avisos)
            print(f"[{indice}/{len(arquivos)}] Resposta inválida: {caminho.name}")
            continue
        # O nome vem do próprio arquivo local, não de uma inferência do modelo.
        dados["arquivo_origem"] = caminho.name
        resultados.append(dados)

        evidencias_invalidas = evidencias_fora_do_texto(dados, texto)
        if evidencias_invalidas:
            avisos.append(
                {
                    "arquivo": caminho.name,
                    "evidencias_nao_localizadas": evidencias_invalidas,
                }
            )

        # Persiste após cada chamada para não perder resultados já cobrados.
        salvar_json(ARQUIVO_SAIDA, resultados)
        salvar_json(ARQUIVO_AVISOS, avisos)
        print(f"[{indice}/{len(arquivos)}] Extraído: {caminho.name}")

    print(f"Resultados: {ARQUIVO_SAIDA}")
    print(f"Avisos: {ARQUIVO_AVISOS}")
    print("A saída precisa ser comparada à referência humana; formato válido não garante acerto factual.")


if __name__ == "__main__":
    main()
