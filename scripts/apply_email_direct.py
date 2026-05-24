"""Apply A4 — email direto pra RH da empresa quando ATS é inacessível.

Trigger: vaga com `_recommend=true` AND `_score>=70` AND source NÃO coberto por
caminho dedicado (workday-natura / gupy-* / gupy / email recrutadora).

Estratégia:
1. Carrega mapping persistido `infra/company_rh_emails.json`.
2. Se empresa já tem email cached → usa.
3. Senão → WebFetch em /trabalhe-conosco|/carreiras|/rh|/contato; regex
   mailto:.*@.* filtrando rh/recrutamento/carreiras/talent/jobs.
4. Se achou → salva mapping (com _verified=false) e envia.
5. Se não achou → status="no_email_found" + alerta Telegram pro usuário.

Dedupe 30 dias por vaga_id.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RH_EMAILS_JSON = REPO / "infra" / "company_rh_emails.json"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

# Caminhos comuns onde RH/Carreiras costuma listar contato
CAREER_PATHS = (
    "/trabalhe-conosco", "/carreiras", "/careers", "/jobs",
    "/rh", "/recursos-humanos", "/contato", "/contact",
)

# Domínios candidatos para grandes empresas BR (slugs)
COMPANY_DOMAIN_HINT = {
    "shopee": ("shopee.com.br", "careers.shopee.com.br"),
    "mercado libre": ("mercadolivre.com.br",),
    "mercado livre": ("mercadolivre.com.br",),
    "magazine luiza": ("magazineluiza.com.br",),
    "magalu": ("magazineluiza.com.br",),
    "carrefour": ("carrefour.com.br",),
    "bradesco": ("bradesco.com.br",),
    "leroy merlin": ("leroymerlin.com.br",),
    "amazon": ("amazon.com.br",),
    "coca-cola femsa": ("kof.com.mx", "cocacolafemsa.com"),
    "itau": ("itau.com.br",),
    "itaú": ("itau.com.br",),
    "vivo": ("vivo.com.br",),
    "cury": ("cury.net",),
    "prosegur": ("prosegur.com.br",),
}


def _load_mapping() -> dict:
    if RH_EMAILS_JSON.exists():
        try:
            return json.loads(RH_EMAILS_JSON.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_mapping(mapping: dict) -> None:
    RH_EMAILS_JSON.parent.mkdir(parents=True, exist_ok=True)
    RH_EMAILS_JSON.write_text(json.dumps(mapping, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _http_get(url: str, timeout: int = 15) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


EMAIL_RE = re.compile(r"\b([a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,})\b", re.I)
GOOD_LOCAL = ("rh", "recrutamento", "carreiras", "talent", "jobs", "selecao", "seleção", "trabalhe", "vagas")
BAD_LOCAL = ("noreply", "no-reply", "donotreply", "press", "imprensa", "marketing", "sac", "atendimento")


def _discover_email_for(company_slug: str) -> str | None:
    hints = COMPANY_DOMAIN_HINT.get(company_slug.lower())
    if not hints:
        # Try slug.com.br as best-guess
        guess = re.sub(r"\s+", "", company_slug.lower())
        hints = (f"{guess}.com.br",)
    for domain in hints:
        for path in CAREER_PATHS:
            url = f"https://www.{domain}{path}"
            try:
                html = _http_get(url, timeout=12)
            except Exception:
                continue
            found = EMAIL_RE.findall(html)
            scored: list[tuple[int, str]] = []
            for e in found:
                local = e.split("@", 1)[0].lower()
                dom = e.split("@", 1)[1].lower()
                if any(b in local for b in BAD_LOCAL):
                    continue
                if not (domain in dom or dom.endswith(domain.split(".", 1)[-1])):
                    continue
                score = sum(1 for g in GOOD_LOCAL if g in local) * 10
                scored.append((score, e))
            if scored:
                scored.sort(reverse=True)
                return scored[0][1]
            time.sleep(0.3)
    return None


def _normalize_company(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


def get_rh_email(company: str) -> tuple[str | None, str]:
    """Retorna (email|None, source: 'cached'|'discovered'|'not_found')."""
    mapping = _load_mapping()
    key = _normalize_company(company)
    if not key:
        return None, "not_found"
    entry = mapping.get(key)
    if entry and isinstance(entry, dict) and entry.get("email") and not entry.get("_bounced"):
        return entry["email"], "cached"
    addr = _discover_email_for(key)
    if addr:
        mapping[key] = {
            "email": addr,
            "_discovered_at": datetime.now(timezone.utc).isoformat(),
            "_verified": False,
            "_bounced": False,
        }
        _save_mapping(mapping)
        return addr, "discovered"
    # Marca tentativa pra não re-buscar a cada run
    mapping.setdefault(key, {"email": None, "_last_attempt": datetime.now(timezone.utc).isoformat(), "_attempts": 0})
    mapping[key]["_attempts"] = (mapping[key].get("_attempts") or 0) + 1
    mapping[key]["_last_attempt"] = datetime.now(timezone.utc).isoformat()
    _save_mapping(mapping)
    return None, "not_found"


SOURCES_ALREADY_COVERED = {
    "workday-natura",
    "gupy", "gupy-vwbrasil", "gupy-natura",  # cobertos por apply_gupy / apply_workday
}


def apply_email_direct(
    vagas: list[dict],
    profile: str,
    send_smtp_email,
    append_application,
    dedupe_check,
    gen_cover_letter,
    cv_pdf: Path,
    dry_run: bool = False,
) -> list[dict]:
    out: list[dict] = []
    if not cv_pdf.exists():
        print("[email-direct] CV PDF ausente, skip", file=sys.stderr)
        return out

    targets = [
        v for v in vagas
        if v.get("_recommend")
        and v.get("_score", 0) >= 70
        and not v.get("source", "").startswith("gupy")
        and v.get("source") != "workday-natura"
        and v.get("source") != "remoteok"  # remoteok já tem URL apply direto
    ]
    if not targets:
        print("[email-direct] sem alvos elegíveis", file=sys.stderr)
        return out

    for v in targets:
        if dedupe_check("email_direct", "vaga_id", v["external_id"], window_days=30):
            print(f"[email-direct] skip {v['external_id']} (já enviado <30d)", file=sys.stderr)
            continue
        addr, src = get_rh_email(v.get("company", ""))
        rec: dict = {
            "platform": "email_direct",
            "vaga_id": v["external_id"],
            "vaga_title": v["title"],
            "company": v.get("company", ""),
            "url": v.get("url", ""),
            "email_source": src,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
        if not addr:
            rec["status"] = "no_email_found"
            rec["info"] = f"webfetch tentou {len(CAREER_PATHS)} paths, nada encontrado"
            append_application(rec)
            out.append(rec)
            print(f"[email-direct] {v['company']}: sem email RH encontrado", file=sys.stderr)
            continue
        rec["to"] = addr
        cover = gen_cover_letter(profile, [v], audience="empresa")
        if not cover:
            rec["status"] = "failed"
            rec["info"] = "cover letter vazia"
            append_application(rec)
            out.append(rec)
            continue
        subject = f"Candidatura — {v['title']} — Fabio Fernandes"
        body = (
            cover
            + f"\n\nVaga: {v.get('url','')}\n\nCurrículo anexo (PDF).\n\nFabio Fernandes\n(11) 95927-3390\nDiadema-SP"
        )
        if dry_run or os.environ.get("EMAIL_DIRECT_DRY_RUN") == "1":
            rec["status"] = "dry_run"
            rec["info"] = f"would-send to {addr} ({len(body)} chars body, {cv_pdf.stat().st_size} bytes attach)"
            print(f"[email-direct] DRY {v['company']} → {addr}", file=sys.stderr)
        else:
            ok, info = send_smtp_email(addr, subject, body, attach_pdf=cv_pdf)
            rec["status"] = "sent" if ok else "failed"
            rec["info"] = info
            print(f"[email-direct] {v['company']} → {addr}: {rec['status']}", file=sys.stderr)
        append_application(rec)
        out.append(rec)
        time.sleep(5)
    return out
