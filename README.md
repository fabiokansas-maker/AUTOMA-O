# ChatGPT Command Bridge

Ponte para o ChatGPT operar VPS / n8n / Jarvis usando Google Drive + Google Sheets
como camada de transporte, já que o ChatGPT não tem ferramenta direta de Hostinger,
SSH, n8n, vpsOps ou Telegram.

## Fluxo

```
ChatGPT
   │  escreve linha em Sheets!commands (status=new)
   ▼
Google Sheet  "ChatGPT Command Bridge"
   │  polling a cada 30s
   ▼
n8n workflow  chatgpt-command-bridge-monitor-v1
   │
   ├── aplica policy.json
   ├── auto      → executa via vpsOps / API Ops / Jarvis
   ├── approval  → move para pending_approval, avisa Jarvis
   └── blocked   → grava em logs, recusa
   │
   ▼
Sheets!results  +  Drive (relatório .md)
   │
   ▼
ChatGPT lê results na próxima rodada
```

## Estrutura do repositório

```
docs/
  ARCHITECTURE.md      detalhes do contrato entre camadas
  POLICY.md            quem pode o quê
sheets/
  schema.json          schema de cada aba do Sheet
  seed.csv             linhas iniciais (policy + 1 comando de teste)
n8n/
  chatgpt-command-bridge-monitor-v1.json   workflow exportável
jarvis/
  bridge_commands.md   spec dos comandos /bridge
  bridge_handlers.py   handlers de referência
scripts/
  test_healthcheck.sh  primeiro teste end-to-end
  validate_command.py  valida payload contra schema antes de gravar
```

## Pré-requisitos no lado Fabio

1. Service Account do Google com acesso ao Sheet e à pasta Drive
2. n8n com credenciais Google Sheets / Google Drive já cadastradas
3. vpsOps e API Ops respondendo em endpoints fixos
4. Jarvis com webhook de entrada (`/bridge ...`)

## Provisionamento

Os IDs (sheet_id, workflow_id, folder_id) não são gerados aqui — este
container não tem acesso ao Google nem ao n8n do Fabio. O passo-a-passo
de provisionamento está em `docs/ARCHITECTURE.md`.
