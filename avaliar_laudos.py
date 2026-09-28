"""Valida e compara a extração feita com IA pela interface, sem chamadas à API."""

import json
import math
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path


PASTA_PROJETO = Path(__file__).resolve().parent
PASTA_LAUDOS = PASTA_PROJETO / "laudos_avaliacao"
ARQUIVO_ESQUEMA = PASTA_PROJETO / "esquema_laudos.json"
ARQUIVO_REFERENCIA = PASTA_PROJETO / "referencia_laudos.json"
ARQUIVO_EXTRAIDO = PASTA_PROJETO / "saida" / "laudos_extraidos.json"
ARQUIVO_AVISOS = PASTA_PROJETO / "saida" / "avisos_laudos.json"
ARQUIVO_AVALIACAO = PASTA_PROJETO / "saida" / "avaliacao_extracao.json"


def ler_json(caminho):
    with caminho.open("r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def validar_contra_esquema(valor, regra, esquema, caminho="$", problemas=None):
    """Validador pequeno para os recursos usados no esquema deste projeto."""
    if problemas is None:
        problemas = []
    if "$ref" in regra:
        nome = regra["$ref"].rsplit("/", 1)[-1]
        validar_contra_esquema(valor, esquema["$defs"][nome], esquema, caminho, problemas)
        return problemas

    tipos = regra.get("type")
    if tipos:
        tipos = tipos if isinstance(tipos, list) else [tipos]
        verificadores = {
            "object": lambda v: isinstance(v, dict),
            "array": lambda v: isinstance(v, list),
            "string": lambda v: isinstance(v, str),
            "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
            "null": lambda v: v is None,
            "boolean": lambda v: isinstance(v, bool),
        }
        if not any(verificadores[tipo](valor) for tipo in tipos):
            problemas.append(f"{caminho}: tipo inválido; esperado {tipos}.")
            return problemas

    if "enum" in regra and valor not in regra["enum"]:
        problemas.append(f"{caminho}: valor fora da lista permitida: {valor!r}.")
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        minimo = regra.get("minimum")
        if minimo is not None and valor < minimo:
            problemas.append(f"{caminho}: valor abaixo do mínimo {minimo}.")
    if regra.get("format") == "date" and isinstance(valor, str):
        try:
            date.fromisoformat(valor)
        except ValueError:
            problemas.append(f"{caminho}: data fora do formato AAAA-MM-DD.")

    if isinstance(valor, dict) and "properties" in regra:
        propriedades = regra["properties"]
        for obrigatorio in regra.get("required", []):
            if obrigatorio not in valor:
                problemas.append(f"{caminho}.{obrigatorio}: campo obrigatório ausente.")
        if regra.get("additionalProperties") is False:
            for chave in valor.keys() - propriedades.keys():
                problemas.append(f"{caminho}.{chave}: campo não previsto no esquema.")
        for chave, conteudo in valor.items():
            if chave in propriedades:
                validar_contra_esquema(
                    conteudo, propriedades[chave], esquema, f"{caminho}.{chave}", problemas
                )
    if isinstance(valor, list) and "items" in regra:
        for indice, conteudo in enumerate(valor):
            validar_contra_esquema(
                conteudo, regra["items"], esquema, f"{caminho}[{indice}]", problemas
            )
    return problemas


def normalizar_texto(valor):
    texto = unicodedata.normalize("NFKD", str(valor).casefold())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = "".join(c if c.isalnum() else " " for c in texto)
    return " ".join(texto.split())


def valores_comparaveis(registro):
    """Compara conteúdo e status; evidências são verificadas literalmente à parte."""
    campos = {
        "tipo_imovel": registro["tipo_imovel"],
        "endereco": registro["endereco"],
        "ano_construcao": registro["ano_construcao"],
        "matricula": registro["matricula"],
        "data_vistoria": registro["data_vistoria"],
    }
    for nome, campo in registro["areas"].items():
        campos[f"areas.{nome}"] = campo

    comparaveis = {}
    for nome, campo in campos.items():
        comparaveis[f"{nome}.valor"] = campo.get("valor")
        comparaveis[f"{nome}.status"] = campo.get("status")

    valor = registro["valor_avaliacao_brl"]
    comparaveis["valor_avaliacao_brl.valor"] = valor.get("valor")
    comparaveis["valor_avaliacao_brl.status"] = valor.get("status")
    onus = registro["onus"]
    comparaveis["onus.classificacao"] = onus.get("classificacao")
    responsavel = registro["responsavel_tecnico"]
    comparaveis["responsavel_tecnico.nome"] = responsavel.get("nome")
    comparaveis["responsavel_tecnico.registro_profissional"] = responsavel.get(
        "registro_profissional"
    )
    comparaveis["responsavel_tecnico.status"] = responsavel.get("status")
    return comparaveis


def valores_iguais(esperado, obtido):
    if esperado is None or obtido is None:
        return esperado is obtido
    if isinstance(esperado, (int, float)) and not isinstance(esperado, bool):
        return isinstance(obtido, (int, float)) and not isinstance(obtido, bool) and math.isclose(
            esperado, obtido, rel_tol=0, abs_tol=0.01
        )
    return normalizar_texto(esperado) == normalizar_texto(obtido)


def coletar_evidencias(valor, caminho="$", saida=None):
    if saida is None:
        saida = []
    if isinstance(valor, dict):
        for chave, conteudo in valor.items():
            if chave == "evidencias" and isinstance(conteudo, list):
                saida.extend((f"{caminho}.{chave}", trecho) for trecho in conteudo)
            else:
                coletar_evidencias(conteudo, f"{caminho}.{chave}", saida)
    elif isinstance(valor, list):
        for indice, conteudo in enumerate(valor):
            coletar_evidencias(conteudo, f"{caminho}[{indice}]", saida)
    return saida


def main():
    necessarios = (ARQUIVO_ESQUEMA, ARQUIVO_REFERENCIA, ARQUIVO_EXTRAIDO)
    ausentes = [str(caminho) for caminho in necessarios if not caminho.exists()]
    if ausentes:
        raise SystemExit("Arquivos necessários ausentes: " + ", ".join(ausentes))

    esquema = ler_json(ARQUIVO_ESQUEMA)
    referencia_lista = ler_json(ARQUIVO_REFERENCIA)
    extraidos_lista = ler_json(ARQUIVO_EXTRAIDO)
    if not isinstance(extraidos_lista, list) or not extraidos_lista:
        raise SystemExit(
            "Nenhum resultado encontrado. Gere o prompt, use a interface de IA e salve "
            "o array JSON em saida/laudos_extraidos.json."
        )

    avisos = []
    nomes = [item.get("arquivo_origem") for item in extraidos_lista if isinstance(item, dict)]
    duplicados = sorted({nome for nome in nomes if nomes.count(nome) > 1})
    if duplicados:
        avisos.append({"tipo": "arquivos_duplicados", "arquivos": duplicados})

    problemas = []
    for indice, registro in enumerate(extraidos_lista):
        problemas.extend(
            validar_contra_esquema(registro, esquema, esquema, f"resultado[{indice}]")
        )

    referencia = {item["arquivo_origem"]: item for item in referencia_lista}
    extraidos = {
        item["arquivo_origem"]: item
        for item in extraidos_lista
        if isinstance(item, dict) and isinstance(item.get("arquivo_origem"), str)
    }
    fontes = {
        caminho.name: caminho.read_text(encoding="utf-8")
        for caminho in PASTA_LAUDOS.glob("laudo_*.txt")
    }
    fontes = {nome: texto for nome, texto in fontes.items() if nome in extraidos}

    for nome, registro in extraidos.items():
        if nome not in fontes:
            problemas.append(f"{nome}: não corresponde a um arquivo de laudo existente.")
            continue
        for caminho, trecho in coletar_evidencias(registro):
            if trecho and trecho not in fontes[nome]:
                avisos.append(
                    {
                        "tipo": "evidencia_nao_localizada",
                        "arquivo": nome,
                        "campo": caminho,
                        "evidencia": trecho,
                    }
                )

    if problemas:
        ARQUIVO_AVISOS.write_text(
            json.dumps(problemas, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        raise SystemExit(
            f"A saída não passou pela validação do esquema ({len(problemas)} problema(s)). "
            f"Veja {ARQUIVO_AVISOS}."
        )

    por_campo = defaultdict(lambda: {"corretos": 0, "comparados": 0})
    divergencias = []
    for nome, esperado in referencia.items():
        obtido = extraidos.get(nome)
        if obtido is None:
            divergencias.append({"arquivo": nome, "erro": "Laudo sem resultado da IA."})
            continue
        esperados = valores_comparaveis(esperado)
        encontrados = valores_comparaveis(obtido)
        for campo, valor_esperado in esperados.items():
            valor_obtido = encontrados.get(campo)
            contagem = por_campo[campo]
            contagem["comparados"] += 1
            if valores_iguais(valor_esperado, valor_obtido):
                contagem["corretos"] += 1
            else:
                divergencias.append(
                    {
                        "arquivo": nome,
                        "campo": campo,
                        "esperado": valor_esperado,
                        "extraido": valor_obtido,
                    }
                )

    corretos = sum(item["corretos"] for item in por_campo.values())
    comparados = sum(item["comparados"] for item in por_campo.values())
    resultado = {
        "status_referencia": "provisoria_requer_revisao_humana",
        "documentos_referencia": len(referencia),
        "documentos_extraidos": len(extraidos),
        "documentos_comparados": sum(nome in extraidos for nome in referencia),
        "campos_corretos": corretos,
        "campos_comparados": comparados,
        "concordancia_normalizada": corretos / comparados if comparados else None,
        "por_campo": {
            campo: {
                **contagem,
                "concordancia": contagem["corretos"] / contagem["comparados"],
            }
            for campo, contagem in sorted(por_campo.items())
        },
        "divergencias": divergencias,
        "avisos_de_evidencia": avisos,
        "observacao": (
            "Concordância provisória porque a referência ainda precisa de validação humana. "
            "A métrica compara valores e status, normaliza acentos/caixa/pontuação e aceita "
            "diferenças numéricas até 0,01. Evidências são checadas literalmente; a métrica "
            "não julga a qualidade semântica das justificativas."
        ),
    }
    ARQUIVO_AVALIACAO.write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    ARQUIVO_AVISOS.write_text(
        json.dumps(avisos, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Concordância provisória: {corretos}/{comparados} valores e status")
    print(f"Documentos comparados: {resultado['documentos_comparados']}/{len(referencia)}")
    print(f"Detalhes: {ARQUIVO_AVALIACAO}")
    if avisos:
        print(f"Avisos de evidência: {len(avisos)} (consulte {ARQUIVO_AVISOS})")


if __name__ == "__main__":
    main()
