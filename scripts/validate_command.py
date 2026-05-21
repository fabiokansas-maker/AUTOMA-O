"""Valida um comando antes de o ChatGPT gravar no Sheet.

Uso:
    python scripts/validate_command.py '{"target_system":"vpsops","action":"healthcheck","payload_json":"{}"}'

Exit code 0 = válido. Imprime o comando completo (com command_id e timestamps).
Exit code 1 = inválido. Imprime o motivo.
"""

from __future__ import annotations

import json
import pathlib
import sys
import uuid
from datetime import datetime, timezone


SCHEMA = json.loads((pathlib.Path(__file__).parent.parent / "sheets" / "schema.json").read_text())
ACTIONS = set(SCHEMA["actions_catalog"])
TARGETS = set(SCHEMA["tabs"]["commands"]["enums"]["target_system"])
SOURCES = set(SCHEMA["tabs"]["commands"]["enums"]["source"])


def validate(raw: dict) -> dict:
    errors = []

    target = raw.get("target_system")
    action = raw.get("action")
    source = raw.get("source", "chatgpt")
    payload = raw.get("payload_json", "{}")
    priority = raw.get("priority", 3)

    if target not in TARGETS:
        errors.append(f"target_system inválido: {target!r}")
    if action not in ACTIONS:
        errors.append(f"action inválido: {action!r}")
    if source not in SOURCES:
        errors.append(f"source inválido: {source!r}")
    try:
        json.loads(payload)
    except Exception as e:
        errors.append(f"payload_json não é JSON: {e}")
    if not (1 <= int(priority) <= 5):
        errors.append(f"priority fora de 1..5: {priority}")

    if errors:
        raise ValueError("; ".join(errors))

    return {
        "command_id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "target_system": target,
        "action": action,
        "payload_json": payload,
        "priority": priority,
        "status": "new",
        "requires_approval": "",
        "approved": "",
        "result_id": "",
        "notes": raw.get("notes", ""),
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("uso: validate_command.py '<json>'", file=sys.stderr)
        sys.exit(2)
    try:
        cmd = validate(json.loads(sys.argv[1]))
    except ValueError as e:
        print(f"INVALID: {e}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(cmd, ensure_ascii=False, indent=2))
