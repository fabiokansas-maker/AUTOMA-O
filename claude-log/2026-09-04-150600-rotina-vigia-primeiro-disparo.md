---
session: b9a215c3-2fe4-5a92-bf2a-b20226cb7440
agent: claude
ts: 2026-09-04T15:06:00Z
status: completed
tags: [google-play, rotina, mcp, aprendizado-infra]
---

# Rotina "Vigia Play Console" — 1º disparo OK + achado sobre conectores MCP

## Resultado do 1º disparo (2026-09-04 15:05 UTC / 12:05 BRT)

Nada novo e acionável. Únicos e-mails do Play em 48h:
- 04/09 02:45 — o lembrete final da verificação de desenvolvedor (já analisado)
- ruído: recibo Anthropic, Play Points nível Platina, assinatura Tinder

Nenhum Telegram disparado. Comportamento correto conforme regra 4 da rotina.

## ACHADO DE INFRA (vale para qualquer rotina futura)

Ao criar o trigger, o `create_trigger` devolveu este aviso:

> "this trigger stores no MCP connectors, so the sessions it fires will run
> without connector (mcp__<server>__*) tools"

**Esse aviso NÃO se aplica a trigger self-bind.** Confirmado empiricamente no
disparo real: a rotina foi criada com `persist_session: true` /
`persistent_session_id` apontando para a própria sessão, e ao disparar o
`mcp__Gmail__search_threads` funcionou normalmente.

Regra prática para outros agentes:
- trigger **self-bind** (dispara na própria sessão) → **herda os conectores** da
  sessão. Usar esse formato sempre que a rotina precisar de Gmail/Drive/etc.
- trigger com `create_new_session_on_fire=true` → sessão nova, **aí sim** o aviso
  vale e a rotina fica sem conector. Evitar para tarefas que dependem de MCP.

Trigger ativo: `trig_0121WfEMD5xih2anM5KpZRRM`, cron `0 15 * * *` (12h BRT),
alvo: prazo 30/09/2026. Deletar depois dessa data.
