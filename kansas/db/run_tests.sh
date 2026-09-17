#!/usr/bin/env bash
# Sobe um Postgres efêmero, aplica as migrations do Kansas e roda a suíte
# de isolamento. Zero dependência de nuvem, zero clique.
#   uso: bash kansas/db/run_tests.sh
set -euo pipefail

PGBIN="${PGBIN:-$(ls -d /usr/lib/postgresql/*/bin 2>/dev/null | tail -1)}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="${PGDATA_DIR:-/tmp/kansas-pgdata}"
SOCK="${PGSOCK_DIR:-/tmp/kansas-pgrun}"
PORT="${PGPORT:-5433}"
RUNAS="${PG_RUNAS:-}"          # usuário não-root p/ o postgres (ex.: pg)

run() { if [ -n "$RUNAS" ]; then su "$RUNAS" -c "$1"; else bash -c "$1"; fi }

if [ "$(id -u)" = "0" ] && [ -z "$RUNAS" ]; then
  id pg >/dev/null 2>&1 || useradd -m pg
  RUNAS=pg
fi

# Derruba qualquer servidor anterior deste datadir (inclusive órfão de uma
# execução que apagou o diretório por baixo dele) antes de recomeçar.
if [ -n "$RUNAS" ]; then
  su "$RUNAS" -c "$PGBIN/pg_ctl -D $DATA -m immediate -w stop" >/dev/null 2>&1 || true
else
  "$PGBIN/pg_ctl" -D "$DATA" -m immediate -w stop >/dev/null 2>&1 || true
fi
pkill -f "postgres.*-k $SOCK" >/dev/null 2>&1 || true
rm -f "$SOCK"/.s.PGSQL.* 2>/dev/null || true

if [ ! -s "$DATA/PG_VERSION" ] || [ ! -s "$DATA/global/pg_filenode.map" ]; then
  rm -rf "$DATA"; mkdir -p "$DATA" "$SOCK"
  [ -n "$RUNAS" ] && chown -R "$RUNAS" "$DATA" "$SOCK"
  run "$PGBIN/initdb -D $DATA -A trust -U postgres" >/dev/null
fi
mkdir -p "$SOCK"; [ -n "$RUNAS" ] && chown -R "$RUNAS" "$SOCK" || true
run "$PGBIN/pg_ctl -D $DATA -o '-k $SOCK -p $PORT -c listen_addresses=' -l /tmp/kansas-pg.log -w start" >/dev/null 2>&1 || true

export PGHOST="$SOCK" PGPORT="$PORT" PGUSER=postgres
psql -q -d postgres -c "drop database if exists kansas_test" >/dev/null
psql -q -d postgres -c "create database kansas_test"        >/dev/null

for f in tests/00_local_shim.sql 001_agent_core.sql 002_rls_and_api.sql \
         003_agents_seed.sql tests/10_harness.sql tests/20_fixtures.sql; do
  psql -v ON_ERROR_STOP=1 -q -d kansas_test -f "$DIR/$f" >/dev/null 2>&1 \
    || { echo "ERRO ao aplicar $f"; psql -v ON_ERROR_STOP=1 -d kansas_test -f "$DIR/$f"; exit 1; }
done

OUT="$(psql -v ON_ERROR_STOP=1 -q -d kansas_test -f "$DIR/tests/30_isolation_test.sql" 2>&1)"
echo "$OUT" | sed 's/^psql:[^ ]*: //' | grep -E 'PASS|FAIL|ERROR' || true

if echo "$OUT" | grep -qE 'FAIL|ERROR'; then
  echo; echo "RESULTADO: VERMELHO — alguma fronteira de isolamento quebrou."; exit 1
fi
echo; echo "RESULTADO: VERDE — $(echo "$OUT" | grep -c PASS) testes de isolamento passaram."
