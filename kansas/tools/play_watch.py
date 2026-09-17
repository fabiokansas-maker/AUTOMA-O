#!/usr/bin/env python3
"""
Vigia do app na Play — roda no GitHub Actions, não no PC de ninguém.

A cada execução:
  1. lê a ficha PÚBLICA da loja (versão, data de atualização, IAP, downloads)
  2. compara com o último estado guardado no repositório
  3. conta os dias até os prazos do Google que podem tirar o app do ar
  4. se houver secret da Play, lê as faixas pela Developer API
  5. manda relatório no Telegram só quando há o que dizer

uso:
  python3 kansas/tools/play_watch.py                 # relatório no stdout
  python3 kansas/tools/play_watch.py --telegram      # manda no Telegram
  python3 kansas/tools/play_watch.py --force         # manda mesmo sem novidade

env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, PLAY_SERVICE_ACCOUNT_JSON (opcional)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import sys
import urllib.parse
import urllib.request

PACOTE = os.environ.get("KANSAS_PACKAGE", "com.pulsefinanceiro.dreai")
ESTADO = pathlib.Path(os.environ.get("KANSAS_STATE", "evidence/play-state.json"))
UA = "Mozilla/5.0 (Linux; Android 14; pt-BR) AppleWebKit/537.36"

# Prazos do Google que têm data e consequência conhecidas.
PRAZOS = [
    ("verificação de desenvolvedor Android", dt.date(2026, 9, 30),
     "apps não registrados são removidos da plataforma no mundo todo"),
    ("prorrogação do target SDK (último dia)", dt.date(2026, 11, 1),
     "fim da janela de prorrogação para continuar distribuindo a todos"),
]

# Só avisa nestes marcos. Sem isto, um prazo de 13 dias viraria 26 mensagens.
MARCOS_DIAS = {30, 14, 7, 5, 3, 2, 1, 0}

MESES = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
         "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}


def buscar_ficha(pacote: str) -> dict:
    url = ("https://play.google.com/store/apps/details?"
           + urllib.parse.urlencode({"id": pacote, "hl": "pt_BR", "gl": "BR"}))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", "replace")
        status = r.status

    texto = re.sub(r"<[^>]+>", " ", html)
    texto = re.sub(r"\s+", " ", texto)

    def primeiro(padrao: str, alvo: str = html) -> str | None:
        m = re.search(padrao, alvo)
        return m.group(1) if m else None

    titulo = primeiro(r'property="og:title"[^>]*content="([^"]*)"')
    if titulo:  # a loja devolve "Nome – Apps no Google Play"
        titulo = re.split(r"\s+[–-]\s+Apps no Google Play", titulo)[0].strip()

    return {
        "http": status,
        "titulo": titulo,
        "descricao": primeiro(r'property="og:description"[^>]*content="([^"]*)"'),
        "versao": primeiro(r'"(\d+\.\d+\.\d+)"'),
        "atualizado_em": primeiro(r"Atualizado em ([0-9]{1,2} de \w+\.? de \d{4})", texto),
        "downloads": primeiro(r"([\d.,]+\+?) downloads", texto),
        "tem_iap": "Compras no app" in html,
        "tem_anuncios": "Contém anúncios" in html,
    }


def data_br(s: str | None) -> dt.date | None:
    if not s:
        return None
    m = re.match(r"(\d{1,2}) de (\w+)\.? de (\d{4})", s)
    if not m:
        return None
    mes = MESES.get(m.group(2)[:3].lower())
    return dt.date(int(m.group(3)), mes, int(m.group(1))) if mes else None


def faixas_da_api() -> list[str]:
    """Só roda se o secret existir; nunca publica nada."""
    caminho = os.environ.get("PLAY_SERVICE_ACCOUNT_JSON", "")
    if not caminho or not os.path.isfile(caminho):
        return []
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    try:
        import play_status  # type: ignore
        chave = json.load(open(caminho, encoding="utf-8"))
        token = play_status.access_token(chave)
        edit = play_status.post(f"{play_status.API}/{PACOTE}/edits", token)
        try:
            tracks = play_status.get(
                f"{play_status.API}/{PACOTE}/edits/{edit['id']}/tracks", token
            ).get("tracks", [])
            linhas = []
            for t in tracks:
                for rel in t.get("releases", []):
                    codigos = ", ".join(map(str, rel.get("versionCodes", []) or [])) or "—"
                    linhas.append(f"{t['track']}: {rel.get('status')} (vc {codigos})")
            return linhas
        finally:
            try:
                play_status.delete(f"{play_status.API}/{PACOTE}/edits/{edit['id']}", token)
            except Exception:
                pass
    except Exception as e:
        return [f"API da Play indisponível: {type(e).__name__}"]


def telegram(texto: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat:
        print("(sem TELEGRAM_BOT_TOKEN/CHAT_ID — não enviei)")
        return False
    dados = urllib.parse.urlencode({
        "chat_id": chat, "text": texto,
        "parse_mode": "HTML", "disable_web_page_preview": "true",
    }).encode()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    with urllib.request.urlopen(urllib.request.Request(url, data=dados), timeout=30) as r:
        return json.load(r).get("ok", False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--telegram", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    hoje = dt.date.today()
    try:
        ficha = buscar_ficha(PACOTE)
    except Exception as e:
        linha = f"⚠️ <b>{PACOTE}</b>: não consegui ler a ficha da Play ({type(e).__name__})"
        print(linha)
        if args.telegram:
            telegram(linha)
        return 1

    anterior = {}
    if ESTADO.is_file():
        try:
            anterior = json.loads(ESTADO.read_text(encoding="utf-8"))
        except Exception:
            anterior = {}

    mudou = [c for c in ("versao", "atualizado_em", "downloads", "tem_iap", "titulo")
             if anterior.get(c) != ficha.get(c)]
    primeira_vez = not anterior

    partes = [f"📱 <b>{ficha.get('titulo') or PACOTE}</b>",
              f"versão {ficha.get('versao') or '?'} · atualizado {ficha.get('atualizado_em') or '?'}"
              f" · {ficha.get('downloads') or '?'} downloads",
              f"loja respondeu HTTP {ficha['http']}"]

    if ficha.get("tem_iap"):
        partes.append("compras no app: ativas")

    d = data_br(ficha.get("atualizado_em"))
    if d:
        dias = (hoje - d).days
        partes.append(f"última atualização há {dias} dia(s)")

    if mudou and not primeira_vez:
        antes_depois = ", ".join(
            f"{c}: {anterior.get(c)!r} → {ficha.get(c)!r}" for c in mudou)
        partes.append(f"🔔 mudou desde a última checagem — {antes_depois}")

    urgentes = []
    avisados = dict(anterior.get("_avisos", {}))
    for nome, prazo, consequencia in PRAZOS:
        faltam = (prazo - hoje).days
        if faltam < 0:
            continue
        marca = "🚨" if faltam <= 14 else "⏳"
        linha = f"{marca} {nome}: faltam {faltam} dia(s) ({prazo:%d/%m/%Y})"
        partes.append(linha)
        # avisa só no marco, e só uma vez por marco
        if faltam in MARCOS_DIAS and avisados.get(nome) != faltam:
            urgentes.append(f"{linha} — {consequencia}")
            avisados[nome] = faltam

    for linha in faixas_da_api():
        partes.append(f"faixa · {linha}")

    relatorio = "\n".join(partes)
    print(relatorio.replace("<b>", "").replace("</b>", ""))

    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ficha["checado_em"] = hoje.isoformat()
    ficha["_avisos"] = avisados
    ESTADO.write_text(json.dumps(ficha, ensure_ascii=False, indent=2), encoding="utf-8")

    vale_avisar = bool(mudou) or bool(urgentes) or primeira_vez or args.force
    if args.telegram and vale_avisar:
        print("telegram:", "enviado" if telegram(relatorio) else "falhou")
    elif args.telegram:
        print("(nada novo e nenhum prazo apertado — não enchi seu Telegram)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
