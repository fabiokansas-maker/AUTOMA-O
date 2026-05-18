#!/usr/bin/env python3
"""Pipeline diário Jarvis Emprego.

Fluxo:
1. Lê perfil/CV (obsidian-bridge/).
2. Coleta vagas das fontes free: Gupy, RemoteOK, Indeed RSS.
3. Filtra geografia (raio ~30km Diadema + remoto BR) e data (últimos 7 dias).
4. Pontua via Gemini 2.5 Flash.
5. Envia relatório no Telegram (chunks ≤4096 chars).
6. Salva snapshot em snapshots/YYYY-MM-DDTHHMM.json.

Configurável só via env vars (GitHub Secrets):
- TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GEMINI_API_KEY
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SNAPSHOTS = REPO / "snapshots"
PROFILE = REPO / "obsidian-bridge" / "perfil.md"
CV = REPO / "obsidian-bridge" / "curriculo.md"

DIADEMA_LAT, DIADEMA_LON = -23.6856, -46.6228
RADIUS_KM = 30.0
DAYS_BACK = 7

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

UA = "Mozilla/5.0 (compatible; Jarvis-Emprego/1.0; +github.com/fabiokansas-maker/automa-o)"


def http_get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json,text/xml,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def http_post(url: str, data: dict, timeout: int = 60) -> dict:
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "User-Agent": UA}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# Centroides aproximados das principais cidades-alvo
CITY_COORDS = {
    "diadema": (-23.6856, -46.6228),
    "são paulo": (-23.5505, -46.6333),
    "sao paulo": (-23.5505, -46.6333),
    "são bernardo do campo": (-23.6939, -46.5658),
    "sao bernardo do campo": (-23.6939, -46.5658),
    "santo andré": (-23.6633, -46.5306),
    "santo andre": (-23.6633, -46.5306),
    "são caetano do sul": (-23.6189, -46.5572),
    "sao caetano do sul": (-23.6189, -46.5572),
    "mauá": (-23.6678, -46.4614),
    "maua": (-23.6678, -46.4614),
    "ribeirão pires": (-23.7128, -46.4136),
    "ribeirao pires": (-23.7128, -46.4136),
    "guarulhos": (-23.4628, -46.5333),
    "osasco": (-23.5325, -46.7919),
    "barueri": (-23.5106, -46.8761),
    "jundiaí": (-23.1864, -46.8842),
    "jundiai": (-23.1864, -46.8842),
    "campinas": (-22.9099, -47.0626),
    "cotia": (-23.6039, -46.9189),
    "taboão da serra": (-23.6258, -46.7919),
    "taboao da serra": (-23.6258, -46.7919),
    "embu": (-23.6489, -46.8519),
    "itapecerica da serra": (-23.7172, -46.8500),
}


def location_fit(city: str | None, state: str | None, remote: bool) -> tuple[str, float | None]:
    """Returns ('within'|'remote'|'outside'|'unknown', distance_km|None)."""
    if remote:
        return "remote", None
    if not city:
        return "unknown", None
    key = city.strip().lower()
    coords = CITY_COORDS.get(key)
    if not coords:
        return "unknown", None
    dist = haversine_km(DIADEMA_LAT, DIADEMA_LON, coords[0], coords[1])
    return ("within" if dist <= RADIUS_KM else "outside"), dist


# ============================== CONECTORES ==============================

def fetch_gupy(keywords: list[str], since: datetime) -> list[dict]:
    out: dict[int, dict] = {}
    for kw in keywords:
        for offset in (0, 10):
            qs = urllib.parse.urlencode({"name": kw, "limit": 10, "offset": offset})
            try:
                raw = http_get(f"https://portal.api.gupy.io/api/v1/jobs?{qs}")
                data = json.loads(raw)
            except Exception as e:
                print(f"[gupy] err kw={kw}: {e}", file=sys.stderr)
                continue
            for j in data.get("data", []):
                jid = j.get("id")
                if not jid or jid in out:
                    continue
                pub = j.get("publishedDate")
                if pub:
                    try:
                        dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                        if dt < since:
                            continue
                    except Exception:
                        pass
                out[jid] = {
                    "source": "gupy",
                    "external_id": str(jid),
                    "title": j.get("name", ""),
                    "company": j.get("careerPageName", ""),
                    "city": j.get("city"),
                    "state": j.get("state"),
                    "remote": bool(j.get("isRemoteWork")),
                    "url": j.get("jobUrl", ""),
                    "published": pub,
                    "description": (j.get("description") or "")[:1500],
                }
            time.sleep(0.3)
    return list(out.values())


def fetch_remoteok(keywords: list[str], since: datetime) -> list[dict]:
    try:
        raw = http_get("https://remoteok.com/api")
        data = json.loads(raw)
    except Exception as e:
        print(f"[remoteok] err: {e}", file=sys.stderr)
        return []
    out: dict[str, dict] = {}
    kw_lower = [k.lower() for k in keywords]
    for item in data[1:] if data else []:
        jid = str(item.get("id") or "")
        if not jid:
            continue
        title = (item.get("position") or "")
        desc = (item.get("description") or "")
        tags = " ".join(item.get("tags") or [])
        haystack = f"{title} {desc} {tags}".lower()
        if not any(k in haystack for k in kw_lower):
            continue
        dt_str = item.get("date") or ""
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            if dt < since:
                continue
        except Exception:
            pass
        out[jid] = {
            "source": "remoteok",
            "external_id": jid,
            "title": title,
            "company": item.get("company") or "",
            "city": None,
            "state": None,
            "remote": True,
            "url": item.get("url") or item.get("apply_url") or "",
            "published": dt_str,
            "description": re.sub(r"<[^>]+>", " ", desc)[:1500],
        }
    return list(out.values())


def fetch_indeed_rss(keywords: list[str], since: datetime) -> list[dict]:
    out: dict[str, dict] = {}
    for kw in keywords[:4]:
        qs = urllib.parse.urlencode({"q": kw, "l": "São Paulo, SP", "fromage": str(DAYS_BACK)})
        try:
            raw = http_get(f"https://br.indeed.com/rss?{qs}").decode("utf-8", "ignore")
        except Exception as e:
            print(f"[indeed] err kw={kw}: {e}", file=sys.stderr)
            continue
        for m in re.finditer(r"<item>([\s\S]*?)</item>", raw):
            block = m.group(1)
            def tag(t: str) -> str:
                mm = re.search(rf"<{t}[^>]*>([\s\S]*?)</{t}>", block, re.I)
                return unescape((mm.group(1) if mm else "").replace("<![CDATA[", "").replace("]]>", "")).strip()
            link = tag("link")
            if not link:
                continue
            jid_m = re.search(r"jk=([a-f0-9]+)", link)
            jid = jid_m.group(1) if jid_m else link
            if jid in out:
                continue
            title_raw = tag("title")
            # Indeed RSS title = "Title - Company - City, State"
            parts = title_raw.rsplit(" - ", 2)
            title = parts[0] if parts else title_raw
            company = parts[1] if len(parts) >= 3 else ""
            loc = parts[2] if len(parts) >= 3 else ""
            city = loc.split(",")[0].strip() if loc else None
            state = loc.split(",")[1].strip() if "," in loc else None
            pub_str = tag("pubDate")
            try:
                dt = datetime.strptime(pub_str, "%a, %d %b %Y %H:%M:%S %Z")
                dt = dt.replace(tzinfo=timezone.utc)
                if dt < since:
                    continue
            except Exception:
                dt = None
            out[jid] = {
                "source": "indeed",
                "external_id": jid,
                "title": title,
                "company": company,
                "city": city,
                "state": state,
                "remote": "remoto" in title_raw.lower(),
                "url": link,
                "published": pub_str,
                "description": tag("description")[:1500],
            }
        time.sleep(0.3)
    return list(out.values())


# ============================== SCORING ==============================

SCORING_PROMPT = """Você é analista de RH sênior em Controladoria/FP&A no Brasil. Avalie objetivamente CADA vaga vs o candidato. Seja crítico e honesto.

=== CANDIDATO ===
{profile}

=== VAGAS ===
{vagas_json}

Para CADA vaga, retorne:
- id (string igual ao external_id da vaga)
- score (0-100; 90+ perfeito, 70-89 bom, 50-69 parcial, <50 descarta)
- match_summary (1-2 frases PT-BR)
- requirements_met (array curto)
- gaps (array curto)
- salary_fit ("within"|"below"|"above"|"unknown", min R$5k)
- recommend_apply (bool: true SE score>=65 E salary_fit não for "below")
- reason_not_apply (string vazia se recommend_apply=true; senão explica em 1 frase por que pular)

Retorne SOMENTE JSON válido com chave "vagas": {{"vagas": [<obj1>, ...]}}"""


def score_with_gemini(profile: str, vagas: list[dict]) -> list[dict]:
    """Score vagas in chunks of 8 to keep response manageable."""
    if not vagas:
        return []
    if not GEMINI_KEY:
        print("[gemini] GEMINI_API_KEY missing — skipping scoring", file=sys.stderr)
        return []

    results: list[dict] = []
    chunk_size = 8
    for i in range(0, len(vagas), chunk_size):
        chunk = vagas[i : i + chunk_size]
        compact = [
            {
                "external_id": v["external_id"],
                "title": v["title"],
                "company": v["company"],
                "city": v.get("city"),
                "state": v.get("state"),
                "remote": v.get("remote", False),
                "description": v["description"][:1200],
            }
            for v in chunk
        ]
        prompt = SCORING_PROMPT.format(profile=profile[:3500], vagas_json=json.dumps(compact, ensure_ascii=False))
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
                "maxOutputTokens": 4096,
            },
        }
        try:
            resp = http_post(url, body, timeout=120)
            text = resp.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
            parsed = json.loads(text)
            results.extend(parsed.get("vagas", []))
        except Exception as e:
            print(f"[gemini] err chunk {i}: {e}", file=sys.stderr)
            for v in chunk:
                results.append(
                    {
                        "id": v["external_id"],
                        "score": 0,
                        "match_summary": f"Erro no scoring: {e}",
                        "requirements_met": [],
                        "gaps": [],
                        "salary_fit": "unknown",
                        "recommend_apply": False,
                        "reason_not_apply": "Falha ao avaliar (erro de API)",
                    }
                )
        time.sleep(1)
    return results


# ============================== TELEGRAM ==============================

def tg_send(text: str) -> None:
    if not (TELEGRAM_TOKEN and TELEGRAM_CHAT):
        print("[telegram] credentials missing", file=sys.stderr)
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    # Telegram limit ~4096 chars
    for i in range(0, len(text), 4000):
        chunk = text[i : i + 4000]
        try:
            http_post(
                url,
                {
                    "chat_id": TELEGRAM_CHAT,
                    "text": chunk,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )
        except Exception as e:
            print(f"[telegram] send err: {e}", file=sys.stderr)
        time.sleep(0.3)


def html_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_report(vagas: list[dict], scores_by_id: dict[str, dict], run_label: str) -> str:
    now = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-3)))
    apply_list: list[str] = []
    skip_list: list[str] = []

    for v in sorted(vagas, key=lambda x: -scores_by_id.get(x["external_id"], {}).get("score", 0)):
        s = scores_by_id.get(v["external_id"], {})
        score = s.get("score", 0)
        loc_fit, dist = location_fit(v.get("city"), v.get("state"), v.get("remote", False))
        loc_label = "remoto" if loc_fit == "remote" else (v.get("city") or "?")
        if dist is not None:
            loc_label = f"{loc_label} ({dist:.0f}km)"
        title = html_escape(v["title"][:80])
        company = html_escape(v["company"][:50])
        url = v["url"]
        src = v["source"]
        summary = html_escape(s.get("match_summary", "")[:200])
        reason = html_escape(s.get("reason_not_apply", "")[:200])

        if s.get("recommend_apply") and loc_fit != "outside":
            block = (
                f"✅ <b>{score}/100</b> · {title}\n"
                f"   {company} · {loc_label} · {src}\n"
                f"   {summary}\n"
                f'   <a href="{url}">Candidatar</a>\n'
            )
            apply_list.append(block)
        else:
            why = reason or summary or "score baixo"
            if loc_fit == "outside":
                why = f"fora do raio ({dist:.0f}km) — {why}"
            block = (
                f"❌ <b>{score}/100</b> · {title}\n"
                f"   {company} · {loc_label} · {src}\n"
                f"   Pula: {why}\n"
                f'   <a href="{url}">Ver mesmo assim</a>\n'
            )
            skip_list.append(block)

    header = (
        f"🤖 <b>Jarvis Emprego — {run_label}</b>\n"
        f"📅 {now.strftime('%Y-%m-%d %H:%M')} BRT\n"
        f"🔍 {len(vagas)} vagas avaliadas · ✅ {len(apply_list)} pra candidatar · ❌ {len(skip_list)} pra pular\n\n"
    )
    body = ""
    if apply_list:
        body += "═══ <b>CANDIDATAR</b> ═══\n\n" + "\n".join(apply_list) + "\n"
    if skip_list:
        body += "═══ <b>PULAR</b> ═══\n\n" + "\n".join(skip_list)
    if not (apply_list or skip_list):
        body = "Nada novo nas últimas 7 dias."
    return header + body


# ============================== MAIN ==============================

def main() -> int:
    run_label = sys.argv[1] if len(sys.argv) > 1 else "manual"
    keywords = [
        "controladoria",
        "fp&a",
        "planejamento financeiro",
        "analista financeiro",
        "fechamento contábil",
        "analista de custos",
    ]
    since = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)

    print(f"[main] run={run_label} since={since.isoformat()}", file=sys.stderr)

    all_vagas: list[dict] = []
    all_vagas.extend(fetch_gupy(keywords, since))
    all_vagas.extend(fetch_remoteok(keywords, since))
    all_vagas.extend(fetch_indeed_rss(keywords, since))
    print(f"[main] coleta bruta: {len(all_vagas)}", file=sys.stderr)

    # Filtra geografia
    kept: list[dict] = []
    for v in all_vagas:
        loc_fit, dist = location_fit(v.get("city"), v.get("state"), v.get("remote", False))
        v["_location_fit"] = loc_fit
        v["_distance_km"] = dist
        # Aceita: dentro do raio, remoto, ou unknown (LLM avalia)
        if loc_fit != "outside":
            kept.append(v)
    print(f"[main] após filtro geo: {len(kept)}", file=sys.stderr)

    # Pega top 20 (mais recentes, ordenando por publishedDate)
    def pub_key(v: dict):
        p = v.get("published") or ""
        return p
    kept.sort(key=pub_key, reverse=True)
    kept = kept[:20]

    profile = PROFILE.read_text(encoding="utf-8") if PROFILE.exists() else ""
    scores = score_with_gemini(profile, kept)
    scores_by_id = {s["id"]: s for s in scores if "id" in s}

    report = format_report(kept, scores_by_id, run_label)
    print(report, file=sys.stderr)
    tg_send(report)

    # Snapshot
    SNAPSHOTS.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M")
    out = SNAPSHOTS / f"{stamp}-{run_label}.json"
    out.write_text(
        json.dumps(
            {
                "run": run_label,
                "ts": datetime.now(timezone.utc).isoformat(),
                "raw_count": len(all_vagas),
                "kept_count": len(kept),
                "scores": scores_by_id,
                "vagas": kept,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[main] snapshot: {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
