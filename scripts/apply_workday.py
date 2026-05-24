"""Apply automático via Workday CXS API (Natura tenant).

Workday tem flow específico: GET job → CSRF → login/createAccount → POST /apply.
Fluxo é frágil; sempre que falhar, cai pra fallback de email pra
talentacquisition@natura.com com a cover letter Gemini + CV anexo.
"""
from __future__ import annotations

import base64
import json
import os
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CANDIDATE = {
    "firstName": "Fabio",
    "lastName": "Fernandes",
    "email": "fabiokansas+natura@gmail.com",
    "phone": "+5511959273390",
    "address1": "Rua Caboclos, 99",
    "city": "Diadema",
    "state": "SP",
    "postalCode": "09930-770",
    "country": "BR",
}

NATURA_FALLBACK_EMAIL = "talentacquisition@natura.com"
NATURA_PASSWORD = os.environ.get("WORKDAY_NATURA_PASSWORD", "")


def _http(url: str, body: dict | None = None, headers: dict | None = None, timeout: int = 30) -> tuple[int, dict, dict]:
    """Retorna (status, json_body, response_headers). Não levanta — caller decide."""
    h = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "pt-BR,en;q=0.7",
    }
    if headers:
        h.update(headers)
    data = None
    if body is not None:
        h["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=h, method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "ignore")
            try:
                return r.status, json.loads(raw) if raw else {}, dict(r.headers)
            except Exception:
                return r.status, {"_raw": raw[:500]}, dict(r.headers)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "ignore")
        try:
            return e.code, json.loads(raw) if raw else {}, dict(e.headers or {})
        except Exception:
            return e.code, {"_raw": raw[:500]}, dict(e.headers or {})
    except Exception as e:
        return 0, {"_err": str(e)[:200]}, {}


def _apply_one_workday(vaga: dict, cv_b64: str, password: str) -> dict:
    """Tenta sequência REST Natura/Workday. Retorna dict com status/info."""
    tenant = "natura"
    site = "NaturaCarreiras"
    external_path = vaga.get("external_id", "").split("-", 1)[-1]  # ex: "/job/Brasil/.../R-12345"
    if not external_path.startswith("/"):
        external_path = "/" + external_path
    base = f"https://{tenant}.wd5.myworkdayjobs.com/wday/cxs/{tenant}/{site}"

    # 1. GET job detail → captura cookies / CSRF (Workday sets via Set-Cookie)
    status, _, hdrs = _http(f"{base}/job{external_path}")
    if status != 200:
        return {"status": "failed", "step": "get_job", "http": status}
    cookie = hdrs.get("Set-Cookie", "")
    csrf = ""
    for part in cookie.split(","):
        if "CSRF_TOKEN" in part:
            csrf = part.split("CSRF_TOKEN=")[-1].split(";")[0]

    # 2. Tentar login. Se 404/401, criar conta.
    auth_headers = {"X-CSRF-Token": csrf, "Cookie": cookie}
    login_body = {"username": CANDIDATE["email"], "password": password}
    status, _, hdrs2 = _http(f"{base}/login", body=login_body, headers=auth_headers)
    if status in (401, 404):
        # Cria conta
        create_body = {
            "username": CANDIDATE["email"],
            "email": CANDIDATE["email"],
            "password": password,
            "passwordConfirm": password,
        }
        status_c, _, hdrs2 = _http(f"{base}/createAccount", body=create_body, headers=auth_headers)
        if status_c not in (200, 201):
            return {"status": "failed", "step": "create_account", "http": status_c}
    elif status != 200:
        return {"status": "failed", "step": "login", "http": status}

    session_cookie = hdrs2.get("Set-Cookie", cookie)

    # 3. POST apply
    apply_body = {
        "applyData": {
            **CANDIDATE,
            "resume": {"contents": cv_b64, "name": "Curriculo_Fabio.pdf", "contentType": "application/pdf"},
        }
    }
    status, body, _ = _http(
        f"{base}/job{external_path}/apply",
        body=apply_body,
        headers={"X-CSRF-Token": csrf, "Cookie": session_cookie},
    )
    if status not in (200, 201, 202):
        return {"status": "failed", "step": "apply", "http": status, "info": str(body)[:200]}
    app_id = body.get("applicationId") or body.get("id") or "unknown"
    return {"status": "sent", "application_id": app_id, "step": "apply", "http": status}


def apply_natura_top(
    vagas: list[dict],
    profile: str,
    from_addr: str,
    send_smtp_email,
    append_application,
    dedupe_check,
    gen_cover_letter,
    cv_pdf: Path,
) -> list[dict]:
    """Aplica nas top 3 Natura via Workday API + fallback email se algum step falhar."""
    out: list[dict] = []
    if not cv_pdf.exists():
        print("[workday] CV PDF não encontrado, skip", file=sys.stderr)
        return out

    targets = [
        v for v in vagas
        if v.get("source") == "workday-natura"
        and v.get("_recommend")
        and v.get("_score", 0) >= 70
    ][:3]
    if not targets:
        print("[workday] sem vagas Natura com score >=70 e recommend_apply", file=sys.stderr)
        return out

    cv_bytes = cv_pdf.read_bytes()
    cv_b64 = base64.b64encode(cv_bytes).decode("ascii")
    password = NATURA_PASSWORD or secrets.token_urlsafe(16)
    if not NATURA_PASSWORD:
        print(f"[workday] WORKDAY_NATURA_PASSWORD ausente, gerando temporário (não persiste): {password}", file=sys.stderr)

    for v in targets:
        if dedupe_check("workday", "vaga_id", v["external_id"], window_days=30):
            print(f"[workday] skip {v['external_id']} (já aplicado <30d)", file=sys.stderr)
            continue
        rec: dict = {
            "platform": "workday",
            "tenant": "natura",
            "vaga_id": v["external_id"],
            "vaga_title": v["title"],
            "url": v["url"],
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            r = _apply_one_workday(v, cv_b64, password)
            rec.update(r)
        except Exception as e:
            rec["status"] = "failed"
            rec["info"] = f"exception: {e}"
        # Fallback email se não SENT
        if rec.get("status") != "sent":
            cover = gen_cover_letter(profile, [v], audience="empresa")
            if cover:
                subject = f"Candidatura — {v['title']} — Fabio Fernandes"
                body = (
                    cover
                    + f"\n\nVaga: {v['url']}\n\nCurrículo anexo.\n\nFabio Fernandes\n(11) 95927-3390\nDiadema-SP"
                )
                ok, info = send_smtp_email(NATURA_FALLBACK_EMAIL, subject, body, attach_pdf=cv_pdf)
                rec["fallback_email"] = "sent" if ok else "failed"
                rec["fallback_info"] = info
                if ok:
                    rec["status"] = "fallback_sent"
        append_application(rec)
        out.append(rec)
        print(f"[workday] {v['external_id'][:40]} → {rec.get('status')} ({rec.get('step','-')})", file=sys.stderr)
    return out
