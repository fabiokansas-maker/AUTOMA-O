"""Triagem do inbox Gmail via IMAP (app password) — M2.

Detecta:
- Novos alertas Indeed (vagas de empresas grandes via email, retorna como discovery)
- Respostas de recrutadoras (Talenses/JPeF/Page/RH/etc) — ALERTA Telegram
- Questionários / próxima etapa (ex: CBRE) — ALERTA Telegram
- Convites de entrevista — ALERTA MÁXIMO Telegram
- Recusas — atualiza applications.json com status=rejected
- Bounces (delivery failure) — marca email RH como inválido em company_rh_emails.json

Sem MCP — usa imaplib stdlib + GMAIL_APP_PASSWORD.
"""
from __future__ import annotations

import email
import imaplib
import json
import os
import re
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RH_EMAILS_JSON = REPO / "infra" / "company_rh_emails.json"

GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
GMAIL_FROM_ADDR = os.environ.get("GMAIL_FROM_ADDR", "fabiokansas@gmail.com")

RECRUITER_DOMAINS = (
    "talenses.com", "jpef.com.br", "apexpartners.com.br",
    "pagepersonnel.com.br", "roberthalf.com.br", "michaelpage.com.br",
    "robertwalters.com.br", "hays.com.br",
)

QUESTIONNAIRE_KEYWORDS = (
    "questionário", "questionario", "teste comportamental", "avaliação", "avaliacao",
    "próxima etapa", "proxima etapa", "etapa do processo", "processo seletivo",
)

INTERVIEW_KEYWORDS = (
    "entrevista", "agendamento de entrevista", "meeting invitation", "encontro",
    "conversa", "bate-papo", "alinhamento", "fit cultural",
)

REJECTION_KEYWORDS = (
    "não fomos", "nao fomos", "infelizmente", "outro candidato",
    "perfil não foi selecionado", "perfil nao foi selecionado",
    "agradecemos seu interesse", "não daremos prosseguimento",
    "nao daremos prosseguimento", "encerramos o processo",
)

CONFIRMATION_KEYWORDS = (
    "recebemos sua candidatura", "candidatura recebida", "application received",
    "thank you for applying", "obrigado por se candidatar", "cadastro realizado",
)


def _imap_connect() -> imaplib.IMAP4_SSL | None:
    if not GMAIL_APP_PASSWORD:
        print("[inbox] GMAIL_APP_PASSWORD ausente — skip triage", file=sys.stderr)
        return None
    try:
        m = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        m.login(GMAIL_FROM_ADDR, GMAIL_APP_PASSWORD)
        m.select("INBOX")
        return m
    except Exception as e:
        print(f"[inbox] login falhou: {e}", file=sys.stderr)
        return None


def _decode(s: str) -> str:
    if not s:
        return ""
    parts = decode_header(s)
    out = []
    for txt, enc in parts:
        if isinstance(txt, bytes):
            try:
                out.append(txt.decode(enc or "utf-8", errors="ignore"))
            except Exception:
                out.append(txt.decode("utf-8", errors="ignore"))
        else:
            out.append(txt)
    return "".join(out)


def _msg_body(msg: email.message.Message) -> tuple[str, str]:
    """Retorna (plain, html)."""
    plain, html = "", ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain" and not plain:
                try:
                    plain = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "ignore")
                except Exception:
                    pass
            elif ct == "text/html" and not html:
                try:
                    html = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "ignore")
                except Exception:
                    pass
    else:
        try:
            txt = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", "ignore")
        except Exception:
            txt = str(msg.get_payload())
        if msg.get_content_type() == "text/html":
            html = txt
        else:
            plain = txt
    return plain, html


def _search(m: imaplib.IMAP4_SSL, criteria: str) -> list[bytes]:
    typ, data = m.search(None, criteria)
    if typ != "OK" or not data or not data[0]:
        return []
    return data[0].split()


def _fetch_msg(m: imaplib.IMAP4_SSL, uid: bytes) -> email.message.Message | None:
    try:
        typ, data = m.fetch(uid, "(RFC822)")
        if typ != "OK" or not data or not data[0]:
            return None
        return email.message_from_bytes(data[0][1])
    except Exception as e:
        print(f"[inbox] fetch err {uid}: {e}", file=sys.stderr)
        return None


def fetch_indeed_email_alerts(since: datetime) -> list[dict]:
    """Parser dos alertas Indeed do inbox (substitui RSS bloqueado)."""
    m = _imap_connect()
    if not m:
        return []
    out: dict[str, dict] = {}
    try:
        date_since = since.strftime("%d-%b-%Y")
        uids = _search(m, f'(FROM "indeed.com" SINCE {date_since})')
        for uid in uids:
            msg = _fetch_msg(m, uid)
            if not msg:
                continue
            subject = _decode(msg.get("Subject", ""))
            company_m = re.search(r"empresas?\s+(.+?)(?:\s+e\s+|$| - )", subject, re.I)
            company = company_m.group(1).strip() if company_m else ""
            _, html = _msg_body(msg)
            if not html:
                continue
            for jm in re.finditer(r'<a[^>]+href="(https?://br\.indeed\.com/(?:rc/clk|viewjob)[^"]+)"[^>]*>([^<]+?)</a>', html):
                link = jm.group(1).split("&amp;")[0].replace("&amp;", "&")
                title = unescape(jm.group(2)).strip()
                if not title or len(title) < 5:
                    continue
                jid_m = re.search(r"jk=([a-f0-9]+)", link)
                jid = jid_m.group(1) if jid_m else link[-40:]
                if jid in out:
                    continue
                pub_str = msg.get("Date", "")
                try:
                    pub_dt = parsedate_to_datetime(pub_str)
                    if pub_dt < since:
                        continue
                except Exception:
                    pass
                out[jid] = {
                    "source": "indeed-email",
                    "external_id": f"indeed-{jid}",
                    "title": title[:120],
                    "company": company or "(Indeed alert)",
                    "city": "São Paulo",
                    "state": "SP",
                    "remote": "remoto" in title.lower() or "remote" in title.lower(),
                    "url": link,
                    "published": pub_str,
                    "description": "",
                }
    finally:
        try:
            m.close()
            m.logout()
        except Exception:
            pass
    return list(out.values())


def triage_inbound(since: datetime) -> list[dict]:
    """Retorna lista de alertas/atualizações detectadas no inbox desde `since`.

    Cada item: {"kind": "...", "urgency": "high|max|low", "title": ..., "snippet": ..., "from": ..., "msg_id": ...}
    """
    m = _imap_connect()
    if not m:
        return []
    alerts: list[dict] = []
    date_since = since.strftime("%d-%b-%Y")
    try:
        # M2.2 Recrutadora respondendo
        for dom in RECRUITER_DOMAINS:
            uids = _search(m, f'(FROM "{dom}" SINCE {date_since} NOT FROM "{GMAIL_FROM_ADDR}")')
            for uid in uids:
                msg = _fetch_msg(m, uid)
                if not msg:
                    continue
                subj = _decode(msg.get("Subject", ""))
                frm = _decode(msg.get("From", ""))
                plain, html = _msg_body(msg)
                snippet = (plain or re.sub(r"<[^>]+>", " ", html))[:300]
                alerts.append({
                    "kind": "recruiter_reply",
                    "urgency": "high",
                    "domain": dom,
                    "subject": subj,
                    "from": frm,
                    "snippet": snippet,
                    "msg_id": msg.get("Message-ID", ""),
                })

        # M2.3 / M2.4 Questionário / Entrevista (subject keyword search)
        uids = _search(m, f'(SINCE {date_since} NOT FROM "{GMAIL_FROM_ADDR}")')
        for uid in uids[-200:]:  # limita ultimos 200 emails da janela
            msg = _fetch_msg(m, uid)
            if not msg:
                continue
            subj = _decode(msg.get("Subject", ""))
            frm = _decode(msg.get("From", "")).lower()
            subj_low = subj.lower()
            plain, html = _msg_body(msg)
            body = (plain or re.sub(r"<[^>]+>", " ", html or ""))
            body_low = body.lower()
            snippet = body[:300]

            # Skip self-noise (indeed alerts handled separately, newsletters)
            if "indeed.com" in frm or "noreply" in frm and "questionário" not in subj_low:
                continue
            if any(d in frm for d in RECRUITER_DOMAINS):
                continue  # já tratado acima

            urgency = None
            kind = None
            if any(k in subj_low or k in body_low[:500] for k in INTERVIEW_KEYWORDS):
                urgency, kind = "max", "interview_invite"
            elif any(k in subj_low for k in QUESTIONNAIRE_KEYWORDS):
                urgency, kind = "high", "questionnaire"
            elif any(k in body_low[:500] for k in REJECTION_KEYWORDS):
                urgency, kind = "low", "rejection"
            elif any(k in body_low[:500] for k in CONFIRMATION_KEYWORDS):
                urgency, kind = "low", "confirmation"
            elif "delivery status notification" in subj_low or "mailer-daemon" in frm:
                urgency, kind = "low", "bounce"

            if kind:
                alerts.append({
                    "kind": kind,
                    "urgency": urgency,
                    "subject": subj,
                    "from": frm,
                    "snippet": snippet,
                    "msg_id": msg.get("Message-ID", ""),
                })
    finally:
        try:
            m.close()
            m.logout()
        except Exception:
            pass
    return alerts


def format_triage_block(alerts: list[dict]) -> str:
    if not alerts:
        return ""
    by_urg: dict[str, list[dict]] = {"max": [], "high": [], "low": []}
    for a in alerts:
        by_urg.setdefault(a.get("urgency", "low"), []).append(a)
    out = ["", "═══ <b>📧 INBOX TRIAGE</b> ═══", ""]
    emoji_by_kind = {
        "interview_invite": "🚨🚨",
        "recruiter_reply": "🚨",
        "questionnaire": "🚨",
        "confirmation": "✅",
        "rejection": "⚠️",
        "bounce": "⚠️",
    }
    for urg in ("max", "high", "low"):
        items = by_urg.get(urg, [])
        if not items:
            continue
        for a in items[:10]:
            em = emoji_by_kind.get(a.get("kind", ""), "•")
            subj = (a.get("subject") or "")[:80].replace("<", "&lt;").replace(">", "&gt;")
            frm = (a.get("from") or "")[:60].replace("<", "&lt;").replace(">", "&gt;")
            snip = (a.get("snippet") or "")[:120].replace("<", "&lt;").replace(">", "&gt;")
            out.append(f"{em} <b>[{a.get('kind','?')}]</b> {subj}")
            out.append(f"   de: {frm}")
            out.append(f"   {snip}")
            out.append("")
    return "\n".join(out)


def mark_bounced_email(addr: str) -> None:
    """Marca endereço como bounced no mapping persistente."""
    mapping: dict = {}
    if RH_EMAILS_JSON.exists():
        try:
            mapping = json.loads(RH_EMAILS_JSON.read_text(encoding="utf-8"))
        except Exception:
            mapping = {}
    for k, v in mapping.items():
        if isinstance(v, dict) and v.get("email", "").lower() == addr.lower():
            v["_bounced"] = True
            v["_bounced_at"] = datetime.now(timezone.utc).isoformat()
    RH_EMAILS_JSON.parent.mkdir(parents=True, exist_ok=True)
    RH_EMAILS_JSON.write_text(json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    since = datetime.now(timezone.utc) - timedelta(days=int(os.environ.get("TRIAGE_DAYS", "7")))
    print("=== INDEED ALERTS ===")
    for v in fetch_indeed_email_alerts(since):
        print(f"- [{v['source']}] {v['title']} @ {v['company']} → {v['url'][:80]}")
    print()
    print("=== TRIAGE ALERTS ===")
    for a in triage_inbound(since):
        print(f"- [{a.get('urgency')}/{a.get('kind')}] {a.get('subject','')[:70]} | {a.get('from','')[:40]}")
