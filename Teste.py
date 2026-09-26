"""Desafio Bari: auditoria inicial e preparação da base de propostas.

Esta primeira versão cobre o começo da Parte 1. As métricas e o relatório
serão acrescentados depois que as regras de tratamento estiverem claras.
"""

from pathlib import Path
from datetime import datetime
import logging

import pandas as pd


# O caminho é relativo ao local do próprio script. Assim, o projeto pode ser
# movido para outro computador sem precisar alterar um caminho absoluto.
PASTA_PROJETO = Path(__file__).resolve().parent
ARQUIVO_CSV = PASTA_PROJETO / "propostas_credito.csv"
PASTA_SAIDA = PASTA_PROJETO / "saida"
ARQUIVO_RELATORIO = PASTA_SAIDA / "relatorio_funil.html"
ARQUIVO_LOG = PASTA_SAIDA / "execucao.log"
# Alerta operacional para taxas com poucos casos; não é um teste estatístico.
MINIMO_PROPOSTAS_ALERTA_SEMANAL = 30

# O enunciado manda retirar Terreno antes de realizar a análise do CSV.
COLUNAS_OBRIGATORIAS = {
    "id_proposta",
    "data_entrada",
    "canal_origem",
    "tipo_imovel",
    "valor_imovel",
    "valor_solicitado",
    "score_credito",
    "etapa_max_funil",
    "status_final",
    "uf",
    "consultor_id",
}


def carregar_base(caminho: Path = ARQUIVO_CSV) -> pd.DataFrame:
    """Lê o CSV e interrompe com uma mensagem clara se faltar coluna essencial."""
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo de entrada não encontrado: {caminho}")

    # utf-8-sig também funciona para UTF-8 comum e remove eventual BOM do cabeçalho.
    dados = pd.read_csv(caminho, encoding="utf-8-sig", low_memory=False)
    colunas_ausentes = COLUNAS_OBRIGATORIAS - set(dados.columns)
    if colunas_ausentes:
        nomes = ", ".join(sorted(colunas_ausentes))
        raise ValueError(f"O CSV não contém as colunas obrigatórias: {nomes}")

    return dados


def configurar_log() -> logging.Logger:
    """Cria um log por execução, salvo na pasta de saída do projeto."""
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("relatorio_funil")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formato = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    arquivo = logging.FileHandler(ARQUIVO_LOG, encoding="utf-8")
    arquivo.setFormatter(formato)
    console = logging.StreamHandler()
    console.setFormatter(formato)
    logger.addHandler(arquivo)
    logger.addHandler(console)
    return logger


def preparar_base(dados: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Padroniza campos usados na análise e aplica a exclusão de Terreno."""
    base = dados.copy()

    # A coluna contém três valores com prefixo "R$". Removemos apenas o prefixo
    # e convertemos o restante para número; valores impossíveis viram ausentes.
    valor_imovel_original = base["valor_imovel"].astype("string")
    valor_imovel_limpo = valor_imovel_original.str.replace(r"^\s*R\$\s*", "", regex=True)
    base["valor_imovel"] = pd.to_numeric(valor_imovel_limpo, errors="coerce")
    valores_imovel_invalidos = int(base["valor_imovel"].isna().sum())

    # Há datas ISO e três datas no formato brasileiro dd/mm/aaaa.
    base["data_entrada"] = pd.to_datetime(
        base["data_entrada"], format="mixed", dayfirst=True, errors="coerce"
    )
    datas_invalidas = int(base["data_entrada"].isna().sum())

    # Padronizamos espaços, caixa e grafia para não contar variações do mesmo canal
    # como categorias diferentes. Ex.: "mídia paga " e "Mídia paga".
    canal_original = base["canal_origem"].astype("string")
    canal_chave = canal_original.str.strip().str.casefold()
    nomes_canais = {
        "correspondente": "Correspondente",
        "organico": "Orgânico",
        "orgânico": "Orgânico",
        "mídia paga": "Mídia paga",
        "indicação": "Indicação",
        "parceria": "Parceria",
    }
    base["canal_origem"] = canal_chave.map(nomes_canais).fillna(canal_original.str.strip())

    # O dicionário menciona LTV, mas a coluna não veio no CSV. Calculamos a razão
    # entre o valor solicitado e o valor do imóvel e deixamos como proporção.
    base["ltv"] = base["valor_solicitado"] / base["valor_imovel"]

    # A exclusão de Terreno é uma regra explícita do enunciado. Preservamos a
    # contagem removida para documentar e explicar seu efeito na análise.
    terrenos_removidos = int(base["tipo_imovel"].str.strip().str.casefold().eq("terreno").sum())
    base_analise = base.loc[
        ~base["tipo_imovel"].str.strip().str.casefold().eq("terreno")
    ].copy()

    auditoria = {
        "linhas_originais": len(dados),
        "terrenos_removidos": terrenos_removidos,
        "linhas_para_analise": len(base_analise),
        "categorias_canal_antes": int(canal_original.nunique()),
        "categorias_canal_depois": int(base["canal_origem"].nunique()),
        "ids_duplicados": int(base_analise["id_proposta"].duplicated().sum()),
        "valores_imovel_invalidos": valores_imovel_invalidos,
        "datas_entrada_invalidas": datas_invalidas,
        "etapas_fora_de_1_a_6": int((~base_analise["etapa_max_funil"].between(1, 6)).sum()),
    }
    return base_analise, auditoria


def calcular_metricas(base: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Monta três tabelas para investigar perdas, canais e evolução mensal."""
    nao_contratadas = base.loc[base["status_final"] != "Contratada"].copy()

    # Uma proposta aparece em apenas uma etapa: a última que alcançou.
    # Somamos o crédito solicitado das propostas não contratadas nessa etapa.
    perdas_por_etapa = (
        nao_contratadas.groupby("etapa_max_funil", as_index=False)
        .agg(
            propostas_perdidas=("id_proposta", "count"),
            valor_solicitado_potencial=("valor_solicitado", "sum"),
        )
        .sort_values("etapa_max_funil")
    )
    perdas_por_etapa_status = (
        nao_contratadas.groupby(["etapa_max_funil", "status_final"], as_index=False)
        .agg(
            propostas_perdidas=("id_proposta", "count"),
            valor_solicitado_potencial=("valor_solicitado", "sum"),
        )
        .sort_values(["etapa_max_funil", "valor_solicitado_potencial"], ascending=[True, False])
    )

    desempenho_canais = (
        base.assign(contratada=base["status_final"].eq("Contratada"))
        .groupby("canal_origem", as_index=False)
        .agg(
            propostas=("id_proposta", "count"),
            contratadas=("contratada", "sum"),
            taxa_contratacao=("contratada", "mean"),
        )
        .sort_values("taxa_contratacao", ascending=False)
    )

    # A coorte é definida pelo mês de entrada. A taxa compara quantas propostas
    # daquele mês terminaram contratadas com o total que entrou naquele mês.
    base_com_mes = base.assign(mes_entrada=base["data_entrada"].dt.to_period("M"))
    contratacao_mensal = (
        base_com_mes.assign(contratada=base_com_mes["status_final"].eq("Contratada"))
        .groupby("mes_entrada", as_index=False)
        .agg(
            propostas=("id_proposta", "count"),
            contratadas=("contratada", "sum"),
            taxa_contratacao=("contratada", "mean"),
        )
    )

    # Uma comparação por ano resume o movimento sem depender de um mês isolado.
    base_com_ano = base.assign(ano_entrada=base["data_entrada"].dt.year)
    contratacao_anual = (
        base_com_ano.assign(contratada=base_com_ano["status_final"].eq("Contratada"))
        .groupby("ano_entrada", as_index=False)
        .agg(
            propostas=("id_proposta", "count"),
            contratadas=("contratada", "sum"),
            taxa_contratacao=("contratada", "mean"),
        )
    )

    # O arquivo do desafio é histórico. Ancoramos a janela móvel de sete dias
    # na data mais recente presente nele, e não na data do computador, para que
    # o relatório continue útil quando for demonstrado com esta base sintética.
    data_final_arquivo = base["data_entrada"].max().normalize()
    inicio_semana_atual = data_final_arquivo - pd.Timedelta(days=6)
    fim_semana_anterior = inicio_semana_atual - pd.Timedelta(days=1)
    inicio_semana_anterior = fim_semana_anterior - pd.Timedelta(days=6)

    def resumir_janela(inicio: pd.Timestamp, fim: pd.Timestamp, nome: str) -> dict:
        propostas_janela = base.loc[
            base["data_entrada"].between(inicio, fim + pd.Timedelta(days=1), inclusive="left")
        ]
        contratadas_janela = propostas_janela["status_final"].eq("Contratada").sum()
        nao_contratadas_janela = propostas_janela.loc[
            propostas_janela["status_final"] != "Contratada"
        ]
        quantidade = len(propostas_janela)
        return {
            "janela": nome,
            "periodo": f"{inicio:%d/%m/%Y} a {fim:%d/%m/%Y}",
            "propostas": quantidade,
            "contratadas": int(contratadas_janela),
            "taxa_contratacao": contratadas_janela / quantidade if quantidade else 0,
            "valor_solicitado_nao_contratado": nao_contratadas_janela["valor_solicitado"].sum(),
            "observacao": (
                f"Volume baixo: apenas {quantidade} propostas; taxa instável."
                if quantidade < MINIMO_PROPOSTAS_ALERTA_SEMANAL
                else ""
            ),
        }

    resumo_semanal = pd.DataFrame(
        [
            resumir_janela(inicio_semana_anterior, fim_semana_anterior, "7 dias anteriores"),
            resumir_janela(inicio_semana_atual, data_final_arquivo, "7 dias mais recentes no arquivo"),
        ]
    )

    # Criamos faixas para comparar perfis. Os quartis são definidos pela própria
    # distribuição dos dados; as faixas de LTV usam o limite de 60% citado no desafio.
    base_perfis = base.copy()
    base_perfis["faixa_ltv"] = pd.cut(
        base_perfis["ltv"],
        bins=[float("-inf"), 0.30, 0.40, 0.50, 0.60, float("inf")],
        labels=["Até 30%", "30% a 40%", "40% a 50%", "50% a 60%", "Acima de 60%"],
    )
    base_perfis["faixa_score"] = pd.qcut(
        base_perfis["score_credito"], q=4, duplicates="drop"
    )
    base_perfis["faixa_valor_solicitado"] = pd.qcut(
        base_perfis["valor_solicitado"], q=4, duplicates="drop"
    )

    def resumir_perfil(coluna: str) -> pd.DataFrame:
        """Resume volume e contratação de cada grupo para comparação descritiva."""
        return (
            base_perfis.assign(contratada=base_perfis["status_final"].eq("Contratada"))
            .groupby(coluna, observed=True, as_index=False)
            .agg(
                propostas=("id_proposta", "count"),
                contratadas=("contratada", "sum"),
                taxa_contratacao=("contratada", "mean"),
            )
        )

    associacoes = {
        "contratacao_por_ltv": resumir_perfil("faixa_ltv"),
        "contratacao_por_imovel": resumir_perfil("tipo_imovel"),
        "contratacao_por_score": resumir_perfil("faixa_score"),
        "contratacao_por_ticket": resumir_perfil("faixa_valor_solicitado"),
        "contratacao_por_uf": resumir_perfil("uf"),
        "contratacao_por_consultor": resumir_perfil("consultor_id"),
    }
    propostas_acima_limite_ltv = base.loc[base["ltv"] > 0.60]
    contratadas_acima_limite_ltv = propostas_acima_limite_ltv.loc[
        propostas_acima_limite_ltv["status_final"].eq("Contratada")
    ]

    correspondentes = base.loc[base["canal_origem"].eq("Correspondente")]
    outros_canais = base.loc[base["canal_origem"].ne("Correspondente")]
    taxa_correspondentes = correspondentes["status_final"].eq("Contratada").mean()
    taxa_outros_canais = outros_canais["status_final"].eq("Contratada").mean()
    contratos_adicionais_cenario = max(
        0,
        len(correspondentes) * taxa_outros_canais
        - correspondentes["status_final"].eq("Contratada").sum(),
    )

    perdas_etapa_3_sem_retorno = nao_contratadas.loc[
        nao_contratadas["etapa_max_funil"].eq(3)
        & nao_contratadas["status_final"].eq("Sem retorno")
    ]
    meta_reengajamento_sem_retorno = 0.10  # hipótese para dimensionar um piloto

    # Comparar canais dentro da mesma faixa de LTV ajuda a verificar se a
    # diferença bruta entre canais é explicada apenas pelo perfil de garantia.
    contratacao_canal_ltv = (
        base_perfis.assign(contratada=base_perfis["status_final"].eq("Contratada"))
        .groupby(["canal_origem", "faixa_ltv"], observed=True, as_index=False)
        .agg(
            propostas=("id_proposta", "count"),
            contratadas=("contratada", "sum"),
            taxa_contratacao=("contratada", "mean"),
        )
        .sort_values(["faixa_ltv", "taxa_contratacao"], ascending=[True, False])
    )
    contratacao_canal_score = (
        base_perfis.assign(contratada=base_perfis["status_final"].eq("Contratada"))
        .groupby(["canal_origem", "faixa_score"], observed=True, as_index=False)
        .agg(
            propostas=("id_proposta", "count"),
            contratadas=("contratada", "sum"),
            taxa_contratacao=("contratada", "mean"),
        )
        .sort_values(["faixa_score", "taxa_contratacao"], ascending=[True, False])
    )
    # Mostra como os desfechos se distribuem dentro de cada canal. Normalize
    # por linha para comparar canais de tamanhos diferentes.
    status_por_canal = pd.crosstab(
        base["canal_origem"], base["status_final"], normalize="index"
    ).mul(100).round(1)

    # Compara correspondentes e outros canais atendidos pelo mesmo consultor.
    # Exigimos pelo menos 20 propostas em cada grupo antes de exibir a comparação.
    contratada = base["status_final"].eq("Contratada")
    eh_correspondente = base["canal_origem"].eq("Correspondente")
    por_consultor_correspondente = (
        base.loc[eh_correspondente]
        .assign(contratada=contratada.loc[eh_correspondente])
        .groupby("consultor_id", as_index=False)
        .agg(
            propostas_correspondente=("id_proposta", "count"),
            contratos_correspondente=("contratada", "sum"),
        )
    )
    por_consultor_outros = (
        base.loc[~eh_correspondente]
        .assign(contratada=contratada.loc[~eh_correspondente])
        .groupby("consultor_id", as_index=False)
        .agg(
            propostas_outros_canais=("id_proposta", "count"),
            contratos_outros_canais=("contratada", "sum"),
        )
    )
    comparacao_por_consultor = por_consultor_correspondente.merge(
        por_consultor_outros, on="consultor_id", how="inner"
    )
    comparacao_por_consultor["taxa_correspondente"] = (
        comparacao_por_consultor["contratos_correspondente"]
        / comparacao_por_consultor["propostas_correspondente"]
    )
    comparacao_por_consultor["taxa_outros_canais"] = (
        comparacao_por_consultor["contratos_outros_canais"]
        / comparacao_por_consultor["propostas_outros_canais"]
    )
    comparacao_por_consultor["diferenca_pontos_percentuais"] = (
        comparacao_por_consultor["taxa_correspondente"]
        - comparacao_por_consultor["taxa_outros_canais"]
    ) * 100
    comparacao_por_consultor = comparacao_por_consultor.loc[
        comparacao_por_consultor["propostas_correspondente"].ge(20)
        & comparacao_por_consultor["propostas_outros_canais"].ge(20)
    ].sort_values("diferenca_pontos_percentuais")

    return {
        "perdas_por_etapa": perdas_por_etapa,
        "perdas_por_etapa_status": perdas_por_etapa_status,
        "resumo_ltv_acima_limite": pd.DataFrame(
            {
                "propostas": [len(propostas_acima_limite_ltv)],
                "contratadas": [int(propostas_acima_limite_ltv["status_final"].eq("Contratada").sum())],
                "valor_solicitado_potencial": [propostas_acima_limite_ltv["valor_solicitado"].sum()],
                "valor_solicitado_contratado": [contratadas_acima_limite_ltv["valor_solicitado"].sum()],
            }
        ),
        "cenarios_recomendacoes": {
            "propostas_correspondente": len(correspondentes),
            "taxa_correspondente": taxa_correspondentes,
            "taxa_outros_canais": taxa_outros_canais,
            "contratos_adicionais_cenario": contratos_adicionais_cenario,
            "sem_retorno_etapa_3": len(perdas_etapa_3_sem_retorno),
            "valor_sem_retorno_etapa_3": perdas_etapa_3_sem_retorno["valor_solicitado"].sum(),
            "meta_reengajamento_sem_retorno": meta_reengajamento_sem_retorno,
            "propostas_reengajadas_cenario": round(
                len(perdas_etapa_3_sem_retorno) * meta_reengajamento_sem_retorno
            ),
            "valor_reengajado_cenario": (
                perdas_etapa_3_sem_retorno["valor_solicitado"].sum()
                * meta_reengajamento_sem_retorno
            ),
        },
        "desempenho_canais": desempenho_canais,
        "contratacao_mensal": contratacao_mensal,
        "contratacao_anual": contratacao_anual,
        "resumo_semanal": resumo_semanal,
        "contratacao_canal_ltv": contratacao_canal_ltv,
        "contratacao_canal_score": contratacao_canal_score,
        "status_por_canal": status_por_canal,
        "comparacao_por_consultor": comparacao_por_consultor,
        **associacoes,
    }


def exportar_relatorio_html(
    base: pd.DataFrame,
    auditoria: dict[str, int],
    metricas: dict[str, pd.DataFrame],
    caminho: Path = ARQUIVO_RELATORIO,
) -> None:
    """Gera um relatório HTML local com as métricas principais para a liderança."""
    total = len(base)
    contratos = int(base["status_final"].eq("Contratada").sum())
    taxa_geral = contratos / total if total else 0
    periodo = (
        f"{base['data_entrada'].min():%d/%m/%Y} a "
        f"{base['data_entrada'].max():%d/%m/%Y}"
    )
    resumo_auditoria = pd.DataFrame(
        {"Verificação": list(auditoria.keys()), "Quantidade": list(auditoria.values())}
    )

    tabelas_html = [
        "<h2>Auditoria da base</h2>" + resumo_auditoria.to_html(index=False, border=0),
        "<h2>Comparação semanal</h2>"
        + metricas["resumo_semanal"].to_html(
            index=False,
            border=0,
            formatters={
                "taxa_contratacao": "{:.1%}".format,
                "valor_solicitado_nao_contratado": "R$ {:,.2f}".format,
            },
        ),
        "<h2>Status das propostas</h2>"
        + base["status_final"].value_counts().rename_axis("status").reset_index(name="propostas").to_html(index=False, border=0),
        "<h2>Crédito solicitado potencial por última etapa</h2>"
        + metricas["perdas_por_etapa"].to_html(index=False, border=0, float_format=lambda valor: f"R$ {valor:,.2f}"),
        "<h2>Contratação por canal</h2>"
        + metricas["desempenho_canais"].to_html(
            index=False, border=0, formatters={"taxa_contratacao": "{:.1%}".format}
        ),
        "<h2>Contratação anual</h2>"
        + metricas["contratacao_anual"].to_html(
            index=False, border=0, formatters={"taxa_contratacao": "{:.1%}".format}
        ),
        "<h2>Contratação por LTV</h2>"
        + metricas["contratacao_por_ltv"].to_html(
            index=False, border=0, formatters={"taxa_contratacao": "{:.1%}".format}
        ),
        "<h2>Contratação por faixa de score</h2>"
        + metricas["contratacao_por_score"].to_html(
            index=False, border=0, formatters={"taxa_contratacao": "{:.1%}".format}
        ),
        "<h2>Distribuição dos desfechos por canal (%)</h2>"
        + metricas["status_por_canal"].to_html(border=0),
    ]

    documento = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Relatório do funil de crédito</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #20252b; max-width: 1100px; margin: 36px auto; padding: 0 20px; line-height: 1.5; }}
    h1, h2 {{ color: #153e5c; }}
    table {{ border-collapse: collapse; margin: 12px 0 28px; width: 100%; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid #d8dee4; padding: 8px 10px; text-align: left; }}
    th {{ background: #eef3f7; }}
    .nota {{ background: #fff8e6; padding: 12px 16px; border-left: 4px solid #d29b22; }}
    .destaque {{ font-size: 18px; font-weight: bold; }}
  </style>
</head>
<body>
  <h1>Relatório do funil de crédito</h1>
  <p>Período de entrada: {periodo} | Gerado em {datetime.now():%d/%m/%Y %H:%M}</p>
  <p class="destaque">{total:,} propostas analisadas | {contratos:,} contratos | conversão observada: {taxa_geral:.1%}</p>
  <p class="nota">O valor solicitado em propostas não contratadas é uma medida de crédito potencial associado às perdas, não receita ou lucro perdido. As comparações são descritivas e não demonstram causalidade.</p>
  {''.join(tabelas_html)}
</body>
</html>
"""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(documento, encoding="utf-8")


def main() -> None:
    """Executa a análise, registra a execução e exporta o relatório HTML."""
    logger = configurar_log()
    logger.info("Início do processamento do funil.")
    try:
        dados = carregar_base()
        base_analise, auditoria = preparar_base(dados)
    except (FileNotFoundError, ValueError, pd.errors.ParserError) as erro:
        logger.exception("Falha ao ler ou preparar o CSV: %s", erro)
        raise SystemExit(1) from erro

    metricas = calcular_metricas(base_analise)
    propostas_semana_mais_recente = int(metricas["resumo_semanal"].iloc[-1]["propostas"])
    if propostas_semana_mais_recente < MINIMO_PROPOSTAS_ALERTA_SEMANAL:
        logger.warning(
            "A janela mais recente tem apenas %s propostas; interprete a taxa semanal com cautela.",
            propostas_semana_mais_recente,
        )
    try:
        exportar_relatorio_html(base_analise, auditoria, metricas)
    except OSError as erro:
        logger.exception("Falha ao salvar o relatório HTML: %s", erro)
        raise SystemExit(1) from erro

    logger.info(
        "Auditoria concluída: %s linhas originais; %s para análise.",
        auditoria["linhas_originais"],
        auditoria["linhas_para_analise"],
    )
    if auditoria["valores_imovel_invalidos"]:
        logger.warning(
            "Existem %s valores de imóvel que não foram convertidos para número.",
            auditoria["valores_imovel_invalidos"],
        )
    if auditoria["datas_entrada_invalidas"]:
        logger.warning(
            "Existem %s datas de entrada que não foram interpretadas.",
            auditoria["datas_entrada_invalidas"],
        )
    if auditoria["etapas_fora_de_1_a_6"]:
        logger.warning(
            "Existem %s propostas com etapa fora do dicionário.",
            auditoria["etapas_fora_de_1_a_6"],
        )
    logger.info("Relatório HTML salvo em %s", ARQUIVO_RELATORIO)
    logger.info("Fim do processamento.")

    print("Auditoria inicial da base de propostas")
    for item, quantidade in auditoria.items():
        print(f"- {item.replace('_', ' ').capitalize()}: {quantidade}")

    print("\nPropostas por status após remover Terreno:")
    print(base_analise["status_final"].value_counts().to_string())

    print("\nValor solicitado potencial das propostas não contratadas, por última etapa:")
    print(
        metricas["perdas_por_etapa"].to_string(
            index=False,
            formatters={"valor_solicitado_potencial": "R$ {:,.2f}".format},
        )
    )

    print("\nDesfechos associados às perdas na etapa 3:")
    perdas_etapa_3 = metricas["perdas_por_etapa_status"].query("etapa_max_funil == 3")
    print(
        perdas_etapa_3.to_string(
            index=False,
            formatters={"valor_solicitado_potencial": "R$ {:,.2f}".format},
        )
    )

    print("\nPropostas acima do limite de LTV de 60% indicado no enunciado:")
    print(
        metricas["resumo_ltv_acima_limite"].to_string(
            index=False,
            formatters={
                "valor_solicitado_potencial": "R$ {:,.2f}".format,
                "valor_solicitado_contratado": "R$ {:,.2f}".format,
            },
        )
    )

    cenarios = metricas["cenarios_recomendacoes"]
    print("\nCenários para dimensionar recomendações (não são previsões):")
    print(
        "- Correspondentes: taxa atual {:.1%}; outros canais {:.1%}; "
        "diferença de aproximadamente {:.0f} contratos no mesmo volume, "
        "se o canal alcançasse a taxa dos outros canais.".format(
            cenarios["taxa_correspondente"],
            cenarios["taxa_outros_canais"],
            cenarios["contratos_adicionais_cenario"],
        )
    )
    print(
        "- Etapa 3 / Sem retorno: meta hipotética de reengajar 10% de {} propostas "
        "(~{} propostas; cerca de R$ {:,.2f} em crédito solicitado associado).".format(
            cenarios["sem_retorno_etapa_3"],
            cenarios["propostas_reengajadas_cenario"],
            cenarios["valor_reengajado_cenario"],
        )
    )
    print(
        "- LTV acima de 60%: revisar {} propostas, incluindo {} já contratadas; "
        "R$ {:,.2f} foi solicitado nesse grupo e R$ {:,.2f} corresponde às contratadas.".format(
            metricas["resumo_ltv_acima_limite"].loc[0, "propostas"],
            metricas["resumo_ltv_acima_limite"].loc[0, "contratadas"],
            metricas["resumo_ltv_acima_limite"].loc[0, "valor_solicitado_potencial"],
            metricas["resumo_ltv_acima_limite"].loc[0, "valor_solicitado_contratado"],
        )
    )

    print("\nContratação por canal (taxa = contratadas / propostas do canal):")
    print(
        metricas["desempenho_canais"].to_string(
            index=False,
            formatters={"taxa_contratacao": "{:.1%}".format},
        )
    )

    print("\nContratação por mês de entrada (taxa = contratadas / propostas do mês):")
    print(
        metricas["contratacao_mensal"].to_string(
            index=False,
            formatters={"taxa_contratacao": "{:.1%}".format},
        )
    )

    print("\nContratação por ano de entrada:")
    print(
        metricas["contratacao_anual"].to_string(
            index=False,
            formatters={"taxa_contratacao": "{:.1%}".format},
        )
    )

    print("\nComparação entre a janela mais recente de 7 dias no arquivo e a anterior:")
    print(
        metricas["resumo_semanal"].to_string(
            index=False,
            formatters={
                "taxa_contratacao": "{:.1%}".format,
                "valor_solicitado_nao_contratado": "R$ {:,.2f}".format,
            },
        )
    )

    tabelas_perfil = [
        ("LTV", "contratacao_por_ltv"),
        ("Tipo de imóvel", "contratacao_por_imovel"),
        ("Score de crédito (quartis)", "contratacao_por_score"),
        ("Valor solicitado (quartis)", "contratacao_por_ticket"),
        ("UF", "contratacao_por_uf"),
    ]
    for titulo, nome_tabela in tabelas_perfil:
        print(f"\nContratação por {titulo.lower()}:")
        print(
            metricas[nome_tabela].to_string(
                index=False,
                formatters={"taxa_contratacao": "{:.1%}".format},
            )
        )

    print("\nContratação por consultor (ordenado da menor para a maior taxa):")
    print(
        metricas["contratacao_por_consultor"]
        .sort_values("taxa_contratacao")
        .to_string(
            index=False,
            formatters={"taxa_contratacao": "{:.1%}".format},
        )
    )

    print("\nContratação por canal dentro de cada faixa de LTV:")
    print(
        metricas["contratacao_canal_ltv"].to_string(
            index=False,
            formatters={"taxa_contratacao": "{:.1%}".format},
        )
    )

    print("\nContratação por canal dentro de cada quartil de score:")
    print(
        metricas["contratacao_canal_score"].to_string(
            index=False,
            formatters={"taxa_contratacao": "{:.1%}".format},
        )
    )

    print("\nDistribuição percentual dos desfechos dentro de cada canal:")
    print(metricas["status_por_canal"].to_string())

    print("\nCorrespondente versus outros canais no mesmo consultor (mínimo 20 propostas por grupo):")
    qtd_menor_taxa = int(
        metricas["comparacao_por_consultor"]["diferenca_pontos_percentuais"].lt(0).sum()
    )
    qtd_consultores_comparados = len(metricas["comparacao_por_consultor"])
    print(
        f"Correspondentes tiveram taxa menor em {qtd_menor_taxa} de "
        f"{qtd_consultores_comparados} consultores comparáveis."
    )
    print(
        metricas["comparacao_por_consultor"].to_string(
            index=False,
            formatters={
                "taxa_correspondente": "{:.1%}".format,
                "taxa_outros_canais": "{:.1%}".format,
                "diferenca_pontos_percentuais": "{:+.1f}".format,
            },
        )
    )


if __name__ == "__main__":
    main()
