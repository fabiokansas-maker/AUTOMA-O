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
import smtplib
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from html import unescape
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SNAPSHOTS = REPO / "snapshots"
PROFILE = REPO / "obsidian-bridge" / "perfil.md"
CV = REPO / "obsidian-bridge" / "curriculo.md"
CV_PDF = REPO / "cv" / "Curriculo_Fabio_Controladoria_0426.pdf"
APPLICATIONS_LOG = REPO / "applications.json"
EVIDENCE_DIR = REPO / "evidence"

DIADEMA_LAT, DIADEMA_LON = -23.6856, -46.6228
RADIUS_KM = 30.0
DAYS_BACK = 7

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "")
N8N_WEBHOOK_HEADER = os.environ.get("N8N_WEBHOOK_HEADER", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
GMAIL_FROM_ADDR = os.environ.get("GMAIL_FROM_ADDR", "fabiokansas@gmail.com")
WORKDAY_NATURA_PASSWORD = os.environ.get("WORKDAY_NATURA_PASSWORD", "")
LINKEDIN_LI_AT = os.environ.get("LINKEDIN_LI_AT", "")

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

GUPY_TARGET_COMPANIES = [
    "vwbrasil", "mercedes-benzcaminhoeseonibus", "vemparabombril",
    "vivo", "vemproitau", "pagseguro", "magazineluiza", "americanas",
    "natura", "ambev", "scania", "ifood", "globo", "br", "cocacolafemsa",
    "carrefourbsf", "bradesco", "pernambucanas", "dasa",
    "cyrela", "gerdau", "usiminas", "localiza",
]


def fetch_gupy(keywords: list[str], since: datetime) -> list[dict]:
    out: dict[int, dict] = {}
    for kw in keywords:
        for offset in (0, 10, 20):
            qs = urllib.parse.urlencode({"name": kw, "limit": 10, "offset": offset})
            try:
                raw = http_get(f"https://portal.api.gupy.io/api/job?{qs}")
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
                    "description": (j.get("description") or ""),
                }
            time.sleep(0.3)
    return list(out.values())


def fetch_gupy_company(subdomain: str, since: datetime) -> list[dict]:
    """Lista vagas direto do career-page Gupy de uma empresa (ex: vwbrasil.gupy.io)."""
    out: list[dict] = []
    try:
        raw = http_get(f"https://{subdomain}.gupy.io/api/job?limit=30&offset=0")
        data = json.loads(raw)
    except Exception as e:
        print(f"[gupy-co] err {subdomain}: {e}", file=sys.stderr)
        return out
    for j in data.get("data") or data.get("jobs") or []:
        jid = j.get("id")
        if not jid:
            continue
        pub = j.get("publishedDate") or j.get("createdAt") or ""
        if pub:
            try:
                dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                if dt < since:
                    continue
            except Exception:
                pass
        out.append({
            "source": f"gupy-{subdomain}",
            "external_id": f"{subdomain}-{jid}",
            "title": j.get("name", ""),
            "company": j.get("careerPageName", subdomain),
            "city": j.get("city"),
            "state": j.get("state"),
            "remote": bool(j.get("isRemoteWork")),
            "url": j.get("jobUrl") or f"https://{subdomain}.gupy.io/job/{jid}",
            "published": pub,
            "description": (j.get("description") or ""),
        })
    return out


def fetch_workday(tenant: str, site: str, keywords: list[str], since: datetime) -> list[dict]:
    """Workday CXS API. Ex: toyota / TLAC, natura / NaturaCarreiras."""
    out: list[dict] = []
    url = f"https://{tenant}.wd5.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
    # alguns tenants são wd501, wd3, wd1, wd103, wd105 etc.
    bases = [
        f"https://{tenant}.wd5.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs",
        f"https://{tenant}.wd3.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs",
        f"https://{tenant}.wd1.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs",
        f"https://{tenant}.wd501.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs",
        f"https://{tenant}.wd103.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs",
        f"https://{tenant}.wd105.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs",
    ]
    for kw in keywords:
        for url in bases:
            try:
                body = json.dumps({"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": kw}).encode()
                req = urllib.request.Request(url, data=body,
                    headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": UA}, method="POST")
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = json.loads(r.read())
                break
            except Exception:
                data = None
        if not data:
            continue
        for j in data.get("jobPostings", []):
            ext = j.get("externalPath") or j.get("title", "")
            jid = f"{tenant}-{ext}"
            pub = j.get("postedOn") or ""
            out.append({
                "source": f"workday-{tenant}",
                "external_id": jid,
                "title": j.get("title", ""),
                "company": tenant.title(),
                "city": (j.get("locationsText") or "").split(",")[0].strip() or None,
                "state": None,
                "remote": "remote" in (j.get("locationsText") or "").lower(),
                "url": f"https://{tenant}.wd5.myworkdayjobs.com/{site}{ext}" if ext.startswith("/") else f"https://{tenant}.wd5.myworkdayjobs.com/{site}/job/{ext}",
                "published": pub,
                "description": (j.get("bulletFields") or [""])[0],
            })
        time.sleep(0.5)
    return out


def fetch_csod_bradesco(keywords: list[str], since: datetime) -> list[dict]:
    """Bradesco Cornerstone OnDemand."""
    out: list[dict] = []
    url = "https://bradesco.csod.com/services/x/career-site/v1/search"
    for kw in keywords:
        body = {
            "careerSiteId": 1,
            "cultureId": 39,  # pt-BR
            "search": kw,
            "pageNumber": 1,
            "pageSize": 25,
        }
        try:
            data = http_post(url, body, timeout=30)
        except Exception as e:
            print(f"[csod-bradesco] err kw={kw}: {e}", file=sys.stderr)
            continue
        for j in data.get("data", {}).get("requisitions", []) or data.get("requisitions", []) or []:
            jid = str(j.get("displayJobId") or j.get("requisitionId") or "")
            if not jid:
                continue
            out.append({
                "source": "csod-bradesco",
                "external_id": f"bradesco-{jid}",
                "title": j.get("displayJobTitle") or j.get("jobTitle", ""),
                "company": "Bradesco",
                "city": (j.get("locations") or [{}])[0].get("city") if j.get("locations") else None,
                "state": (j.get("locations") or [{}])[0].get("stateCode") if j.get("locations") else None,
                "remote": False,
                "url": f"https://bradesco.csod.com/ux/ats/careersite/1/home/requisition/{jid}?c=bradesco",
                "published": j.get("postedDate") or "",
                "description": (j.get("description") or j.get("externalDescription") or ""),
            })
        time.sleep(0.3)
    return out


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
            "description": re.sub(r"<[^>]+>", " ", desc),
        }
    return list(out.values())


def fetch_indeed_rss(keywords: list[str], since: datetime) -> list[dict]:
    out: dict[str, dict] = {}
    for kw in keywords:
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
                "description": tag("description"),
            }
        time.sleep(0.3)
    return list(out.values())


# ============================== DISCOVERY HTML (BeautifulSoup) ==============================

def _html_get(url: str, timeout: int = 25) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.5",
        "Referer": "https://www.google.com/",
        "Sec-Fetch-Site": "cross-site",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def fetch_vagas_html(keywords: list[str], since: datetime) -> list[dict]:
    out: dict[str, dict] = {}
    for kw in keywords:
        slug = kw.lower().replace(" ", "-").replace("&", "e")
        url = f"https://www.vagas.com.br/vagas-de-{urllib.parse.quote(slug)}-em-sao-paulo"
        try:
            html = _html_get(url)
        except Exception as e:
            print(f"[vagas] err kw={kw}: {e}", file=sys.stderr)
            continue
        for m in re.finditer(r'<li class="vaga (?:odd|even)[^"]*"[\s\S]*?</li>', html):
            block = m.group(0)
            href_m = re.search(r'<a class="link-detalhes-vaga"[^>]*data-id-vaga="(\d+)"[^>]*title="([^"]+)"[^>]*href="([^"]+)"', block)
            if not href_m:
                continue
            jid, title_attr, link = href_m.group(1), href_m.group(2), href_m.group(3)
            if link.startswith("/"):
                link = "https://www.vagas.com.br" + link
            if jid in out:
                continue
            company_m = re.search(r'<span class="emprVaga[^"]*"[^>]*>\s*([^<]+?)\s*</span>', block)
            loc_m = re.search(r'<div class="vaga-local"[^>]*>[\s\S]*?</i>\s*([^<]+?)\s*</div>', block)
            desc_m = re.search(r'<div class="detalhes[^"]*"[^>]*>\s*<p[^>]*>([\s\S]*?)</p>', block)
            date_m = re.search(r'<span class="data-publicacao"[^>]*>[\s\S]*?</i>\s*([\d/]+)\s*</span>', block)
            city_raw = (loc_m.group(1) if loc_m else "").strip()
            if " - " in city_raw:
                city, state = [s.strip() for s in city_raw.split(" - ", 1)]
            elif city_raw.lower().startswith("localiza"):
                city, state = None, None
            else:
                city, state = city_raw or None, None
            out[jid] = {
                "source": "vagas",
                "external_id": f"vagas-{jid}",
                "title": unescape(title_attr).strip(),
                "company": unescape((company_m.group(1) if company_m else "")).strip(),
                "city": city,
                "state": state,
                "remote": "remoto" in city_raw.lower() or "home office" in city_raw.lower(),
                "url": link,
                "published": (date_m.group(1) if date_m else ""),
                "description": unescape(re.sub(r"<[^>]+>", " ", desc_m.group(1) if desc_m else "")).strip(),
            }
        time.sleep(0.4)
    return list(out.values())


def fetch_catho_html(keywords: list[str], since: datetime) -> list[dict]:
    """Catho mudou rota; rota antiga 404. Stub até descobrir o novo path."""
    # TODO: re-investigar Catho via DevTools (provavelmente migraram pra /api/v3/jobs JSON).
    return []


def fetch_infojobs_html(keywords: list[str], since: datetime) -> list[dict]:
    out: dict[str, dict] = {}
    for kw in keywords:
        url = f"https://www.infojobs.com.br/empregos.aspx?palabra={urllib.parse.quote(kw)}&provincia=S%C3%A3o+Paulo"
        try:
            html = _html_get(url)
        except Exception as e:
            print(f"[infojobs] err kw={kw}: {e}", file=sys.stderr)
            continue
        for m in re.finditer(r'<div id="vacancy(\d+)"[^>]*data-href="([^"]+)"[\s\S]{0,6000}?(?=<div id="vacancy\d+"|<footer|</main)', html):
            jid = m.group(1)
            href = m.group(2)
            block = m.group(0)
            if jid in out:
                continue
            link = "https://www.infojobs.com.br" + href if href.startswith("/") else href
            title_m = re.search(r'class="[^"]*js_vacancyTitle[^"]*"[^>]*>\s*([^<]+?)\s*</h2>', block)
            company_m = re.search(r'href="https://www\.infojobs\.com\.br/empresa-[^"]+"[^>]*>\s*([\s\S]{0,200}?)<span', block)
            company = ""
            if company_m:
                company = unescape(re.sub(r"<[^>]+>", " ", company_m.group(1))).strip()
                company = re.sub(r"\s+", " ", company)
            city_m = re.search(r'<div class="mb-8">\s*([^<]+?)<', block)
            date_m = re.search(r'class="js_date"\s+data-value="([^"]+)"', block)
            pub = ""
            if date_m:
                try:
                    dt = datetime.strptime(date_m.group(1), "%Y/%m/%d %H:%M:%S").replace(tzinfo=timezone.utc)
                    pub = dt.isoformat()
                    if dt < since:
                        continue
                except Exception:
                    pass
            city_raw = unescape((city_m.group(1) if city_m else "")).strip()
            city = city_raw.split(" - ")[0].strip() if " - " in city_raw else (city_raw or None)
            state = city_raw.split(" - ")[1].strip() if " - " in city_raw else None
            slug_from_href = href.split("__")[0].lstrip("/").replace("vaga-de-", "").replace("-", " ")
            out[jid] = {
                "source": "infojobs",
                "external_id": f"infojobs-{jid}",
                "title": (title_m.group(1).strip() if title_m else slug_from_href[:80]),
                "company": company,
                "city": city,
                "state": state or "SP",
                "remote": "home office" in block.lower() or "remoto" in block.lower(),
                "url": link,
                "published": pub,
                "description": "",
            }
        time.sleep(0.4)
    return list(out.values())


def fetch_linkedin_guest_html(keywords: list[str], since: datetime) -> list[dict]:
    out: dict[str, dict] = {}
    for i, kw in enumerate(keywords[:5]):
        url = (
            "https://www.linkedin.com/jobs/search/?"
            + urllib.parse.urlencode({
                "keywords": kw,
                "location": "São Paulo, Brazil",
                "f_TPR": "r604800",
                "sortBy": "DD",
            })
        )
        try:
            html = _html_get(url, timeout=30)
        except Exception as e:
            print(f"[linkedin-guest] err kw={kw}: {e}", file=sys.stderr)
            continue
        for m in re.finditer(r'<a [^>]*href="(https://[a-z]+\.linkedin\.com/jobs/view/[^"?#]+(?:\?[^"]*)?)"[^>]*>', html):
            link = m.group(1).split("?")[0]
            jid_m = re.search(r"-(\d+)$", link)
            jid = jid_m.group(1) if jid_m else link
            if jid in out:
                continue
            slug = urllib.parse.unquote(link.rsplit("/", 1)[-1])
            slug_human = re.sub(r"-\d+$", "", slug).replace("-", " ").strip()
            # "Coordenador A Planejamento" → padroniza
            slug_human = re.sub(r"\bat\b", "@", slug_human, flags=re.I).title()
            out[jid] = {
                "source": "linkedin-guest",
                "external_id": f"linkedin-{jid}",
                "title": slug_human[:120] or "(linkedin)",
                "company": "",
                "city": "São Paulo",
                "state": "SP",
                "remote": False,
                "url": link,
                "published": "",
                "description": "",
            }
        if i < len(keywords[:5]) - 1:
            time.sleep(15)  # guest limit ~5/h
    return list(out.values())


def fetch_linkedin_jobs_auth(keywords: list[str], since: datetime) -> list[dict]:
    """Versão autenticada (cookie li_at). Mais cards, mais metadata. Ativa se LINKEDIN_LI_AT."""
    if not LINKEDIN_LI_AT:
        return fetch_linkedin_guest_html(keywords, since)
    out: dict[str, dict] = {}
    for kw in keywords[:5]:
        url = (
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?"
            + urllib.parse.urlencode({"keywords": kw, "location": "São Paulo, Brazil", "f_TPR": "r604800", "start": 0})
        )
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
                "Cookie": f"li_at={LINKEDIN_LI_AT}",
                "Accept": "text/html",
            })
            with urllib.request.urlopen(req, timeout=30) as r:
                html = r.read().decode("utf-8", "ignore")
        except Exception as e:
            print(f"[linkedin-auth] err kw={kw}: {e}", file=sys.stderr)
            continue
        for m in re.finditer(r'<li[\s\S]*?data-entity-urn="urn:li:jobPosting:(\d+)"[\s\S]*?</li>', html):
            jid = m.group(1)
            block = m.group(0)
            if jid in out:
                continue
            title_m = re.search(r'<h3 class="base-search-card__title">\s*([^<]+)', block)
            company_m = re.search(r'<h4 class="base-search-card__subtitle">\s*<a[^>]*>\s*([^<]+)', block) \
                or re.search(r'<h4 class="base-search-card__subtitle">\s*([^<]+)', block)
            city_m = re.search(r'<span class="job-search-card__location">\s*([^<]+)', block)
            date_m = re.search(r'<time[^>]*datetime="([^"]+)"', block)
            link_m = re.search(r'href="(https://[a-z]+\.linkedin\.com/jobs/view/[^"?#]+)', block)
            out[jid] = {
                "source": "linkedin",
                "external_id": f"linkedin-{jid}",
                "title": (title_m.group(1).strip() if title_m else "")[:120],
                "company": (company_m.group(1).strip() if company_m else ""),
                "city": (city_m.group(1).strip().split(",")[0] if city_m else "São Paulo"),
                "state": "SP",
                "remote": "remoto" in block.lower() or "remote" in block.lower(),
                "url": (link_m.group(1) if link_m else url),
                "published": (date_m.group(1) if date_m else ""),
                "description": "",
            }
        time.sleep(2)
    return list(out.values())


# ============================== DISCOVERY EXTRA (Shopee / ML / LinkedIn by company) ==============================


def fetch_shopee_careers(keywords: list[str], since: datetime) -> list[dict]:
    """Shopee careers BR — Next.js __NEXT_DATA__ JSON embedded."""
    out: dict[str, dict] = {}
    for kw in keywords[:4]:
        try:
            url = f"https://careers.shopee.com.br/jobs?searchKeyword={urllib.parse.quote(kw)}"
            html = _html_get(url, timeout=20)
        except Exception as e:
            print(f"[shopee] err kw={kw}: {e}", file=sys.stderr)
            continue
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>', html, re.S)
        if not m:
            continue
        try:
            payload = json.loads(m.group(1))
        except Exception as e:
            print(f"[shopee] json err: {e}", file=sys.stderr)
            continue
        # tentar múltiplos paths que Shopee usa
        jobs: list[dict] = []
        node = payload
        for key in ("props", "pageProps"):
            node = (node or {}).get(key) or {}
        for k in ("jobs", "jobList", "results", "data"):
            if isinstance(node.get(k), list):
                jobs = node[k]
                break
        for j in jobs:
            jid = str(j.get("id") or j.get("jobId") or j.get("requisitionId") or "")
            if not jid or jid in out:
                continue
            title = (j.get("title") or j.get("name") or "").strip()
            if not title:
                continue
            loc = (j.get("location") or j.get("city") or {})
            city = loc.get("city") if isinstance(loc, dict) else (loc if isinstance(loc, str) else None)
            out[jid] = {
                "source": "shopee",
                "external_id": f"shopee-{jid}",
                "title": title,
                "company": "Shopee",
                "city": city,
                "state": (loc.get("state") if isinstance(loc, dict) else None),
                "remote": "remote" in (str(loc).lower() if loc else ""),
                "url": f"https://careers.shopee.com.br/jobs/{jid}",
                "published": j.get("postedDate") or j.get("createdAt") or "",
                "description": (j.get("description") or j.get("responsibilities") or ""),
            }
        time.sleep(0.5)
    return list(out.values())


def fetch_mercadolivre_careers(keywords: list[str], since: datetime) -> list[dict]:
    """ML careers — tenta Lever, Greenhouse e portal próprio em cadeia."""
    out: dict[str, dict] = {}
    # 1. Lever
    try:
        raw = http_get("https://api.lever.co/v0/postings/mercadolibre?mode=json", timeout=15)
        data = json.loads(raw)
        for j in data:
            jid = j.get("id")
            if not jid:
                continue
            title = j.get("text", "")
            if not any(k.lower() in title.lower() for k in keywords):
                continue
            cat = j.get("categories") or {}
            out[jid] = {
                "source": "ml-lever",
                "external_id": f"ml-{jid}",
                "title": title,
                "company": "Mercado Livre",
                "city": cat.get("location") or None,
                "state": None,
                "remote": "remote" in (cat.get("commitment") or "").lower(),
                "url": j.get("hostedUrl") or "",
                "published": "",
                "description": (j.get("descriptionPlain") or j.get("description") or "")[:8000],
            }
        if out:
            return list(out.values())
    except Exception as e:
        print(f"[ml-lever] err: {e}", file=sys.stderr)
    # 2. Greenhouse fallback
    try:
        raw = http_get("https://boards-api.greenhouse.io/v1/boards/mercadolibre/jobs", timeout=15)
        data = json.loads(raw)
        for j in data.get("jobs", []):
            jid = str(j.get("id"))
            title = j.get("title", "")
            if not any(k.lower() in title.lower() for k in keywords):
                continue
            loc = j.get("location") or {}
            out[jid] = {
                "source": "ml-greenhouse",
                "external_id": f"ml-{jid}",
                "title": title,
                "company": "Mercado Livre",
                "city": (loc.get("name") or "").split(",")[0].strip() if loc else None,
                "state": None,
                "remote": "remote" in (loc.get("name") or "").lower(),
                "url": j.get("absolute_url") or "",
                "published": j.get("updated_at") or "",
                "description": "",
            }
        if out:
            return list(out.values())
    except Exception as e:
        print(f"[ml-greenhouse] err: {e}", file=sys.stderr)
    return list(out.values())


# Mapping LinkedIn company-IDs (descobertos via URL `/company/<slug>/people/?facetCurrentCompany=ID`)
LINKEDIN_COMPANY_IDS = {
    "mercadolivre": 7491,
    "shopee": 11856189,
    "itau": 11086,
    "carrefour": 10670,
    "natura": 10260,
    "magazineluiza": 31023,
    "ambev": 11077,
    "vivo": 11079,
    "bradesco": 10260,
    "amazon": 1586,
}


def fetch_linkedin_by_company(since: datetime) -> list[dict]:
    """Vagas LinkedIn por company ID via guest seeMore endpoint (HTML estável)."""
    out: dict[str, dict] = {}
    for slug, cid in LINKEDIN_COMPANY_IDS.items():
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?f_C={cid}&start=0&location=Brazil"
        try:
            html = _html_get(url, timeout=20)
        except Exception as e:
            print(f"[li-co {slug}] err: {e}", file=sys.stderr)
            continue
        for m in re.finditer(r'data-entity-urn="urn:li:jobPosting:(\d+)"[\s\S]*?<h3[^>]*>\s*([^<]+?)\s*</h3>[\s\S]*?<h4[^>]*>[\s\S]*?>([^<]+?)<', html):
            jid, title, company = m.group(1), m.group(2).strip(), m.group(3).strip()
            if jid in out:
                continue
            link_m = re.search(rf'href="(https://[a-z]+\.linkedin\.com/jobs/view/[^"?#]*-{jid})', html)
            out[jid] = {
                "source": f"linkedin-co-{slug}",
                "external_id": f"linkedin-{jid}",
                "title": title[:120],
                "company": company or slug.title(),
                "city": "Brazil",
                "state": None,
                "remote": False,
                "url": (link_m.group(1) if link_m else f"https://www.linkedin.com/jobs/view/{jid}"),
                "published": "",
                "description": "",
            }
        time.sleep(2)
    return list(out.values())


# ============================== APPLICATIONS LOG (JSONL) ==============================

def load_applications_log() -> list[dict]:
    if not APPLICATIONS_LOG.exists():
        return []
    recs = []
    for line in APPLICATIONS_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            recs.append(json.loads(line))
        except Exception:
            continue
    return recs


def append_application(record: dict) -> None:
    record = {**record, "logged_at": datetime.now(timezone.utc).isoformat()}
    with APPLICATIONS_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def dedupe_check(platform: str, key_field: str, key_value: str, window_days: int) -> bool:
    """Retorna True se já aplicou (skip)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    for r in load_applications_log():
        if r.get("platform") != platform:
            continue
        if r.get(key_field) != key_value:
            continue
        ts = r.get("logged_at") or r.get("sent_at") or ""
        try:
            if datetime.fromisoformat(ts.replace("Z", "+00:00")) >= cutoff:
                return True
        except Exception:
            continue
    return False


# ============================== SCORING ==============================

SCORING_PROMPT = """Você é analista de RH sênior em Controladoria/FP&A no Brasil. Avalie objetivamente CADA vaga vs o candidato. Seja crítico e honesto — pular vaga ruim é melhor que aplicar mal.

=== CANDIDATO (perfil + currículo md + texto extraído do PDF) ===
{profile}

=== EXEMPLOS HISTÓRICOS DE PULOS RECENTES (não repetir mesmos erros) ===
{few_shot}

=== VAGAS PARA AVALIAR ===
{vagas_json}

Regras estritas:
- R1: score 0-100. 90+ = match perfeito; 70-89 = bom; 50-69 = parcial; <50 = descarta
- R2: salary_fit = "below" se vaga explicita <R$5k OU pede júnior (mercado júnior = 3-4k)
- R3: location: aceita Diadema/SBC/Sto André/Mauá/SP capital sul, ou remoto BR
- R4: recommend_apply = TRUE SOMENTE SE score>=65 AND salary_fit != "below" AND R7 atendida
- R5: requirements_met = array com 2-5 evidências CONCRETAS do CV que batem com a vaga
- R6: gaps = array com requisitos da vaga que o candidato NÃO tem (vazio se nenhum)
- R7: vaga PRECISA ter pelo menos UM destes hard-skills no escopo: SAP/Bluesoft/Sponte/Mega/Omie/DRE/fechamento/FP&A/orçamento/controladoria/planejamento financeiro. Senão score≤55.
- R8: vaga trainee/estagiário/júnior puro (sem menção a sênior/pleno) → recommend_apply=false (candidato tem 6 anos de experiência, não regredir)
- R9: match_summary: 1-2 frases PT-BR explicando o porquê do score
- R10: reason_not_apply: vazio se recommend=true; senão 1 frase específica (não "score baixo")

Para CADA vaga, retorne objeto JSON:
{{"id": "<external_id>", "score": <0-100>, "match_summary": "...", "requirements_met": [...], "gaps": [...], "salary_fit": "within|below|above|unknown", "recommend_apply": <bool>, "reason_not_apply": "..."}}

Retorne SOMENTE JSON válido: {{"vagas": [<obj1>, ...]}}"""


def _build_few_shot(max_records: int = 10) -> str:
    """Carrega últimos N records de applications.json com status skipped/failed
    pra alimentar o prompt como exemplo negativo (S2.5)."""
    if not APPLICATIONS_LOG.exists():
        return "(nenhum histórico ainda)"
    try:
        recs = []
        for line in APPLICATIONS_LOG.read_text(encoding="utf-8").splitlines()[-200:]:
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except Exception:
                continue
        bads = [r for r in recs if r.get("status") in ("skipped", "failed", "no_email_found", "rejected")]
        bads = bads[-max_records:]
        if not bads:
            return "(sem skips/falhas recentes)"
        lines = []
        for r in bads:
            title = r.get("vaga_title") or r.get("subject") or "?"
            reason = r.get("info") or r.get("reason_not_apply") or r.get("status") or ""
            lines.append(f"- pulou: {title[:80]} | motivo: {str(reason)[:120]}")
        return "\n".join(lines)
    except Exception:
        return "(erro carregando histórico)"


def score_with_gemini(profile_bundle: str, vagas: list[dict]) -> list[dict]:
    """Score vagas em chunks de 3 vagas/call para análise profunda. Sem caps."""
    if not vagas:
        return []
    if not GEMINI_KEY:
        print("[gemini] GEMINI_API_KEY missing — skipping scoring", file=sys.stderr)
        return []

    few_shot = _build_few_shot()
    results: list[dict] = []
    chunk_size = 3  # S2.2: menos vagas por call = mais raciocínio por vaga
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
                "source": v.get("source", ""),
                "description": v["description"],  # S2.3: descrição inteira (1M token model)
            }
            for v in chunk
        ]
        prompt = SCORING_PROMPT.format(
            profile=profile_bundle,
            few_shot=few_shot,
            vagas_json=json.dumps(compact, ensure_ascii=False),
        )
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
                "maxOutputTokens": 8192,
            },
        }
        parsed = None
        last_err = None
        for model in ("gemini-2.5-flash-lite", "gemini-flash-latest", "gemini-2.5-flash"):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
            try:
                resp = http_post(url, body, timeout=120)
                text = resp.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
                parsed = json.loads(text)
                break
            except Exception as e:
                last_err = e
                continue
        if parsed:
            results.extend(parsed.get("vagas", []))
        else:
            print(f"[gemini] err chunk {i}: {last_err}", file=sys.stderr)
            for v in chunk:
                results.append(
                    {
                        "id": v["external_id"],
                        "score": 0,
                        "match_summary": f"Erro no scoring: {last_err}",
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

def tg_discover_chat_id() -> str:
    """Se TELEGRAM_CHAT_ID não setado, descobre via getUpdates."""
    global TELEGRAM_CHAT
    if TELEGRAM_CHAT:
        return TELEGRAM_CHAT
    if not TELEGRAM_TOKEN:
        return ""
    try:
        raw = http_get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates")
        data = json.loads(raw)
        for r in data.get("result", []):
            cid = r.get("message", {}).get("chat", {}).get("id")
            if cid:
                TELEGRAM_CHAT = str(cid)
                print(f"[telegram] auto-discovered chat_id={cid}", file=sys.stderr)
                return TELEGRAM_CHAT
    except Exception as e:
        print(f"[telegram] discover err: {e}", file=sys.stderr)
    return ""


def n8n_forward(payload: dict) -> None:
    """Posta vagas recomendadas no webhook do n8n existente (n8n-mryj).

    Ativa só se N8N_WEBHOOK_URL estiver setado. Permite que o ChatGPT (que tem
    acesso ao n8nOps MCP) crie um workflow simples no n8n-mryj com:
        Webhook (POST /webhook/automa-o) → branch por v.recommend_apply
        → ramificações de apply (Gupy login, email recrutadora, etc.)

    Pra o lado do Claude funcionar passivo: bastar o N8N_WEBHOOK_URL como secret
    do GitHub Actions. Não preciso de N8N_API_KEY pra postar em webhook (só pra
    criar workflow via API REST do n8n).
    """
    if not N8N_WEBHOOK_URL:
        return
    headers = {"Content-Type": "application/json", "User-Agent": UA}
    if N8N_WEBHOOK_HEADER and ":" in N8N_WEBHOOK_HEADER:
        k, v = N8N_WEBHOOK_HEADER.split(":", 1)
        headers[k.strip()] = v.strip()
    body = json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(N8N_WEBHOOK_URL, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"[n8n] forward → HTTP {r.status} ({len(payload.get('vagas_top', []))} vagas top)", file=sys.stderr)
    except Exception as e:
        print(f"[n8n] forward erro: {e}", file=sys.stderr)


# ============================== COVER LETTER + EMAIL ==============================

RECRUITERS: list[dict] = [
    {"name": "Talenses", "to": "contato@talenses.com"},
    {"name": "JPeF", "to": "contato@jpef.com.br"},
    {"name": "Apex Talent", "to": "recruitment@apexpartners.com.br"},
    {"name": "Page Personnel", "to": "paulosaopaulo@pagepersonnel.com.br"},
    {"name": "Robert Half", "to": "saopaulo@roberthalf.com.br"},
]


COVER_CACHE_DIR = REPO / "cache" / "cover_letters"


def gen_cover_letter(profile_bundle: str, vagas_top: list[dict], audience: str = "empresa", match_analysis: dict | None = None) -> str:
    """Gera carta de apresentação 180 palavras via Gemini.

    A5: cache por external_id (apply do mesmo job entre runs reusa cover).
    Quando match_analysis vem (S2.7), cita requirements_met + endereça gaps.
    """
    if not GEMINI_KEY or not vagas_top:
        return ""

    # Cache só pra audience=empresa (recrutadora é genérica e curta)
    cache_key = None
    if audience == "empresa" and len(vagas_top) == 1:
        ext = vagas_top[0].get("external_id", "")
        safe = re.sub(r"[^A-Za-z0-9_-]", "_", ext)[:80]
        cache_key = COVER_CACHE_DIR / f"{safe}.txt"
        if cache_key.exists():
            try:
                cached = cache_key.read_text(encoding="utf-8").strip()
                if cached:
                    return cached
            except Exception:
                pass

    ctx = "\n".join(f"- {v['title']} @ {v['company']} ({v.get('city','?')})" for v in vagas_top[:3])
    instr = (
        "Escreva uma carta de apresentação (cover letter) em PT-BR, tom profissional e direto, ~180 palavras. "
        "Sem clichês ('apaixonado'). Sem markdown. Sem assinatura. Apenas o corpo do email."
    )
    if audience == "recrutadora":
        instr += " Audience: recrutadora de RH especializada em Finanças. Mencione abertura geral para Controladoria/FP&A em ABC+SP, R$5k+ CLT preferencial."
    else:
        v = vagas_top[0]
        instr += f" Audience: hiring manager da vaga '{v['title']}' em {v['company']}. Cite 2 conquistas reais do currículo (DRE, fechamento, SAP/Bluesoft, etc.) que batem com a vaga."
        if match_analysis:
            reqs = match_analysis.get("requirements_met") or []
            gaps = match_analysis.get("gaps") or []
            if reqs:
                instr += f" Requisitos atendidos a destacar: {', '.join(reqs[:4])}."
            if gaps:
                instr += f" Um gap a endereçar de forma positiva (1 frase mostrando que está confortável aprendendo): {gaps[0]}."

    vaga_desc = ""
    if len(vagas_top) == 1:
        vaga_desc = f"\n\n=== DESCRIÇÃO DA VAGA ===\n{vagas_top[0].get('description','')[:2500]}"

    prompt = f"{instr}\n\n=== PERFIL + CV ===\n{profile_bundle[:6000]}\n\n=== VAGAS DE INTERESSE ===\n{ctx}{vaga_desc}"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 800},
    }
    try:
        resp = http_post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_KEY}",
            body,
            timeout=60,
        )
        text = resp.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
        if text and cache_key:
            cache_key.parent.mkdir(parents=True, exist_ok=True)
            cache_key.write_text(text, encoding="utf-8")
        return text
    except Exception as e:
        print(f"[cover-letter] err: {e}", file=sys.stderr)
        return ""


def _send_smtp_email(to_addr: str, subject: str, body: str, attach_pdf: Path | None = None) -> tuple[bool, str]:
    if not GMAIL_APP_PASSWORD:
        return False, "GMAIL_APP_PASSWORD ausente"
    msg = EmailMessage()
    msg["From"] = GMAIL_FROM_ADDR
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg["Reply-To"] = GMAIL_FROM_ADDR
    msg.set_content(body)
    if attach_pdf and attach_pdf.exists():
        data = attach_pdf.read_bytes()
        msg.add_attachment(data, maintype="application", subtype="pdf", filename=attach_pdf.name)
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as srv:
            srv.starttls(context=ctx)
            srv.login(GMAIL_FROM_ADDR, GMAIL_APP_PASSWORD)
            srv.send_message(msg)
        return True, msg["Message-ID"] or ""
    except Exception as e:
        return False, str(e)[:200]


def email_recruiters(top_vagas: list[dict], profile_bundle: str) -> list[dict]:
    """Envia 1 email por recrutadora (5) referenciando vagas top. Dedupe 48h."""
    sent: list[dict] = []
    if not GMAIL_APP_PASSWORD:
        print("[email-recruiters] GMAIL_APP_PASSWORD ausente — skip", file=sys.stderr)
        return sent
    # Só vagas com score >= 75 e fontes de empresa (não recrutadora-de-mercado)
    refs = [v for v in top_vagas if v.get("_score", 0) >= 75]
    if not refs:
        print("[email-recruiters] sem refs (score >=75) — skip", file=sys.stderr)
        return sent
    cover = gen_cover_letter(profile_bundle, refs, audience="recrutadora")
    if not cover:
        print("[email-recruiters] cover letter vazia — skip", file=sys.stderr)
        return sent
    for r in RECRUITERS:
        if dedupe_check("email", "to", r["to"], window_days=2):
            print(f"[email-recruiters] skip {r['name']} (já enviado <48h)", file=sys.stderr)
            continue
        subject = "Fabio Fernandes — Perfil para Controladoria / FP&A em SP"
        body = cover + "\n\nCurrículo anexo. Disponível para conversa.\n\nFabio Fernandes\n(11) 95927-3390\nDiadema-SP"
        ok, info = _send_smtp_email(r["to"], subject, body, attach_pdf=CV_PDF)
        rec = {
            "platform": "email",
            "recruiter": r["name"],
            "to": r["to"],
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "status": "sent" if ok else "failed",
            "info": info,
            "vagas_referenced": [v["external_id"] for v in refs[:3]],
        }
        append_application(rec)
        sent.append(rec)
        print(f"[email-recruiters] {r['name']} → {rec['status']}: {info[:60]}", file=sys.stderr)
        time.sleep(2)
    return sent


# ============================== TELEGRAM (cont.) ==============================

def tg_send(text: str) -> None:
    if not TELEGRAM_TOKEN:
        print("[telegram] TELEGRAM_BOT_TOKEN missing", file=sys.stderr)
        return
    if not TELEGRAM_CHAT:
        tg_discover_chat_id()
    if not TELEGRAM_CHAT:
        print("[telegram] chat_id desconhecido — manda qualquer msg ao bot e rode de novo", file=sys.stderr)
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    # Telegram limit 4096 chars. Quebra em blocos terminando em \n quando possível.
    chunks: list[str] = []
    buf = ""
    for line in text.split("\n"):
        if len(buf) + len(line) + 1 > 3800:
            chunks.append(buf)
            buf = line
        else:
            buf = (buf + "\n" + line) if buf else line
    if buf:
        chunks.append(buf)
    for chunk in chunks:
        for attempt in range(2):
            try:
                http_post(url, {
                    "chat_id": TELEGRAM_CHAT,
                    "text": chunk,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                })
                break
            except urllib.error.HTTPError as e:
                body = e.read().decode(errors="replace")[:300]
                print(f"[telegram] HTTP {e.code} (attempt {attempt+1}): {body}", file=sys.stderr)
                if attempt == 0 and e.code == 400:
                    # Retry sem HTML
                    try:
                        plain = re.sub(r"<[^>]+>", "", chunk)
                        http_post(url, {"chat_id": TELEGRAM_CHAT, "text": plain, "disable_web_page_preview": True})
                        break
                    except Exception as e2:
                        print(f"[telegram] retry plain err: {e2}", file=sys.stderr)
            except Exception as e:
                print(f"[telegram] err: {e}", file=sys.stderr)
        time.sleep(0.4)


def html_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _fmt_applications(apps: list[dict]) -> str:
    if not apps:
        return ""
    by_plat: dict[str, list[dict]] = {}
    for a in apps:
        by_plat.setdefault(a.get("platform", "?"), []).append(a)
    out = ["", "═══ <b>APLICAÇÕES ENVIADAS</b> ═══", ""]
    emoji = {"email": "📧", "workday": "🌐", "gupy": "🤖", "email_direct": "✉️"}
    for plat in ("email", "workday", "gupy", "email_direct"):
        items = by_plat.get(plat, [])
        if not items:
            continue
        out.append(f"{emoji.get(plat,'•')} <b>{plat}</b> ({len(items)}):")
        for a in items:
            st = a.get("status", "?").upper()
            if plat == "email":
                line = f"  · [{st}] {a.get('recruiter','?')} → {a.get('to','?')}"
            elif plat == "workday":
                line = f"  · [{st}] {html_escape(a.get('vaga_title','?')[:60])} ({a.get('tenant','?')}) {a.get('application_id','')}"
            elif plat == "gupy":
                screenshot = f" 📷 {a['screenshot']}" if a.get("screenshot") else ""
                line = f"  · [{st}] {html_escape(a.get('vaga_title','?')[:60])} ({a.get('company','?')}){screenshot}"
            elif plat == "email_direct":
                line = f"  · [{st}] {html_escape(a.get('vaga_title','?')[:50])} ({a.get('company','?')}) → {a.get('to','?email?')} [src={a.get('email_source','?')}]"
            else:
                line = f"  · [{st}] {a}"
            out.append(line)
        out.append("")
    return "\n".join(out)


def format_report(vagas: list[dict], scores_by_id: dict[str, dict], run_label: str, applications: list[dict] | None = None, triage_alerts: list[dict] | None = None) -> str:
    now = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-3)))
    apply_list: list[str] = []
    skip_list: list[str] = []
    applications = applications or []

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
    body += _fmt_applications(applications)
    if triage_alerts:
        try:
            from inbox_triage import format_triage_block  # type: ignore
            body += format_triage_block(triage_alerts)
        except Exception as e:
            print(f"[format_report] triage format err: {e}", file=sys.stderr)
    return header + body


# ============================== MAIN ==============================

def _build_profile_bundle() -> str:
    """Concatena profile.md + curriculo.md + texto extraído do CV PDF (S2.4)."""
    parts: list[str] = []
    if PROFILE.exists():
        parts.append("# PERFIL\n" + PROFILE.read_text(encoding="utf-8"))
    if CV.exists():
        parts.append("# CV (markdown)\n" + CV.read_text(encoding="utf-8"))
    try:
        from cv_text import extract_cv_text  # type: ignore
        pdf_text = extract_cv_text(CV_PDF)
        if pdf_text:
            parts.append("# CV (texto extraído do PDF)\n" + pdf_text)
    except Exception as e:
        print(f"[profile_bundle] cv_text err: {e}", file=sys.stderr)
    return "\n\n".join(parts)


def main() -> int:
    run_label = sys.argv[1] if len(sys.argv) > 1 else "manual"
    triage_only = run_label == "triage-only"
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

    # M2: Inbox triage no INÍCIO (precisa de contexto fresco antes de apply)
    triage_alerts: list[dict] = []
    indeed_email_vagas: list[dict] = []
    try:
        from inbox_triage import triage_inbound, fetch_indeed_email_alerts  # type: ignore
        triage_alerts = triage_inbound(since)
        print(f"[inbox-triage] {len(triage_alerts)} alertas detectados", file=sys.stderr)
        indeed_email_vagas = fetch_indeed_email_alerts(since)
        print(f"[indeed-email] {len(indeed_email_vagas)} vagas de alertas Indeed", file=sys.stderr)
    except Exception as e:
        print(f"[inbox-triage] err: {e}", file=sys.stderr)

    if triage_only:
        # Modo só triagem: manda alerta e sai
        if triage_alerts:
            from inbox_triage import format_triage_block  # type: ignore
            tg_send("🔍 <b>Triagem manual</b>\n" + format_triage_block(triage_alerts))
        else:
            tg_send("🔍 Triagem: sem novidades no inbox")
        return 0

    all_vagas: list[dict] = list(indeed_email_vagas)
    all_vagas.extend(fetch_gupy(keywords, since))
    for sub in GUPY_TARGET_COMPANIES:
        try:
            got = fetch_gupy_company(sub, since)
            if got:
                all_vagas.extend(got)
        except Exception as e:
            print(f"[gupy-co] {sub} err: {e}", file=sys.stderr)
        time.sleep(0.3)
    all_vagas.extend(fetch_remoteok(keywords, since))
    # Workday: tenants conhecidos + tentativas best-effort (404 silencioso ok)
    workday_tenants = [
        ("toyota", "TLAC"),
        ("natura", "NaturaCarreiras"),
        ("vw", "VolkswagenCareers"),
        ("mb", "MercedesBenzCareers"),
    ]
    for tenant, site in workday_tenants:
        try:
            got = fetch_workday(tenant, site, keywords[:3], since)
            if got:
                all_vagas.extend(got)
                print(f"[workday] {tenant}: {len(got)} vagas", file=sys.stderr)
        except Exception as e:
            print(f"[workday] {tenant} falhou: {e}", file=sys.stderr)
    try:
        all_vagas.extend(fetch_vagas_html(keywords, since))
    except Exception as e:
        print(f"[vagas-html] err: {e}", file=sys.stderr)
    try:
        all_vagas.extend(fetch_infojobs_html(keywords, since))
    except Exception as e:
        print(f"[infojobs-html] err: {e}", file=sys.stderr)
    try:
        all_vagas.extend(fetch_linkedin_jobs_auth(keywords, since))
    except Exception as e:
        print(f"[linkedin] err: {e}", file=sys.stderr)
    # D2.7-D2.9: novos scrapers
    try:
        got = fetch_shopee_careers(keywords, since)
        all_vagas.extend(got)
        print(f"[shopee] {len(got)} vagas", file=sys.stderr)
    except Exception as e:
        print(f"[shopee] err: {e}", file=sys.stderr)
    try:
        got = fetch_mercadolivre_careers(keywords, since)
        all_vagas.extend(got)
        print(f"[ml] {len(got)} vagas", file=sys.stderr)
    except Exception as e:
        print(f"[ml] err: {e}", file=sys.stderr)
    try:
        got = fetch_linkedin_by_company(since)
        all_vagas.extend(got)
        print(f"[linkedin-by-company] {len(got)} vagas", file=sys.stderr)
    except Exception as e:
        print(f"[linkedin-by-company] err: {e}", file=sys.stderr)
    # Catho 404 (rota antiga inválida); Bradesco CSOD 401 (precisa auth) — ambos stubs hoje.
    print(f"[main] coleta bruta: {len(all_vagas)}", file=sys.stderr)

    # Dedupe global por external_id (vagas iguais vindas de fontes diferentes)
    seen_ids: set[str] = set()
    deduped: list[dict] = []
    for v in all_vagas:
        ext = v.get("external_id", "")
        if ext and ext in seen_ids:
            continue
        seen_ids.add(ext)
        deduped.append(v)
    print(f"[main] após dedupe: {len(deduped)}", file=sys.stderr)
    all_vagas = deduped

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

    # S2.1: REMOVIDO kept[:20] — todas vagas vão pro scoring
    # Ordena por data publicada pra manter snapshot organizado
    def pub_key(v: dict):
        return v.get("published") or ""
    kept.sort(key=pub_key, reverse=True)

    profile_bundle = _build_profile_bundle()
    print(f"[main] profile bundle: {len(profile_bundle)} chars", file=sys.stderr)
    scores = score_with_gemini(profile_bundle, kept)
    scores_by_id = {s["id"]: s for s in scores if "id" in s}

    # Anota score+match na vaga pra facilitar filtragem nas funções de apply
    for v in kept:
        s = scores_by_id.get(v["external_id"], {})
        v["_score"] = s.get("score", 0)
        v["_recommend"] = s.get("recommend_apply", False)
        v["_match"] = s  # passar análise inteira pro gen_cover_letter

    EVIDENCE_DIR.mkdir(exist_ok=True)
    applications: list[dict] = []

    # --- Apply A1: email recrutadoras ---
    try:
        applications.extend(email_recruiters(kept, profile_bundle))
    except Exception as e:
        print(f"[apply-email] err: {e}", file=sys.stderr)

    # --- Apply A2: Workday Natura ---
    try:
        from apply_workday import apply_natura_top  # type: ignore
        natura_apps = apply_natura_top(kept, profile_bundle, GMAIL_FROM_ADDR, _send_smtp_email, append_application, dedupe_check, gen_cover_letter, CV_PDF)
        applications.extend(natura_apps)
    except Exception as e:
        print(f"[apply-workday] err: {e}", file=sys.stderr)

    # --- Apply A3: Gupy Playwright ---
    try:
        from apply_gupy import apply_gupy_top  # type: ignore
        gupy_apps = apply_gupy_top(kept, profile_bundle, EVIDENCE_DIR, append_application, dedupe_check, gen_cover_letter, CV_PDF)
        applications.extend(gupy_apps)
    except Exception as e:
        print(f"[apply-gupy] err: {e}", file=sys.stderr)

    # --- Apply A4: Email direto pra RH da empresa ---
    try:
        from apply_email_direct import apply_email_direct  # type: ignore
        direct_apps = apply_email_direct(kept, profile_bundle, _send_smtp_email, append_application, dedupe_check, gen_cover_letter, CV_PDF)
        applications.extend(direct_apps)
    except Exception as e:
        print(f"[apply-email-direct] err: {e}", file=sys.stderr)

    report = format_report(kept, scores_by_id, run_label, applications=applications, triage_alerts=triage_alerts)
    print(report, file=sys.stderr)
    tg_send(report)
    n8n_forward({
        "run": run_label,
        "ts": datetime.now(timezone.utc).isoformat(),
        "kept_count": len(kept),
        "scores": scores_by_id,
        "vagas_top": [v for v in kept if scores_by_id.get(v["external_id"], {}).get("recommend_apply")],
    })

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
                "applications": applications,
                "triage_alerts": triage_alerts,
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
