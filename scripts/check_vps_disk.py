#!/usr/bin/env python3
"""Checa uso de disco do VPS Hostinger via API oficial e alerta no Telegram.

Endereça pendência #1 do registry: "Disco da VPS com alerta Hostinger de quota".

Uso (em GitHub Actions cron ou manual):
    HOSTINGER_API_TOKEN=<token de https://hpanel.hostinger.com/profile/api> \
    TELEGRAM_BOT_TOKEN=<...> TELEGRAM_CHAT_ID=<...> \
    python3 scripts/check_vps_disk.py

Comportamento:
- Lista VMs via GET /api/vps/v1/virtual-machines
- Acha a VPS srv1621330 (ou override via VPS_HOSTNAME)
- Lê métricas via GET /api/vps/v1/virtual-machines/{id}/metrics
  (Endpoints alternativos tentados se 404: /usage, /actions, /info)
- Calcula uso de disco em %
- Se >= ALERT_THRESHOLD_PCT (default 80%): manda alerta no Telegram com:
    * uso atual
    * total alocado
    * top 5 paths recomendados pra limpeza (docker images dangling, logs, etc.)

Sem dependências externas — só urllib + json.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

API_BASE = os.environ.get("HOSTINGER_API_BASE", "https://developers.hostinger.com")
TOKEN = os.environ.get("HOSTINGER_API_TOKEN", "")
TARGET = os.environ.get("VPS_HOSTNAME", "srv1621330")
ALERT_THRESHOLD = float(os.environ.get("ALERT_THRESHOLD_PCT", "80"))

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")


def api(path: str) -> dict:
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json",
            "User-Agent": "automa-o-disk-check/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def find_vps() -> dict:
    resp = api("/api/vps/v1/virtual-machines")
    items = resp.get("data") if isinstance(resp, dict) else resp
    if not items:
        raise SystemExit("Sem VMs retornadas pela API.")
    for vm in items:
        host = vm.get("hostname", "")
        if host.startswith(TARGET) or str(vm.get("id", "")) == TARGET:
            return vm
    raise SystemExit(f"VPS {TARGET} não encontrada. Disponíveis: {[v.get('hostname') for v in items]}")


def fetch_disk_metrics(vm_id: int) -> dict:
    """Tenta endpoints prováveis até pegar dados de disco."""
    candidates = [
        f"/api/vps/v1/virtual-machines/{vm_id}/metrics",
        f"/api/vps/v1/virtual-machines/{vm_id}/usage",
        f"/api/vps/v1/virtual-machines/{vm_id}",
    ]
    last_err = None
    for p in candidates:
        try:
            data = api(p)
            # Achata possíveis estruturas
            blob = json.dumps(data).lower()
            if "disk" in blob or "storage" in blob:
                return {"endpoint": p, "data": data}
        except Exception as e:
            last_err = e
            continue
    raise SystemExit(f"Nenhum endpoint retornou métrica de disco. Último erro: {last_err}")


def parse_disk(metrics: dict) -> tuple[float, float, float]:
    """Retorna (usado_gb, total_gb, pct). Tolera shapes diferentes da API."""
    data = metrics["data"]

    def search(obj, *keys):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k.lower() in [x.lower() for x in keys]:
                    return v
                r = search(v, *keys)
                if r is not None:
                    return r
        elif isinstance(obj, list):
            for it in obj:
                r = search(it, *keys)
                if r is not None:
                    return r
        return None

    used = search(data, "disk_used", "used", "storageUsed", "usedDisk", "disk_usage")
    total = search(data, "disk_total", "total", "storageTotal", "totalDisk", "disk", "disk_size")
    pct = search(data, "disk_percentage", "diskPct", "percent", "usage_percent")

    def to_gb(v):
        if v is None:
            return None
        v = float(v)
        # Heurística: se > 10000 deve estar em MB; se > 10_000_000 em bytes
        if v > 10_000_000:
            return v / (1024 ** 3)
        if v > 10_000:
            return v / 1024
        return v

    used_gb = to_gb(used)
    total_gb = to_gb(total)
    if pct is not None:
        pct = float(pct)
    elif used_gb and total_gb:
        pct = (used_gb / total_gb) * 100

    return used_gb or 0, total_gb or 0, pct or 0


def tg_alert(text: str) -> None:
    if not (TELEGRAM_TOKEN and TELEGRAM_CHAT):
        print("[telegram] credenciais ausentes — log only.")
        return
    body = json.dumps({"chat_id": TELEGRAM_CHAT, "text": text, "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=10)


def main() -> int:
    if not TOKEN:
        print("ERRO: HOSTINGER_API_TOKEN ausente.", file=sys.stderr)
        return 1
    vm = find_vps()
    vm_id = vm["id"]
    print(f"[disk-check] VPS id={vm_id} hostname={vm.get('hostname')} state={vm.get('state')}")

    metrics = fetch_disk_metrics(vm_id)
    used_gb, total_gb, pct = parse_disk(metrics)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"[disk-check] {used_gb:.1f}GB / {total_gb:.1f}GB ({pct:.1f}%) via {metrics['endpoint']}")

    if pct >= ALERT_THRESHOLD:
        msg = (
            f"⚠️ <b>Disco VPS crítico</b>\n"
            f"{vm.get('hostname')} · {used_gb:.1f}/{total_gb:.1f}GB (<b>{pct:.1f}%</b>)\n"
            f"check: {now}\n\n"
            f"<b>Limpeza sugerida (do mais barato):</b>\n"
            f"1. <code>docker system prune -af --volumes</code> (imagens/volumes dangling)\n"
            f"2. <code>journalctl --vacuum-time=3d</code> (logs systemd antigos)\n"
            f"3. <code>du -sh /var/lib/docker/containers/*/*log</code> (logs de containers)\n"
            f"4. <code>apt-get clean</code>\n"
            f"5. ver Drive backups antigos em /opt/* /home/*"
        )
        tg_alert(msg)
        print("[disk-check] alerta enviado.")
        return 2

    print("[disk-check] OK, abaixo do threshold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
