# Campanha Conscium Devenire — automação Instagram (@mestranatureza)

Publica automaticamente os 40 carrosséis da campanha, **2 por semana (segundas e quintas, 11h horário de Brasília)**, ao longo de 20 semanas (13/07/2026 → 26/11/2026).

## Como funciona

- `posts/post-NN/` — cards (`card-*.png`) e `legenda.txt` de cada post.
- `schedule.json` — mapa data → post (fuso `America/Sao_Paulo`, 11:00).
- `publish.py` — descobre o post do dia e publica o carrossel via Meta Graph API.
- `.github/workflows/publish.yml` — roda via cron `0 14 * * 1,4` (14:00 UTC = 11:00 BRT).
- `state/published.json` — registro do que já foi publicado (idempotência).

As imagens são servidas por `raw.githubusercontent.com` (por isso o repositório é público) para que os servidores da Meta consigam baixá-las.

## Segredos do GitHub (Settings → Secrets and variables → Actions)

- `IG_ACCESS_TOKEN` — token da Meta com escopo `instagram_content_publish`.
- `IG_USER_ID` — id da conta Instagram Business (`17841403158526487`).

## Testar manualmente

Actions → **Publicar carrossel no Instagram** → *Run workflow*.
Deixe `force_post` vazio para publicar o post agendado para hoje, ou informe `post-05` para publicar um específico na hora.

## Observações

- O cron do GitHub Actions é em UTC e pode atrasar alguns minutos em horários de pico — normal.
- Se o token expirar, atualize o secret `IG_ACCESS_TOKEN`.
- O commit automático do `state` a cada execução também mantém o agendamento ativo (o GitHub desativa cron após 60 dias de inatividade do repositório).
