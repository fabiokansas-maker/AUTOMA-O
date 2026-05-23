# Template — converter script PC → container orquestrado por n8n

Aplicar para cada script aprovado em `scripts-confirmed-keep.md`.

## Estrutura no repo

```
infra/migration/scripts/<nome>/
├── Dockerfile
├── requirements.txt   (ou package.json)
├── entrypoint.sh
├── README.md
└── .env.example
```

## Estrutura no VPS (após upload)

```
/opt/automacoes/<nome>/
├── Dockerfile
├── requirements.txt
├── entrypoint.sh
├── .env             ← chmod 600, dono root, gerado pelo workflow n8n
└── src/             ← código do script
```

## Dockerfile padrão (Python)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ /app/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

## Dockerfile padrão (Node)

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --omit=dev
COPY src/ /app/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

## entrypoint.sh

```bash
#!/usr/bin/env bash
set -Eeuo pipefail
cd /app
# Carrega .env se existir
[ -f /app/.env ] && set -a && . /app/.env && set +a
exec python -u main.py "$@"   # ou node main.js
```

## docker-compose.automacoes.yml (raiz `/opt/automacoes/`)

Um único compose orquestra todos os scripts migrados. Cada serviço é "one-shot" (chamado via `docker compose run --rm <nome>`) ou daemon (`restart: unless-stopped`).

```yaml
services:
  <nome>:
    build: ./<nome>
    image: automao/<nome>:latest
    restart: "no"                # one-shot; troque para unless-stopped se for daemon
    env_file: ./<nome>/.env
    networks:
      - automao_net
    volumes:
      - /opt/automacoes/<nome>/data:/data:rw

networks:
  automao_net:
    external: true               # rede compartilhada com n8n-mryj se for o caso
```

## Workflow n8n correspondente

`workflows/30-<nome>.json` — schedule trigger + Execute Command:

```
docker compose -f /opt/automacoes/docker-compose.automacoes.yml run --rm <nome>
```

Saída → Telegram (sucesso) OU branch on-error → Telegram (falha).

## Provisionamento .env via n8n

O `.env` no VPS é gerado pelo n8n a partir de credenciais já criptografadas (não vai pro repo). Workflow auxiliar `setup-<nome>-env`:

1. Lê credentials (`<nome>-creds`) no n8n.
2. Escreve `/opt/automacoes/<nome>/.env` via Execute Command.
3. `chmod 600` + `chown root:root`.

Esse workflow roda 1×, manualmente, depois do `docker build`. Pode ser disparado pelo comando Telegram `/setup-<nome>`.
