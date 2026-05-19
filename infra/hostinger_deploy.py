#!/usr/bin/env python3
"""Deploy AUTOMA-O stack ao VPS Hostinger via API REST.

Uso:
    export HOSTINGER_API_TOKEN=<token de https://hpanel.hostinger.com/profile/api>
    python3 infra/hostinger_deploy.py

Fluxo:
1. GET /api/vps/v1/virtual-machines — lista VMs, acha srv1621330
2. POST /api/vps/v1/virtual-machines/{id}/docker — envia docker-compose.yml + env
3. GET /api/vps/v1/virtual-machines/{id} — confirma running
4. Telegram ping "stack no ar"

Não precisa SSH. Não precisa terminal. Não precisa clique no painel.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

API_BASE = os.environ.get("HOSTINGER_API_BASE", "https://developers.hostinger.com")
TOKEN = os.environ.get("HOSTINGER_API_TOKEN", "")
TARGET_HOSTNAME = os.environ.get("VPS_HOSTNAME", "srv1621330.hstgr.cloud")
COMPOSE_FILE = Path(__file__).parent / "docker-compose.yml"

ENV_FOR_COMPOSE = [
    "POSTGRES_PASSWORD", "BROWSERLESS_TOKEN", "CONNECTORS_API_KEY",
    "N8N_ENCRYPTION_KEY", "N8N_HOST", "N8N_PROTOCOL", "N8N_WEBHOOK_URL",
    "GEMINI_API_KEY", "OPENAI_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
    "GUPY_EMAIL", "GUPY_PASSWORD", "CAPTCHA_2CAPTCHA_KEY",
]


def api(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "automa-o-deploy/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        body_err = e.read().decode(errors="replace")[:500]
        print(f"[api] {method} {path} -> HTTP {e.code}: {body_err}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"[api] {method} {path} -> {e}", file=sys.stderr)
        raise


def find_vps(hostname: str) -> dict:
    """Lista todas as VMs e acha pelo hostname (parte antes do .hstgr.cloud)."""
    resp = api("GET", "/api/vps/v1/virtual-machines")
    items = resp.get("data") or resp if isinstance(resp, list) else resp.get("data", [])
    short = hostname.split(".")[0]
    for vm in items:
        if vm.get("hostname", "").startswith(short) or str(vm.get("id", "")) in hostname:
            return vm
    raise SystemExit(f"VPS {hostname} não encontrada. VMs disponíveis: {[v.get('hostname') for v in items]}")


def deploy_compose(vm_id: int, compose_yaml: str, env_inline: str) -> dict:
    return api(
        "POST",
        f"/api/vps/v1/virtual-machines/{vm_id}/docker",
        {
            "project_name": "automa-o",
            "content": compose_yaml,
            "environment": env_inline,
        },
    )


def build_env_inline() -> str:
    lines = []
    for k in ENV_FOR_COMPOSE:
        v = os.environ.get(k, "")
        if v:
            lines.append(f"{k}={v}")
    return "\n".join(lines)


def tg_notify(text: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat):
        return
    try:
        urllib.request.urlopen(urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=json.dumps({"chat_id": chat, "text": text}).encode(),
            headers={"Content-Type": "application/json"},
        ), timeout=10)
    except Exception:
        pass


def main() -> int:
    if not TOKEN:
        print("ERRO: HOSTINGER_API_TOKEN não setado.", file=sys.stderr)
        print("Gera em https://hpanel.hostinger.com/profile/api", file=sys.stderr)
        return 1
    if not COMPOSE_FILE.exists():
        print(f"ERRO: {COMPOSE_FILE} não existe.", file=sys.stderr)
        return 1

    print(f"[1/3] Procurando VPS {TARGET_HOSTNAME}...")
    vm = find_vps(TARGET_HOSTNAME)
    vm_id = vm["id"]
    print(f"     achei: id={vm_id} hostname={vm.get('hostname')} state={vm.get('state')}")

    print(f"[2/3] Enviando docker-compose...")
    compose_yaml = COMPOSE_FILE.read_text()
    env_inline = build_env_inline()
    resp = deploy_compose(vm_id, compose_yaml, env_inline)
    print(f"     resp: {json.dumps(resp)[:300]}")

    print(f"[3/3] Aguardando containers iniciarem (60s)...")
    time.sleep(60)
    info = api("GET", f"/api/vps/v1/virtual-machines/{vm_id}")
    state = info.get("state") or info.get("status")
    print(f"     state final: {state}")

    tg_notify(
        f"🚀 Stack AUTOMA-O deployada no VPS\n"
        f"VM: {vm.get('hostname')} (id={vm_id})\n"
        f"state: {state}\n"
        f"Próximo cron: 8h/12h/17h BRT"
    )
    print("OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
