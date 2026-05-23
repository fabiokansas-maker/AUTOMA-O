# Padronização n8n-mryj — Checklist + diff aplicável

Aplica APENAS o que o diagnóstico (`evidence/<data>-diagnostics.md`) marcou como FALSE. Executado pelo ChatGPT via Hostinger MCP `vps.execute`.

## Pré-condição obrigatória

Backup full do n8n-mryj antes de QUALQUER edit:

```bash
# Snapshot Postgres do n8n
docker exec n8n-mryj-postgres pg_dump -U n8n n8n | gzip > /opt/backups/pre-standardization-n8n-db-$(date +%F).sql.gz

# Snapshot volume n8n_data
tar czf /opt/backups/pre-standardization-n8n-vol-$(date +%F).tar.gz \
  -C /var/lib/docker/volumes/n8n-mryj_n8n_data _data
```

Se algum dos dois falhar, NÃO PROSSEGUIR. Reportar no Telegram.

## Issue 1 — `DB_TYPE != postgresdb` (SQLite detectado)

Risco: SQLite em produção limita workflows concorrentes e perde durabilidade.

Plano de migração (executar OFFLINE — janela de manutenção ≤30min):

```bash
# 1. Parar n8n
docker compose -f /path/to/n8n-mryj/docker-compose.yml stop n8n

# 2. Exportar workflows e credenciais para JSON (n8n CLI)
docker run --rm \
  -v n8n-mryj_n8n_data:/home/node/.n8n \
  -v /opt/backups/n8n-export:/export \
  n8nio/n8n:latest \
  n8n export:workflow --all --output=/export/workflows.json

docker run --rm \
  -v n8n-mryj_n8n_data:/home/node/.n8n \
  -v /opt/backups/n8n-export:/export \
  n8nio/n8n:latest \
  n8n export:credentials --all --output=/export/credentials.json

# 3. Editar docker-compose.yml do n8n-mryj — adicionar:
#    DB_TYPE=postgresdb
#    DB_POSTGRESDB_HOST=<host postgres existente OU postgres do stack connectors>
#    DB_POSTGRESDB_PORT=5432
#    DB_POSTGRESDB_DATABASE=n8n
#    DB_POSTGRESDB_USER=...
#    DB_POSTGRESDB_PASSWORD=...

# 4. Subir Postgres ANTES (já está rodando? confirmar)
# 5. Subir n8n com nova config
docker compose -f /path/to/n8n-mryj/docker-compose.yml up -d n8n

# 6. Importar workflows e credenciais
docker exec n8n-mryj n8n import:workflow --separate --input=/export/workflows.json
docker exec n8n-mryj n8n import:credentials --separate --input=/export/credentials.json

# 7. Validar contagem: deve bater com 305 workflows / 161 ativos do diagnóstico
docker exec n8n-mryj n8n list:workflow | wc -l
```

## Issue 2 — `restart != unless-stopped`

```bash
# Editar docker-compose.yml e setar restart: unless-stopped no service n8n
# OU via docker update (mais barato):
docker update --restart unless-stopped n8n-mryj
```

## Issue 3 — Vars `N8N_HOST`, `WEBHOOK_URL`, `GENERIC_TIMEZONE`, `TZ` ausentes

Editar docker-compose.yml do n8n-mryj (NÃO o nosso connectors), adicionar:

```yaml
environment:
  N8N_HOST: srv1621330.hstgr.cloud
  N8N_PROTOCOL: https
  WEBHOOK_URL: https://srv1621330.hstgr.cloud/
  GENERIC_TIMEZONE: America/Sao_Paulo
  TZ: America/Sao_Paulo
```

Restart:

```bash
docker compose -f /path/to/n8n-mryj/docker-compose.yml up -d n8n
```

## Validação pós-padronização

```bash
docker inspect n8n-mryj --format '{{json .Config.Env}}' | jq -r '.[]' | \
  grep -E '^(DB_TYPE|N8N_HOST|WEBHOOK_URL|GENERIC_TIMEZONE|TZ)='

docker inspect n8n-mryj --format '{{.HostConfig.RestartPolicy.Name}}'

# Smoke: API responde?
curl -sI http://127.0.0.1:5678/healthz | head -1

# Workflows ainda no count esperado?
docker exec n8n-mryj n8n list:workflow | wc -l
```

Cada um dos checks deve retornar OK. Se alguma divergência, restaurar do backup da pré-condição.

## Importar workflows AUTOMA-O

Após padronização OK, ChatGPT via n8nOps:

```
workflows.import_bulk(
  files=["workflows/01-coletor.json", ..., "workflows/12-doc-sync.json"],
  resolve_credentials_by_logical_id=true,
  active_after_import="per_manifest"
)
```

Validação:

```
workflows.list(tag="automao") → 11 entries
```
