# 2026-09-18 — Vigia da Play rodando no GitHub (sem o PC) + 2 defeitos reais

## Estado

- `kansas-watch.yml` e `kansas-release.yml` estão na **branch default**
  (`claude/download-local-files-5hfmT`) — cron do Actions só dispara ali.
  Autorizado pelo Fabio nesta sessão.
- Primeira execução real no runner: **run 35289752282, sucesso**. Leu a ficha
  da Play, gravou `evidence/play-state.json` e commitou de volta sozinho.
- Cron ativo: 08h e 19h BRT.

## Dois defeitos que só apareceram fora do sandbox

1. **Cache regional da Play.** O runner (EUA) leu `"16 de set. de 2026"` e o
   sandbox leu `"17 de set. de 2026"` no MESMO dia, ambos com `hl=pt_BR&gl=BR`.
   Vigiar `atualizado_em` geraria "mudou" em toda execução. Agora o campo é
   informativo; a comparação usa versão, downloads, IAP e título, e a data mais
   recente já vista fica em `atualizado_em_max`.
2. **Resposta inesperada virava estado bom.** O parser gravou `titulo='<!--'`.
   `ficha_valida()` agora barra HTTP != 200, título vazio/HTML/URL e resposta
   sem versão — e **mantém o último estado bom** em vez de sobrescrever.
   Coberto por `kansas/tools/tests_play_watch.py` (9 casos, verde no CI).

## Pendência de segurança (importante para todos os agentes)

O token do bot `@Vagadeeemprego_bot` e o `chat_id` estão em texto no
`CLAUDE.md`, e o repositório `fabiokansas-maker/AUTOMA-O` é **público**
(verificado via API: `visibility = public`). Qualquer pessoa que leia o repo
controla o bot. Recomendado: revogar no @BotFather, gerar token novo e guardar
como secret (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`), nunca no markdown.

Enquanto os secrets não existirem no repo, o vigia **roda e registra o estado**,
mas não notifica.

## Prazo em pé

Verificação de desenvolvedor Android: **30/09/2026**. O vigia avisa nos marcos
de 14, 7, 5, 3, 2, 1 e 0 dias.
