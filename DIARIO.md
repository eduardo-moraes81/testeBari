# Diário de bordo

> Rascunho para revisar e completar com a experiência real do candidato antes da entrega.

## Uso de IA

Usei o Codex para discutir decisões de tratamento dos dados, estruturar o diagnóstico do funil, propor um esquema JSON para os laudos e preparar scripts de extração e avaliação. Também usei a IA como apoio para entender erros de instalação do pandas.

Um erro importante aconteceu na conferência dos laudos: uma versão do arquivo `laudo_02.txt` tinha o mesmo conteúdo que `laudo_03.txt`, e a análise apontou essa duplicidade. Depois que os arquivos foram atualizados, conferi os 17 nomes e seus hashes SHA-256; a nova versão não contém duplicatas exatas. Aprendi que uma conclusão sobre arquivos precisa estar associada à versão concreta examinada e ser refeita quando a fonte muda.

Outro cuidado foi a exibição de acentos no terminal. O texto parecia corrompido, mas a leitura dos bytes confirmou que os arquivos estavam em UTF-8 válido. Não alterei os originais com base apenas na aparência do terminal.

Na Parte 3, o esquema limita o formato da resposta da IA, mas não comprova que a extração esteja correta. Por isso, preparei evidências textuais, estados para campos ausentes ou conflitantes e uma referência inicial para comparação. A referência foi montada com assistência de IA e precisa de conferência humana antes de ser usada como gabarito definitivo.

## Conceito que aprendi

Uma taxa de conversão precisa ser lida junto com o volume do grupo. Também aprendi a separar associação de causalidade: uma taxa menor entre correspondentes não prova, por si só, que o canal causou a diferença. Para investigar, comparei grupos dentro de faixas de LTV e score e entre consultores com volumes mínimos, mantendo explícitos os limites desses recortes.

Na extração de texto, aprendi a diferença entre validar a estrutura e validar o conteúdo. Um JSON pode seguir o esquema e ainda trazer um valor incorreto ou uma evidência que não sustenta o campo.

## Autocrítica e próximos passos

- A extração por API ainda precisa ser executada e comparada à referência.
- A referência dos laudos precisa ser revisada por uma pessoa, especialmente os casos ambíguos de área útil, idade aproximada, ônus sem certidão e valores conflitantes.
- As estimativas de impacto são cenários para priorizar pilotos, não previsões de contratos ou receita.
- **Tempo total de trabalho:** [preencher com o tempo real].
- **O que eu mudaria se tivesse mais tempo:** [preencher com a autocrítica pessoal].
- **O que aprendi e consigo explicar com minhas palavras:** [revisar para refletir seu próprio aprendizado].
