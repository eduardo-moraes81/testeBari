# Diário de bordo

> Rascunho para revisar e completar com a experiência real do candidato antes da entrega.

## Uso de IA

Usei o Codex para discutir decisões de tratamento dos dados, estruturar o diagnóstico do funil, propor um esquema JSON para os laudos e preparar scripts de extração e avaliação. E também utilizei a IA para realizar a estrutura do nosso site para fins de relatório do funil.

Um erro importante aconteceu na conisso aconteceu na hora de eu transferir os arquivos de pasta... e mesmo assim ele tinha renomeado automaticamente e corretamente as pastas, porém na hora da analise estava dando como duplicado e eu reparei depois e vi que realmente estava duplicado e corrigi os arquivos. Depois que os arquivos foram atualizados, conferi os 17 nomes e seus hashes SHA-256; a nova versão não contém duplicatas exatas. Aprendi que uma conclusão sobre arquivos precisa estar associada à versão concreta examinada e ser refeita quando a fonte muda.

Outro cuidado foi a exibição de acentos no terminal. O texto parecia corrompido, mas a leitura dos bytes confirmou que os arquivos estavam em UTF-8 válido. Não alterei os originais com base apenas na aparência do terminal.

Uma primeira proposta técnica foi integrar a extração a uma API do chatGPT, porém eu tinha que ter créditos. A tentativa encontrou erros de autenticação e limite de uso; como não havia crédito disponível, essa dependência não era adequada ao contexto. A integração foi removida. Aprendi que o enunciado pede uso de IA, mas não obriga que isso seja feito por API: podemos usar uma interface de IA e manter a validação repetível em código local.

Na Parte 3, o esquema limita o formato da resposta da IA, mas não comprova que a extração esteja correta. Por isso, preparei evidências textuais, estados para campos ausentes ou conflitantes e uma referência inicial para comparação. Revisei as divergências contra os laudos: corrigi a separação entre nome e título profissional, mantive os números de unidade no endereço e marquei como ambíguos dados que o texto não confirma, como ano de construção e equivalência entre área coberta e construída. Depois das correções, o avaliador encontrou concordância em 442 de 442 valores e status, sem avisos de evidência. A revisão das divergências foi concluída; essa concordância mede consistência com a referência revisada, não acurácia independente. Ainda falta minha conferência final da referência e preencher minha reflexão pessoal.

## Conceito que aprendi

Uma taxa de conversão precisa ser lida junto com o volume do grupo. Também aprendi a separar associação de causalidade: uma taxa menor entre correspondentes não prova, por si só, que o canal causou a diferença. Para investigar, comparei grupos dentro de faixas de LTV e score e entre consultores com volumes mínimos, mantendo explícitos os limites desses recortes.

Na extração de texto, aprendi a diferença entre validar a estrutura e validar o conteúdo. Um JSON pode seguir o esquema e ainda trazer um valor incorreto ou uma evidência que não sustenta o campo.

## Autocrítica e próximos passos

- Fazer uma conferência final da referência dos laudos, especialmente os casos ambíguos de área útil, idade aproximada, ônus sem certidão e valores conflitantes.
- As estimativas de impacto são cenários para priorizar pilotos, não previsões de contratos ou receita.
- **Tempo total de trabalho:** [preencher com o tempo real].
- **O que eu mudaria se tivesse mais tempo e verba:** integraria uma API de IA à Parte 3 para o programa enviar automaticamente o texto de cada laudo, solicitar os campos definidos no esquema e salvar as respostas estruturadas em JSON. Depois, o script validaria o formato, conferiria se as evidências aparecem nos textos e compararia os resultados com uma referência revisada por uma pessoa. Isso reduziria o trabalho manual, mas não eliminaria erros de interpretação; por isso, eu manteria a revisão humana e controlaria os custos das chamadas e a segurança da chave da API.
- **O que aprendi e consigo explicar com minhas palavras:** [revisar para refletir seu próprio aprendizado].
