# Desafio Prático — Estágio AI & Data Lab | Bari

## Objetivo

Investigar, com os dados fictícios fornecidos no desafio, onde as propostas de crédito deixam o funil, como variam as taxas de contratação e quais pontos merecem validação com as áreas de negócio. A análise é descritiva: identifica padrões e associações, mas não demonstra causalidade.

## Arquivos

- `propostas_credito.csv`: propostas de crédito fornecidas para análise.
- `Teste.py`: leitura, tratamento, diagnóstico e geração do relatório da Parte 2.
- `extrair_laudos.py`: prepara um prompt com os laudos e o esquema para uso na interface de IA; não faz chamadas de API.
- `avaliar_laudos.py`: valida a resposta JSON e compara campos com a referência inicial.
- `laudos_avaliacao/`: 17 laudos em texto livre para a Parte 3.
- `esquema_laudos.json`: formato de saída planejado para a extração estruturada da Parte 3.
- `referencia_laudos.json`: referência inicial para revisar e avaliar a extração.
- `DIARIO.md`: rascunho do diário de bordo; complete tempo e reflexão pessoal.
- `RESUMO_EXECUTIVO.md`: resumo de resultados, recomendações e limites.
- `saida/relatorio_funil.html`: relatório HTML gerado pelo script.
- `saida/execucao.log`: log da execução mais recente.

A automação da Parte 2 tem uma primeira versão. Na Parte 3, os 17 laudos foram comparados com a referência revisada: houve concordância em 442 de 442 valores e status, sem divergências ou avisos de evidência. Isso demonstra consistência com a referência revisada, não acurácia independente. O diário e o resumo executivo ainda precisam da revisão pessoal do candidato.

## Como executar a análise atual

1. Abra o terminal na pasta do projeto e ative o ambiente virtual em que instalou o pandas.
2. Execute:

   ```powershell
   python Teste.py
   ```

O script lê o CSV ao lado dele, imprime a auditoria e as tabelas no terminal e atualiza o relatório e o log na pasta `saida/`. Se o comando `python` apontar para outro ambiente, selecione no VS Code o mesmo interpretador em que o pandas está instalado.

### Como a janela semanal é definida

A comparação usa os sete dias mais recentes representados em `data_entrada` e os sete dias imediatamente anteriores. A janela é ancorada na data máxima do arquivo, em vez da data do computador, porque o CSV fornecido é histórico e termina em 2025. Quando a base for atualizada semanalmente, a janela acompanha as datas novas. Na execução de referência, cada janela tinha apenas duas propostas; por isso o relatório e o log avisam que a taxa semanal é instável. O alerta de 30 propostas é um limite operacional para chamar atenção, não um critério de significância estatística.

### Agendar no Windows

No Agendador de Tarefas do Windows, crie uma tarefa semanal para segunda-feira. Use como programa o `python.exe` do ambiente virtual em que o pandas está instalado, como argumento o caminho completo para `Teste.py` e como pasta inicial `C:\testeBari`. O arquivo `propostas_credito.csv` deve ser atualizado antes da execução. O relatório e o log serão substituídos a cada execução.

## O que a análise faz

1. Confere se o CSV existe e contém as colunas necessárias para os cálculos.
2. Converte `valor_imovel` e `data_entrada` para formatos que permitem fazer contas e agrupar por mês.
3. Padroniza os nomes dos canais, para que variações de escrita não sejam tratadas como canais diferentes.
4. Calcula `ltv` como `valor_solicitado / valor_imovel`, pois o dicionário define essa razão, mas o CSV não contém a coluna.
5. Remove as propostas cujo tipo de imóvel é `Terreno`, conforme instrução explícita do desafio.
6. Calcula volumes e taxas de contratação por etapa, canal, mês, ano, LTV, score, valor solicitado, tipo de imóvel, UF e consultor.
7. Compara correspondentes com outros canais dentro das faixas de LTV e score e dentro do mesmo consultor.
8. Gera um relatório HTML e registra início, conclusão e avisos no log. Interrompe a execução com erro registrado se o CSV estiver ausente, ilegível ou sem uma coluna obrigatória.

### Por que essas escolhas

- **Pandas e código reproduzível:** o arquivo tem 6.400 linhas e várias dimensões de comparação. O script permite repetir os cálculos sobre o CSV inteiro e revisar as regras. Uma análise manual em planilha também seria possível, mas seria mais difícil reproduzir exatamente cada tratamento.
- **Remover Terreno:** essa exclusão não foi inferida por nós; o enunciado exige que ela seja feita antes da análise.
- **Padronizar canais por um mapeamento explícito:** o CSV tem oito grafias distintas que correspondem a cinco canais. Apenas converter para minúsculas não resolveria diferenças de acento e grafia, como `Organico` e `Orgânico`.
- **Calcular o LTV:** a fórmula descrita no dicionário é `valor_solicitado / valor_imovel`. Guardamos a razão como proporção; por exemplo, `0,60` equivale a `60%`.
- **Usar taxas junto dos volumes:** uma taxa sem seu denominador pode dar destaque excessivo a um grupo pequeno. Por isso, as tabelas mostram propostas e contratos além da taxa.
- **Criar faixas fixas para LTV e quartis para score e valor solicitado:** a faixa de 60% vem do limite citado no enunciado. Para score e valor, o desafio não define cortes; os quartis criam quatro grupos de tamanho parecido a partir da própria base. Os intervalos observados são impressos pelo script.
- **Comparar canais dentro de grupos e consultores:** isso verifica se a diferença bruta persiste em recortes mais parecidos. Ainda não controla todas as características simultaneamente e, portanto, não prova que o canal causou a diferença.
- **Sinalizar a etapa 7 sem alterar ou excluir a proposta:** o dicionário descreve etapas de 1 a 6, mas a única proposta na etapa 7 está contratada e tem dados de contrato. Sem confirmação do negócio, alterar a etapa ou excluir o registro seria uma suposição.
- **Não preencher datas de contrato e taxas ausentes:** os 5.159 registros sem esses campos coincidem com as propostas não contratadas. A ausência parece estrutural; preencher esses valores inventaria informação.
- **Tratar valor solicitado como volume potencial associado a uma perda:** é o montante de crédito pedido nas propostas não contratadas. Não equivale a receita, lucro ou dinheiro que a empresa certamente teria recebido.
- **Usar 20 propostas como mínimo na comparação por consultor:** esse corte reduz o destaque de grupos muito pequenos. É um critério prático, não um limiar de significância estatística; mostramos os volumes para que a comparação possa ser avaliada.

## Auditoria e decisões de tratamento

| Achado | Tratamento | Motivo e limite |
|---|---|---|
| 6.400 linhas na base original | Mantidas para auditoria inicial | Contagem de referência antes da exclusão obrigatória. |
| 535 propostas de `Terreno` | Removidas da base de análise | Regra explícita do desafio. Restaram 5.865 propostas. |
| Oito grafias de canal | Mapeadas para cinco nomes canônicos | Evita contar variações de caixa, espaços, acento e grafia como canais diferentes. |
| Três valores de imóvel com prefixo `R$` | Prefixo removido e valor convertido | A conversão numérica teve zero valores inválidos após o tratamento. |
| Datas em ISO e em formato brasileiro | Interpretadas com dia primeiro | Não houve datas de entrada inválidas após a conversão. |
| Uma proposta na etapa 7 | Mantida e sinalizada | Fora do dicionário, mas tem status e dados de contratação; confirmar com o negócio. |
| `ltv` não existe no CSV | Calculado pela fórmula do dicionário | Precisamos validar com o negócio se a fórmula e os valores de origem estão alinhados à regra operacional. |
| 904 propostas com LTV acima de 60%, 109 contratadas | Sinalizadas para revisão, sem exclusão automática | O enunciado informa máximo de 60%. Os casos podem refletir exceções, divergência de dados ou regra aplicada de outra forma. |
| `taxa_juros_aa` sugere taxa anual, mas o dicionário descreve taxa mensal | Campo não usado nas conclusões | A unidade é ambígua e precisa de confirmação. |
| Ausência de data de assinatura e taxa nas propostas não contratadas | Mantida como ausente | Não há base para imputar esses dados. |

## Resultados preliminares da Parte 1

- Após remover `Terreno`, restaram **5.865 propostas**, das quais **1.128 foram contratadas**.
- A maior soma de crédito solicitado entre propostas não contratadas aparece na etapa 3: **1.657 propostas e R$ 649,8 milhões solicitados**. Nesse grupo, os desfechos foram desistência (575), reprovação de crédito (556) e sem retorno (526).
- A conversão geral foi **20,3% em 2024** e **18,4% em 2025**. Há variação entre meses; isso sugere queda anual, mas não demonstra uma queda contínua recente.
- Correspondentes tiveram conversão de **13,7%** (223 contratos em 1.627 propostas), contra **21,4%** nos demais canais combinados. A taxa dos correspondentes foi menor em 27 dos 30 consultores comparáveis e também permaneceu baixa na maioria das faixas de LTV e score analisadas.
- O canal de correspondentes teve **27,9% de propostas sem retorno**, ante 23,4% a 25,7% nos outros canais.
- A contratação variou de **12,1%** entre propostas com LTV acima de 60% a **23,0%** na faixa de 40% a 50%. Por quartis de score, variou de **11,3%** no quartil inferior a **29,5%** no superior.

Esses recortes são descritivos. Mesmo comparando canal dentro de faixas ou do mesmo consultor, podem existir diferenças de perfil não observadas. Os resultados servem para priorizar investigação e pilotos, não para afirmar causalidade.

## Recomendações candidatas e estimativas

1. **Validar a regra e os dados de LTV:** revisar as 904 propostas acima de 60%, incluindo 109 contratadas. O grupo soma R$ 468,9 milhões solicitados; R$ 59,1 milhões correspondem às propostas contratadas. O impacto estimado é o escopo da revisão, não uma economia comprovada.
2. **Rodar um piloto de qualificação e acompanhamento no canal de correspondentes:** a diferença bruta para os outros canais é de 7,7 pontos percentuais. Se as 1.627 propostas atingissem a conversão combinada dos outros canais, o cenário seria de aproximadamente 124 contratos adicionais. Supõe que a diferença seja redutível e não garante o resultado.
3. **Testar um fluxo de contato para propostas sem retorno na etapa 3:** há 526 propostas nessa situação, associadas a R$ 207,7 milhões solicitados. Uma meta hipotética de reengajar 10% alcançaria cerca de 53 propostas e R$ 20,8 milhões em crédito solicitado associado; isso não significa 53 novos contratos.

## Registro de uso de IA e tempo de trabalho

O uso de IA será documentado no `DIARIO.md`, com as ferramentas utilizadas, exemplos de sugestões incorretas ou incompletas, validações feitas e o que foi aprendido. O tempo total de trabalho foram de : **15 horas**.

Os dados do desafio são fictícios. A revisão de propostas acima de 60% tornou-se um abacaxi útil para a análise: é preciso reconciliar a regra de negócio com os registros antes de chamar esses casos de violações.

## Parte 3 — extração estruturada dos laudos

`esquema_laudos.json` define os campos, os tipos de valor e como registrar evidências e ausências. `referencia_laudos.json` contém uma referência inicial para os 17 documentos, montada durante a revisão assistida por IA. Antes de tratar as métricas como resultado final, o USUÁRIO deve conferir valores, evidências e decisões de classificação. Por exemplo, idade aproximada não vira ano de construção.

Na conferência atual, os 17 arquivos têm referência correspondente, não há nomes duplicados no conjunto e todos os trechos de evidência registrados foram encontrados nos respectivos textos. Essa checagem confirma correspondência literal e estrutura; não substitui a revisão semântica das classificações.

### Como interpretar os casos ambíguos

- `área útil` não foi tratada automaticamente como `área privativa` (laudos 03 e 13), pois o esquema pede uma categoria específica e o texto não afirma que os termos sejam equivalentes. O valor numérico fica nulo nesse campo; a medida original permanece na evidência.
- `área coberta` não foi tratada automaticamente como `área construída` (laudo 14), pelo mesmo motivo; o valor numérico fica nulo nesse campo.
- Idade aproximada e ano de referência não foram convertidos em ano de construção (laudos 03, 08 e 14). O ano genérico do laudo 12 também não identifica a que evento se refere, então foi marcado como ambíguo.
- A data de levantamento do laudo 11 não foi assumida como data de vistoria: o valor fica nulo e a diferença de significado é registrada como ambiguidade.
- No laudo 04, o tipo `terreno urbano` não foi usado sozinho para concluir que não existe edificação; como o documento não informa área construída nem declara ausência de construção, o campo fica ausente.
- “Não foi possível verificar” por falta de certidão, ou uma declaração do proprietário sem certidão, significa `nao_verificado`; silêncio ou ausência de dados sobre ônus significa `nao_informado`.
- A área total do laudo 17 tem dois valores; ambos ficam como evidência e o valor estruturado fica nulo com status `conflitante`.
- No laudo 05, 4,8 hectares foram convertidos para 48.000 m² usando 1 ha = 10.000 m². A observação registra que o número foi convertido, não copiado com a unidade original.

1. Gere um prompt com os 17 laudos:

   ```powershell
   python extrair_laudos.py
   ```

2. Abra `saida/prompt_extracao_laudos.md`, copie o conteúdo e cole na interface de IA disponível para você, no meu caso utilizei o GEMINI. O script não envia nenhum arquivo pela rede. Se a resposta for grande demais para a interface, gere um prompt individual com `python extrair_laudos.py --arquivo laudo_01.txt` e repita para cada arquivo.
3. Revise a resposta e salve o array JSON em `saida/laudos_extraidos.json` (UTF-8).
4. Rode `python avaliar_laudos.py`. O avaliador verifica o esquema, arquivos e evidências literais, e compara valores/status com a referência provisória. Problemas de estrutura ficam em `saida/avisos_laudos.json`; métricas e divergências ficam em `saida/avaliacao_extracao.json`.
