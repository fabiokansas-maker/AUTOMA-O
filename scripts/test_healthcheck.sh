#!/usr/bin/env bash
# Smoke test ponta-a-ponta da bridge.
#
# Pré: BRIDGE_SHEET_ID + BRIDGE_SA_JSON exportados, n8n com o workflow
# ativo, vpsOps respondendo em $VPSOPS_BASE_URL.
#
# O que faz:
# 1. valida comando de healthcheck
# 2. grava na aba commands via Sheets API (usa o helper python)
# 3. aguarda até 90s pela linha em results
# 4. imprime o resultado

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

CMD_JSON=$(python3 "$ROOT/scripts/validate_command.py" \
  '{"target_system":"vpsops","action":"healthcheck","payload_json":"{\"scope\":\"all\"}","source":"manual","notes":"smoke test"}')

COMMAND_ID=$(echo "$CMD_JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin)["command_id"])')

echo "[1/4] comando válido. command_id=$COMMAND_ID"

python3 - <<PY
import gspread, json, os
sh = gspread.service_account(filename=os.environ["BRIDGE_SA_JSON"]).open_by_key(os.environ["BRIDGE_SHEET_ID"])
cmd = json.loads('''$CMD_JSON''')
ws = sh.worksheet("commands")
headers = ws.row_values(1)
row = [cmd.get(h, "") for h in headers]
ws.append_row(row, value_input_option="USER_ENTERED")
print("[2/4] linha gravada na aba commands")
PY

echo "[3/4] aguardando até 90s pelo resultado..."
for i in $(seq 1 18); do
  OUT=$(python3 - <<PY
import gspread, os
sh = gspread.service_account(filename=os.environ["BRIDGE_SA_JSON"]).open_by_key(os.environ["BRIDGE_SHEET_ID"])
for r in sh.worksheet("results").get_all_records():
    if r.get("command_id") == "$COMMAND_ID":
        print(r.get("exit_code"), "|", r.get("summary"))
        break
PY
)
  if [ -n "$OUT" ]; then
    echo "[4/4] resultado: $OUT"
    exit 0
  fi
  sleep 5
done

echo "[FALHA] sem resultado em 90s. confira: n8n workflow ativo, policy permite, vpsOps acessível"
exit 1
