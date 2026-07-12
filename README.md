# Campanha Conscium Devenire

Automação editorial criada para publicar uma campanha de 40 carrosséis no Instagram do Instituto Mestra Natureza.

## Objetivo

A campanha está organizada em duas publicações por semana, às segundas e quintas, durante 20 semanas. O fluxo automatiza a escolha do post correto, a preparação do carrossel, a publicação pela Meta Graph API e o registro do resultado.

Período planejado: 13/07/2026 a 26/11/2026, sempre às 11h no horário de Brasília.

## Como funciona

1. O GitHub Actions inicia o fluxo conforme o agendamento ou por execução manual.
2. `publish.py` identifica o post correspondente à data no `schedule.json`.
3. Cada imagem é enviada para a Meta e acompanhada até o fim do processamento.
4. O carrossel é montado e publicado.
5. O resultado é gravado em `state/published.json` para evitar repetição.

## Cuidados de operação

* controle de estado para impedir publicações duplicadas
* grupo de concorrência no GitHub Actions
* novas tentativas em falhas temporárias de rede ou da API
* verificação do processamento de cada item antes da publicação
* parâmetro de cache busting nas URLs das imagens
* modo `DRY_RUN` para montar e validar o carrossel sem publicar
* execução manual de um post específico por `workflow_dispatch`

## Estrutura

* `posts/post-NN/`: imagens e legenda de cada publicação
* `schedule.json`: calendário, configuração e relação de cards
* `publish.py`: integração com a Meta Graph API
* `.github/workflows/publish.yml`: agendamento e execução no GitHub Actions
* `state/published.json`: histórico usado pelo controle de idempotência

As imagens são servidas por `raw.githubusercontent.com` para que os servidores da Meta consigam acessá-las durante a criação do carrossel. Por isso, este repositório é público.

## Configuração

O workflow espera dois segredos no GitHub:

* `IG_ACCESS_TOKEN`: token com permissão `instagram_content_publish`
* `IG_USER_ID`: identificador da conta Instagram Business

A versão da Graph API pode ser ajustada pela variável `API_VERSION`.

## Teste manual

Em **Actions**, abra **Publicar carrossel no Instagram** e escolha **Run workflow**.

Deixe `force_post` vazio para usar o post agendado para o dia ou informe uma pasta, como `post-05`, para testar uma publicação específica. Para validar sem publicar, defina `DRY_RUN` no ambiente de execução.

## Status

Automação em implantação para a campanha prevista entre julho e novembro de 2026.

## Conteúdo e direitos

Os cards, textos, marca e materiais editoriais pertencem ao Instituto Mestra Natureza e aos respectivos autores. O código da automação está publicado para consulta e estudo.
