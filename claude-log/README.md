# claude-log

Log de progresso do agente Claude trabalhando neste repo. Cada sessão/intervenção
escreve um arquivo `YYYY-MM-DD-HHMMSS-<slug>.md` aqui.

O workflow `workflows/08-claude-log-sync.json` (rodando no n8n do usuário, sempre online)
faz pull deste diretório a cada 5 min e escreve em `Obsidian/Claude/` no Google Drive.
Quando o PC do usuário fica online, o Drive Desktop sincroniza pro vault local — o
usuário vê o histórico no Obsidian.

## Formato de entrada

```md
---
session: <id>
agent: claude
ts: <ISO 8601>
status: in_progress | completed | blocked
---

# <Título curto>

<Corpo: o que foi feito, próximos passos, blockers>
```

## Como o agente escreve

Use o helper `scripts/claude-log.sh` (roda local, faz commit + push):

```bash
scripts/claude-log.sh "título" "corpo do update" --status completed
```

Ou via GitHub MCP (`mcp__github__create_or_update_file`) apontando pra
`claude-log/<arquivo>.md` na branch ativa.
