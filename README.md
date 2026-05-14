# AUTOMA-O — Automação de candidatura a vagas

Pipeline de coleta + matching + auto-aplicação em vagas de emprego, orquestrado por **n8n**, com storage no **Obsidian** (via Google Drive) e snapshot diário neste repo.

## Visão geral

```
[Plataformas]              [n8n workflows]               [Storage]
LinkedIn (vagas + posts)   ─┐                       ┌─→ Obsidian (Drive)
Gupy                       ─┤                       │
Vagas.com / Catho          ─┼─→ Coletor → Matcher ─┼─→ Postgres (dedup)
Infojobs                   ─┤   ↓                  │
Indeed / Glassdoor         ─┤   Aplicador (DRAFT/AUTO)
RemoteOK / Remotar         ─┘   ↓                   └─→ snapshots/ (Git, daily)
                                Telegram (1-click apply)
```

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `infra/` | docker-compose (Postgres + Browserless), schema SQL, env template |
| `connectors/` | API HTTP (Express) com 1 endpoint por plataforma |
| `workflows/` | Workflows n8n exportados como `.json` |
| `prompts/` | Prompts de LLM (matching, carta de apresentação) |
| `obsidian-bridge/` | Templates de notas markdown |
| `snapshots/` | Snapshot diário do estado (vagas vistas, aplicações, métricas) — commit automático |

## Setup rápido

1. **Infra:** `cd infra && cp .env.example .env`, edite credenciais, `docker compose up -d`.
2. **Conectores:** `cd connectors && npm i && npm run dev` (sobe Express na porta 3000).
3. **n8n:** importe os JSONs de `workflows/` no seu n8n existente, configure credenciais (Drive, LLM, Telegram), aponte HTTP nodes pra `http://<host>:3000/connectors/<plataforma>`.
4. **Obsidian:** mova vault pra pasta sincronizada do Google Drive Desktop. Crie `Curriculo.md` e `Perfil.md` na raiz.

Setup detalhado em `infra/README.md`.

## Snapshot diário

O workflow `07-snapshot.json` roda 1x/dia e:
1. Pega métricas do Postgres (vagas vistas, aplicadas, taxa de match).
2. Lê resumo do dia do Obsidian.
3. Commita um arquivo `snapshots/YYYY-MM-DD.md` neste repo.

Isso permite acompanhar o histórico via Git e dá visibilidade pra ferramentas externas (incluindo o Claude em sessões futuras).

## Status

Em construção. Roadmap em `/root/.claude/plans/quero-criar-automa-o-que-vectorized-trinket.md` (referência local).
