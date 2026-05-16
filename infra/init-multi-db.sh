#!/bin/bash
# Cria DB adicional pro n8n no mesmo Postgres usado pelo AUTOMA-O.
# Roda automaticamente no primeiro start do container (entrypoint scripts dir).
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE n8n;
    GRANT ALL PRIVILEGES ON DATABASE n8n TO $POSTGRES_USER;
EOSQL
