# Infra setup

## Pré-requisitos
- Docker + Docker Compose
- Acesso ao seu n8n existente (URL + API key opcional)
- Conta Google com Drive (pra bridge Obsidian)

## Subir

```bash
cp .env.example .env
# Edite .env com credenciais reais (mínimo: senhas Postgres + Browserless token)
docker compose up -d
```

Confira:
```bash
docker compose ps
docker compose logs -f connectors
psql postgres://automao:<senha>@localhost:5432/automao -c '\dt'
```

## Conectar ao seu n8n

No n8n, crie credenciais:
- **Postgres** apontando pra `host.docker.internal:5432` (se n8n e infra estão no mesmo host) ou IP da VPS.
- **HTTP Header Auth** com header `X-API-Key: <CONNECTORS_API_KEY do .env>` pra chamar os conectores.
- **Google Drive OAuth** pra ler/escrever no vault Obsidian sincronizado.
- **Anthropic** ou **OpenAI** pra LLM.
- **Telegram Bot** pra notificações.

Importe os JSONs de `../workflows/` pelo UI do n8n (Settings → Import) e ative.

## Snapshot diário (Git)

O workflow `07-snapshot.json` precisa de SSH key configurada no host onde o n8n roda Bash, OU usa o GitHub MCP/API. Veja `../workflows/README.md`.
