"""Handlers de referência para os comandos /bridge do Jarvis.

Use como módulo dentro do Jarvis. Depende de:
- gspread (auth via service account)
- variáveis de ambiente:
    BRIDGE_SHEET_ID       id do Google Sheet
    BRIDGE_SA_JSON        path do JSON da service account
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

import gspread


SHEET_ID = os.environ["BRIDGE_SHEET_ID"]
SA_JSON = os.environ["BRIDGE_SA_JSON"]


def _client():
    return gspread.service_account(filename=SA_JSON).open_by_key(SHEET_ID)


def _now():
    return datetime.now(timezone.utc).isoformat()


def cmd_status() -> str:
    sh = _client()
    commands = sh.worksheet("commands").get_all_records()
    pending = sh.worksheet("pending_approval").get_all_records()

    counts = {"new": 0, "running": 0, "done": 0, "error": 0, "blocked": 0}
    last = None
    for row in commands:
        st = row.get("status", "")
        counts[st] = counts.get(st, 0) + 1
        last = row

    lines = [
        "[BRIDGE STATUS]",
        f"new:               {counts.get('new', 0)}",
        f"running:           {counts.get('running', 0)}",
        f"awaiting_approval: {len(pending)}",
        f"done (total):      {counts.get('done', 0)}",
        f"error (total):     {counts.get('error', 0)}",
        f"blocked (total):   {counts.get('blocked', 0)}",
    ]
    if last:
        lines.append(
            f"last_command:      {last['command_id']} · "
            f"{last['action']}@{last['target_system']} · {last['status']}"
        )
    return "\n".join(lines)


def cmd_pendentes() -> str:
    sh = _client()
    rows = sh.worksheet("pending_approval").get_all_records()
    if not rows:
        return "[PENDÊNCIAS] (vazio)"
    rows.sort(key=lambda r: r.get("asked_at", ""), reverse=True)
    lines = ["[PENDÊNCIAS]"]
    for i, r in enumerate(rows, 1):
        lines.append(
            f"{i}. {r['command_id']}  action={r['action']}  "
            f"target={r['target_system']}  asked_at={r['asked_at']}"
        )
    lines.append("use:  /bridge aprovar <command_id>")
    return "\n".join(lines)


def cmd_aprovar(command_id: str) -> str:
    sh = _client()
    commands = sh.worksheet("commands")
    pending = sh.worksheet("pending_approval")
    logs = sh.worksheet("logs")

    rows = commands.get_all_records()
    target_row_idx = None
    target_row = None
    for i, r in enumerate(rows, start=2):  # header in row 1
        if r["command_id"] == command_id:
            target_row_idx = i
            target_row = r
            break
    if not target_row:
        return f"[ERRO] {command_id} não encontrado em commands"

    headers = commands.row_values(1)
    approved_col = headers.index("approved") + 1
    status_col = headers.index("status") + 1
    commands.update_cell(target_row_idx, approved_col, "TRUE")
    commands.update_cell(target_row_idx, status_col, "new")

    pending_rows = pending.get_all_records()
    for i, r in enumerate(pending_rows, start=2):
        if r["command_id"] == command_id:
            pending.delete_rows(i)
            break

    logs.append_row([
        str(uuid.uuid4()),
        _now(),
        "audit",
        command_id,
        "approved_by_jarvis",
        f"action={target_row['action']} target={target_row['target_system']}",
    ])

    return (
        f"[APROVADO] {command_id}  "
        f"action={target_row['action']}  target={target_row['target_system']}\n"
        "n8n vai pegar na próxima rodada (até 30s)"
    )


def cmd_resultado(command_id: str) -> str:
    sh = _client()
    rows = sh.worksheet("results").get_all_records()
    match = next((r for r in rows if r.get("command_id") == command_id), None)
    if not match:
        return f"[RESULTADO] {command_id}: ainda sem resultado"
    return (
        f"[RESULTADO] {command_id}\n"
        f"exit_code: {match.get('exit_code')}\n"
        f"summary:   {match.get('summary')}\n"
        f"drive:     {match.get('drive_link') or '-'}\n"
        f"finished:  {match.get('finished_at')}"
    )


DISPATCH = {
    "status": lambda *_: cmd_status(),
    "pendentes": lambda *_: cmd_pendentes(),
    "aprovar": lambda args: cmd_aprovar(args[0]) if args else "[ERRO] uso: /bridge aprovar <command_id>",
    "resultado": lambda args: cmd_resultado(args[0]) if args else "[ERRO] uso: /bridge resultado <command_id>",
}


def handle(line: str) -> str:
    parts = line.strip().split()
    if not parts or parts[0] != "/bridge" or len(parts) < 2:
        return "[ERRO] uso: /bridge {status|pendentes|aprovar|resultado}"
    sub = parts[1]
    args = parts[2:]
    fn = DISPATCH.get(sub)
    if not fn:
        return f"[ERRO] subcomando desconhecido: {sub}"
    return fn(args)
