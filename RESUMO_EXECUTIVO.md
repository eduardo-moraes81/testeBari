# Resumo executivo

## Diagnóstico

Após remover as 535 propostas de terrenos conforme o desafio, a base de análise ficou com **5.865 propostas**, das quais **1.128 foram contratadas**. A maior concentração de crédito solicitado entre propostas não contratadas está na etapa 3: **1.657 propostas e R$ 649,8 milhões solicitados**. O valor representa crédito pedido, não receita ou perda financeira realizada.

A conversão anual foi de **20,3% em 2024** e **18,4% em 2025**. Correspondentes converteram **13,7%** (223 de 1.627), contra **21,4%** nos demais canais. A diferença persistiu na maioria dos recortes por LTV, score e consultor, mas a análise é observacional e não demonstra causalidade.

## Recomendações priorizadas

1. **Investigar e testar melhorias no canal de correspondentes.** A diferença bruta de 7,7 pontos percentuais equivale a cerca de **124 contratos adicionais** em um cenário hipotético no qual o canal atingisse a taxa combinada dos demais. Tratar esse número como potencial para dimensionar um piloto, não como previsão.
2. **Revisar propostas com LTV acima de 60%.** São **904 propostas**, das quais 109 foram contratadas, associadas a R$ 468,9 milhões solicitados. Confirmar a fórmula e as exceções com a área de negócio antes de interpretar os casos como violações.
3. **Testar contato de recuperação para propostas sem retorno na etapa 3.** São **526 propostas**, com R$ 207,7 milhões solicitados. Uma meta hipotética de reengajar 10% alcançaria cerca de 53 propostas e R$ 20,8 milhões em crédito solicitado associado; não implica novos contratos.

## Automação e extração de laudos

A rotina da Parte 2 lê o CSV, aplica os tratamentos documentados e gera relatório HTML e log. A Parte 3 tem um esquema estruturado, referência inicial para 17 laudos, script de extração via API e avaliador de divergências. **A extração ainda não foi executada**; depende de chave de API configurada localmente, pode gerar cobrança e requer revisão humana da referência e das respostas.

## Limites

Os resultados são descritivos; grupos podem diferir em características não observadas. A base tem poucos registros nas janelas semanais recentes, então as taxas semanais são instáveis. Valores solicitados não equivalem a perdas, receita ou lucro. A saída estruturada da IA não substitui a conferência do texto original.
