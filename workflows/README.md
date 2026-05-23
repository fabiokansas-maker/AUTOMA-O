# Workflows n8n — AUTOMA-O

Todos importados no `n8n-mryj` existente (305 workflows / 161 ativos) via n8nOps MCP (executado pelo ChatGPT). NÃO subimos n8n próprio.

Declarado em `manifest.json`. Credenciais necessárias em `credentials-schema.json`.

## Pipeline AUTOMA-O — vagas

| Arquivo | O que faz | Trigger | Status |
|---|---|---|---|
| `01-coletor.json` | Chama conectores (Gupy/Workday/RemoteOK/Indeed/LinkedIn/etc.) em paralelo, normaliza | Cron 5min | importado |
| `03-matcher.json` | Gemini 2.5 Flash Lite scoring, grava `match_results` | Triggered pelo 01 | importado |
| `04-aplicador-auto.json` | Browserless headless OU email recrutadora | Triggered pelo 03 | importado |
| `05-email-status.json` | Lê confirmações via Gmail + atualiza status | Cron 1h | importado |
| `06-reporter.json` | Relatório diário no Telegram | Cron 21h BRT | importado |
| `07-snapshot-diario.json` | Snapshot DB → Drive | Cron 23h | já existia |
| `08-claude-log-sync.json` | Sincroniza `claude-log/` → Drive | Cron 5min | já existia |

## Infra — backup + monitoramento

| Arquivo | O que faz | Trigger | Status |
|---|---|---|---|
| `09-backup-daily.json` | pg_dump n8n + automao + tar volume n8n + tar /opt/automacoes; upload Drive; retenção 7d | Cron 03h00 BRT | novo |
| `10-healthcheck-5min.json` | Ping 7 serviços; alerta Telegram com rate-limit 30min/serviço; heartbeat 1h | Cron 5min | novo |
| `11-disk-watch.json` | Hostinger API metrics; alerta ≥80%; prune automático ≥90% | Cron 1h | novo |
| `12-doc-sync.json` | README.md/CLAUDE.md do repo → /opt/README.md e /opt/CLAUDE.md | Cron 04h00 BRT | novo |

## Como importar

Via n8nOps MCP (executado pelo ChatGPT):

```
workflows.import_bulk(
  manifest="workflows/manifest.json",
  resolve_credentials_by_logical_id=true,
  active_after_import="per_manifest"
)
```

Pré-condição: credenciais criadas conforme `credentials-schema.json` (valores no env do container n8n-mryj, NUNCA no repo).

## Validação pós-import

```
workflows.list(tag="automao") → 11 entries
```

Ativos esperados: 09/10/11/12 (infra) ficam ON imediatamente. 01–08 ficam OFF até o usuário ativar (decisão para evitar 1ª candidatura acidental).

## Placeholders nos JSONs

Os JSONs usam `id` lógico nas credenciais (ex: `postgres-automao`, `telegram-bot`). n8nOps resolve cada um para o credential UUID concreto no momento do import — não substituir manualmente.
