"""Compara a extração da API com a referência manual, campo a campo."""

import json
import math
import unicodedata
from collections import defaultdict
from pathlib import Path


PASTA_PROJETO = Path(__file__).resolve().parent
ARQUIVO_REFERENCIA = PASTA_PROJETO / "referencia_laudos.json"
ARQUIVO_EXTRAIDO = PASTA_PROJETO / "saida" / "laudos_extraidos.json"
ARQUIVO_AVALIACAO = PASTA_PROJETO / "saida" / "avaliacao_extracao.json"


def ler_json(caminho):
    with caminho.open("r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def normalizar_texto(valor):
    texto = unicodedata.normalize("NFKD", str(valor).casefold())
    texto = "".join(caractere for caractere in texto if not unicodedata.combining(caractere))
    caracteres = [caractere if caractere.isalnum() else " " for caractere in texto]
    return " ".join("".join(caracteres).split())


def valores_comparaveis(registro):
    """Retorna somente valores e classificações; evidência e observação são revisadas à parte."""
    campos = {
        "tipo_imovel": registro["tipo_imovel"],
        "endereco": registro["endereco"],
        "ano_construcao": registro["ano_construcao"],
        "matricula": registro["matricula"],
        "data_vistoria": registro["data_vistoria"],
    }
    for nome_area, campo in registro["areas"].items():
        campos[f"areas.{nome_area}"] = campo

    comparaveis = {}
    for nome, campo in campos.items():
        comparaveis[f"{nome}.valor"] = campo.get("valor")
        comparaveis[f"{nome}.status"] = campo.get("status")

    valor = registro["valor_avaliacao_brl"]
    comparaveis["valor_avaliacao_brl.valor"] = valor.get("valor")
    comparaveis["valor_avaliacao_brl.rotulo_no_laudo"] = valor.get("rotulo_no_laudo")
    comparaveis["valor_avaliacao_brl.status"] = valor.get("status")

    onus = registro["onus"]
    comparaveis["onus.classificacao"] = onus.get("classificacao")
    comparaveis["onus.descricao"] = onus.get("descricao")

    responsavel = registro["responsavel_tecnico"]
    comparaveis["responsavel_tecnico.nome"] = responsavel.get("nome")
    comparaveis["responsavel_tecnico.registro_profissional"] = responsavel.get(
        "registro_profissional"
    )
    comparaveis["responsavel_tecnico.status"] = responsavel.get("status")
    return comparaveis


def iguais(esperado, encontrado):
    if esperado is None or encontrado is None:
        return esperado is encontrado
    if isinstance(esperado, (int, float)) and not isinstance(esperado, bool):
        if not isinstance(encontrado, (int, float)) or isinstance(encontrado, bool):
            return False
        return math.isclose(esperado, encontrado, rel_tol=0, abs_tol=0.01)
    return normalizar_texto(esperado) == normalizar_texto(encontrado)


def main():
    if not ARQUIVO_REFERENCIA.exists() or not ARQUIVO_EXTRAIDO.exists():
        raise SystemExit(
            "Não encontrei a referência ou a extração. Execute extrair_laudos.py "
            "antes de avaliar."
        )

    referencia = {item["arquivo_origem"]: item for item in ler_json(ARQUIVO_REFERENCIA)}
    extraidos = {item["arquivo_origem"]: item for item in ler_json(ARQUIVO_EXTRAIDO)}
    por_campo = defaultdict(lambda: {"corretos": 0, "comparados": 0})
    divergencias = []
    documentos_comparados = 0

    for arquivo, esperado in referencia.items():
        encontrado = extraidos.get(arquivo)
        if encontrado is None:
            divergencias.append({"arquivo": arquivo, "erro": "Laudo sem resultado da extração."})
            continue

        documentos_comparados += 1
        esperados = valores_comparaveis(esperado)
        obtidos = valores_comparaveis(encontrado)
        for campo, valor_esperado in esperados.items():
            valor_encontrado = obtidos.get(campo)
            resultado = por_campo[campo]
            resultado["comparados"] += 1
            if iguais(valor_esperado, valor_encontrado):
                resultado["corretos"] += 1
            else:
                divergencias.append(
                    {
                        "arquivo": arquivo,
                        "campo": campo,
                        "esperado": valor_esperado,
                        "extraido": valor_encontrado,
                    }
                )

    total_corretos = sum(item["corretos"] for item in por_campo.values())
    total_comparados = sum(item["comparados"] for item in por_campo.values())
    resultado = {
        "documentos_referencia": len(referencia),
        "documentos_extraidos": len(extraidos),
        "documentos_comparados": documentos_comparados,
        "campos_corretos": total_corretos,
        "campos_comparados": total_comparados,
        "acuracia_exata_normalizada": (
            total_corretos / total_comparados if total_comparados else None
        ),
        "por_campo": {
            campo: {
                **contagem,
                "acuracia": (
                    contagem["corretos"] / contagem["comparados"]
                    if contagem["comparados"]
                    else None
                ),
            }
            for campo, contagem in sorted(por_campo.items())
        },
        "divergencias": divergencias,
        "observacao": (
            "A comparação normaliza acentos, caixa e pontuação para texto e tolera "
            "diferenças numéricas até 0,01. Ela mede igualdade de campos, não avalia "
            "se evidências e observações estão bem justificadas."
        ),
    }

    ARQUIVO_AVALIACAO.parent.mkdir(parents=True, exist_ok=True)
    ARQUIVO_AVALIACAO.write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if total_comparados:
        print(f"Acurácia normalizada: {total_corretos}/{total_comparados} campos")
    else:
        print("Nenhum campo pôde ser comparado.")
    print(f"Documentos comparados: {documentos_comparados}/{len(referencia)}")
    print(f"Detalhes: {ARQUIVO_AVALIACAO}")


if __name__ == "__main__":
    main()
