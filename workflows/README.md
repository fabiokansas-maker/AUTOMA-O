# Workflows n8n

Importe cada `.json` no UI do seu n8n (Workflows → Import from File).

## Lista

| Arquivo | O que faz | Trigger |
|---|---|---|
| `01-coletor.json` | Chama todos os conectores em paralelo, normaliza resultados | Cron 5min *(TODO)* |
| `02-deduplicador.json` | Insere em `jobs` com `ON CONFLICT DO NOTHING` | Triggered pelo 01 *(TODO)* |
| `03-matcher.json` | LLM avalia score + gaps, salva em `match_results` | Triggered pelo 02 *(TODO)* |
| `04-aplicador.json` | DRAFT (gera carta + notifica) ou AUTO (submete) | Triggered pelo 03 *(TODO)* |
| `05-notificador.json` | Telegram com card + botões 1-click | Triggered pelo 04 *(TODO)* |
| `06-reporter.json` | Relatório markdown diário em Obsidian | Cron 9h *(TODO)* |
| **`07-snapshot-diario.json`** | Snapshot do dia em `snapshots/YYYY-MM-DD.md` (commit GitHub + Drive) | Cron 23h ✅ |
| **`08-claude-log-sync.json`** | Sincroniza `claude-log/` do GitHub → `Obsidian/Claude/` no Drive | Cron 5min ✅ |

## Credenciais necessárias no n8n

Antes de importar, crie estas credenciais e anote os IDs (ou edite os JSONs depois):
- **Postgres** (host, port, db, user, password do `.env` da `infra/`)
- **GitHub API** (Personal Access Token com `repo`)
- **Google Drive OAuth2** (autorize com a conta cuja Drive sincroniza com o vault Obsidian)
- **HTTP Header Auth** com `X-API-Key: <CONNECTORS_API_KEY>` (pra chamar a API de conectores)
- **Anthropic API** ou **OpenAI API**
- **Telegram Bot**

## Placeholders nos JSONs

Procure e substitua antes de importar (ou edite no UI depois):
- `REPLACE_WITH_POSTGRES_CRED_ID`
- `REPLACE_WITH_GITHUB_CRED_ID`
- `REPLACE_WITH_DRIVE_CRED_ID`
- `REPLACE_WITH_OBSIDIAN_VAGAS_RELATORIOS_FOLDER_ID` (folder ID do Drive)
- `REPLACE_WITH_OBSIDIAN_CLAUDE_FOLDER_ID` (folder ID do Drive)

Pra pegar o folder ID do Drive: abrir a pasta no navegador, copiar o segmento depois de `/folders/` na URL.
