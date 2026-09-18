#!/usr/bin/env python3
"""
Vigia do app na Play — roda no GitHub Actions, não no PC de ninguém.

A cada execução:
  1. lê a ficha PÚBLICA da loja (versão, data de atualização, IAP, downloads)
  2. compara com o último estado guardado no repositório
  3. conta os dias até os prazos do Google que podem tirar o app do ar
  4. se houver secret da Play, lê as faixas pela Developer API
  5. escreve o relatório em evidence/play-status.md, commitado pelo workflow

uso:
  python3 kansas/tools/play_watch.py

env: PLAY_SERVICE_ACCOUNT_JSON (opcional)
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

    titulo = primeiro(r'<meta\s+property="og:title"\s+content="([^"<>]{2,120})"')
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


def ficha_valida(f: dict) -> str | None:
    """Devolve o motivo se a ficha não for confiável, ou None se estiver boa.

    Sem isto, uma resposta inesperada da Play (interstício de consentimento,
    página de erro, HTML cortado) era gravada como estado bom e virava um
    'mudou desde a última checagem' fantasma na execução seguinte.
    """
    if f.get("http") != 200:
        return f"HTTP {f.get('http')}"
    t = (f.get("titulo") or "").strip()
    if not t:
        return "sem título na resposta"
    if "<" in t or ">" in t or t.startswith("http"):
        return f"título não parece um nome de app: {t[:40]!r}"
    if not f.get("versao"):
        return "sem número de versão na resposta"
    return None


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


def main() -> int:
    ap = argparse.ArgumentParser()
    args = ap.parse_args()

    hoje = dt.date.today()
    try:
        ficha = buscar_ficha(PACOTE)
    except Exception as e:
        print(f"⚠️ {PACOTE}: não consegui ler a ficha da Play ({type(e).__name__})")
        return 1

    motivo = ficha_valida(ficha)
    if motivo:
        print(f"⚠️ {PACOTE}: a Play devolveu algo que não dá para confiar "
              f"({motivo}). Mantive o último estado bom.")
        return 1

    anterior = {}
    if ESTADO.is_file():
        try:
            anterior = json.loads(ESTADO.read_text(encoding="utf-8"))
        except Exception:
            anterior = {}

    # 'atualizado_em' NÃO entra aqui: a Play serve a ficha por cache regional e
    # a mesma hora pode devolver 16 ou 17 de setembro dependendo de onde o
    # runner está. Verificado: sandbox (BR) e runner do GitHub (US) divergiram
    # no mesmo dia. Vigiar esse campo geraria alerta fantasma toda execução.
    CAMPOS_VIGIADOS = ("versao", "downloads", "tem_iap", "titulo")
    mudou = [c for c in CAMPOS_VIGIADOS if anterior.get(c) != ficha.get(c)]
    primeira_vez = not anterior

    # guarda a data mais recente já vista, para "há N dias" não andar pra trás
    vista = data_br(ficha.get("atualizado_em"))
    antes = anterior.get("atualizado_em_max")
    melhor = max([d for d in (vista, dt.date.fromisoformat(antes) if antes else None) if d],
                 default=None)

    partes = [f"📱 {ficha.get('titulo') or PACOTE}",
              f"versão {ficha.get('versao') or '?'} · atualizado {ficha.get('atualizado_em') or '?'}"
              f" · {ficha.get('downloads') or '?'} downloads",
              f"loja respondeu HTTP {ficha['http']}"]

    if ficha.get("tem_iap"):
        partes.append("compras no app: ativas")

    if melhor:
        partes.append(f"última atualização há {(hoje - melhor).days} dia(s)")

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
    print(relatorio)

    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ficha["checado_em"] = hoje.isoformat()
    if melhor:
        ficha["atualizado_em_max"] = melhor.isoformat()
    ficha["_avisos"] = avisados
    ESTADO.write_text(json.dumps(ficha, ensure_ascii=False, indent=2), encoding="utf-8")

    # Relatório legível fica no repositório, junto da evidência. Sem bot,
    # sem app de mensagem: quem abre o repo (ou uma sessão do Claude) lê.
    md = pathlib.Path("evidence/play-status.md")
    destaque = "ATENÇÃO" if (mudou or urgentes) else "sem novidade"
    md.write_text(
        f"# Play — {ficha.get('titulo') or PACOTE}\n\n"
        f"_checado em {hoje.isoformat()} · {destaque}_\n\n"
        + "\n".join(f"- {linha}" for linha in partes[1:]) + "\n",
        encoding="utf-8")
    print(f"\nrelatório escrito em {md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
