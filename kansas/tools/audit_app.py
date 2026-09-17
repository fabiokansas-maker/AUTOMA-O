#!/usr/bin/env python3
"""
Auditor Fase Zero do app Kansas / Dinheiro em Dia.

Roda contra o repositório do app (React Native ou Android nativo) e produz o
inventário que a especificação pede — SEM ninguém abrir arquivo na mão:

  * identidade de publicação (applicationId, namespace, versionCode, signing)
  * prontidão Play Store 2026 (target SDK, edge-to-edge)
  * telas existentes -> agente responsável (matriz reaproveitar/migrar/trocar)
  * bugs de inset/sobreposição (padding mágico, StatusBar.currentHeight…)
  * i18n (moeda concatenada, data fixa, string não externalizada)
  * segurança de IA (user_id escolhido pelo modelo, SQL livre, segredo no repo)

uso:
  python3 kansas/tools/audit_app.py /caminho/do/repo-do-app [--json saida.json]

Sai com código 1 se encontrar achado BLOQUEANTE.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

IGNORAR = {"node_modules", ".git", "build", ".gradle", "Pods", "dist",
           "vendor", ".idea", "__pycache__", "ios/Pods"}
EXT_CODIGO = {".js", ".jsx", ".ts", ".tsx", ".kt", ".java", ".dart", ".xml"}

SEVERIDADES = ("bloqueante", "alto", "medio", "info")


class Achado:
    def __init__(self, sev: str, categoria: str, msg: str,
                 arquivo: str = "", linha: int = 0):
        self.sev, self.categoria, self.msg = sev, categoria, msg
        self.arquivo, self.linha = arquivo, linha

    def to_dict(self) -> dict:
        return {"severidade": self.sev, "categoria": self.categoria,
                "mensagem": self.msg, "arquivo": self.arquivo, "linha": self.linha}


def arquivos(raiz: pathlib.Path):
    for p in raiz.rglob("*"):
        if not p.is_file():
            continue
        if any(parte in IGNORAR for parte in p.parts):
            continue
        yield p


# ---------------------------------------------------------------- identidade
def auditar_identidade(raiz: pathlib.Path, ach: list[Achado]) -> dict:
    info: dict = {}
    gradles = [p for p in arquivos(raiz) if p.name in ("build.gradle", "build.gradle.kts")]
    for g in gradles:
        txt = g.read_text(encoding="utf-8", errors="ignore")
        for campo, padrao in (
            ("applicationId", r"applicationId\s*=?\s*[\"']([\w.]+)[\"']"),
            ("namespace",     r"namespace\s*=?\s*[\"']([\w.]+)[\"']"),
            ("targetSdk",     r"targetSdk(?:Version)?\s*=?\s*(\d+)"),
            ("compileSdk",    r"compileSdk(?:Version)?\s*=?\s*(\d+)"),
            ("minSdk",        r"minSdk(?:Version)?\s*=?\s*(\d+)"),
            ("versionCode",   r"versionCode\s*=?\s*(\d+)"),
            ("versionName",   r"versionName\s*=?\s*[\"']([^\"']+)[\"']"),
        ):
            m = re.search(padrao, txt)
            if m and campo not in info:
                info[campo] = m.group(1)
        if "signingConfigs" in txt:
            info["temSigningConfig"] = True

    # projeto RN costuma guardar o target em android/build.gradle (ext)
    if "targetSdk" not in info:
        for g in gradles:
            m = re.search(r"targetSdkVersion\s*=\s*(\d+)",
                          g.read_text(encoding="utf-8", errors="ignore"))
            if m:
                info["targetSdk"] = m.group(1)
                break

    if not info.get("applicationId"):
        ach.append(Achado("alto", "identidade",
                          "applicationId não encontrado — confirme antes de qualquer "
                          "rebranding: trocá-lo faz a Play tratar o envio como OUTRO app"))
    if not info.get("temSigningConfig"):
        ach.append(Achado("alto", "identidade",
                          "nenhum signingConfigs no Gradle — a identidade de assinatura "
                          "precisa continuar a mesma para atualizar o app publicado"))

    alvo = int(info.get("targetSdk", 0) or 0)
    if alvo and alvo < 35:
        ach.append(Achado("bloqueante", "play-store",
                          f"targetSdk={alvo}: abaixo de 35 o app deixa de aparecer para "
                          "novos usuários em Android recente"))
    elif alvo and alvo < 36:
        ach.append(Achado("bloqueante", "play-store",
                          f"targetSdk={alvo}: toda ATUALIZAÇÃO nova precisa mirar 36+"))
    elif not alvo:
        ach.append(Achado("alto", "play-store", "targetSdk não identificado no Gradle"))
    return info


# ------------------------------------------------------------ insets / layout
PADRAO_INSET = [
    (r"paddingTop\s*:\s*(\d{2,})", "medio",
     "paddingTop numérico fixo — status bar varia por aparelho; use insets"),
    (r"paddingBottom\s*:\s*(\d{2,})", "medio",
     "paddingBottom numérico fixo — barra de gestos ≠ 3 botões; use insets"),
    (r"marginTop\s*:\s*(\d{2,})\s*,?\s*//.*status", "alto",
     "margem chutada para compensar a status bar"),
    (r"StatusBar\.currentHeight", "alto",
     "StatusBar.currentHeight não cobre notch, gestos nem paisagem"),
    (r"height\s*:\s*(?:56|48|80|100)\b.*(?:bottom|nav)", "medio",
     "altura fixa de barra inferior"),
]


def auditar_layout(raiz: pathlib.Path, ach: list[Achado]) -> dict:
    usa_safearea = usa_edge2edge = False
    telas: list[str] = []
    for p in arquivos(raiz):
        if p.suffix not in EXT_CODIGO:
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = str(p.relative_to(raiz))

        if "react-native-safe-area-context" in txt or "useSafeAreaInsets" in txt:
            usa_safearea = True
        if "enableEdgeToEdge" in txt or "setDecorFitsSystemWindows" in txt \
                or "WindowCompat" in txt:
            usa_edge2edge = True
        if re.search(r"(Screen|Page|Activity|Fragment)\.(tsx|jsx|kt|java)$", p.name) \
                or re.search(r"(Screen|Page)$", p.stem):
            telas.append(rel)

        for padrao, sev, msg in PADRAO_INSET:
            for m in re.finditer(padrao, txt):
                linha = txt[:m.start()].count("\n") + 1
                ach.append(Achado(sev, "insets", msg, rel, linha))

    if not usa_safearea:
        ach.append(Achado("alto", "insets",
                          "projeto não usa react-native-safe-area-context (nem insets "
                          "equivalentes): em Android 15+ o conteúdo desenha atrás das barras"))
    if not usa_edge2edge:
        ach.append(Achado("medio", "insets",
                          "nenhuma configuração explícita de edge-to-edge encontrada"))
    return {"telas": sorted(set(telas)), "usa_safe_area": usa_safearea,
            "usa_edge_to_edge": usa_edge2edge}


# ------------------------------------------------------------------- i18n
def auditar_i18n(raiz: pathlib.Path, ach: list[Achado]) -> None:
    padroes = [
        (r"[\"']R\$\s*[\"']\s*\+", "alto", "moeda concatenada na mão (\"R$ \" + valor)"),
        (r"`R\$\s*\$\{", "alto", "moeda concatenada em template string"),
        (r"toFixed\(2\)[^\n]{0,40}R\$", "alto", "formatação manual de dinheiro"),
        (r"[\"']DD/MM/YYYY[\"']", "medio", "formato de data fixo"),
        (r"locale\s*[:=]\s*[\"']pt-BR[\"']", "medio", "locale fixo no código"),
        (r"currency\s*[:=]\s*[\"']BRL[\"']", "medio", "moeda fixa no código"),
        (r"America/Sao_Paulo", "medio", "timezone fixo no código"),
    ]
    for p in arquivos(raiz):
        if p.suffix not in EXT_CODIGO:
            continue
        txt = p.read_text(encoding="utf-8", errors="ignore")
        rel = str(p.relative_to(raiz))
        for padrao, sev, msg in padroes:
            for m in re.finditer(padrao, txt):
                ach.append(Achado(sev, "i18n", msg, rel, txt[:m.start()].count("\n") + 1))


# --------------------------------------------------------- segurança de IA
def auditar_ia(raiz: pathlib.Path, ach: list[Achado]) -> None:
    padroes = [
        (r"(?:queryDatabase|runSql|executeSql)\s*\(", "bloqueante",
         "tool de SQL livre exposta ao modelo"),
        (r"user_?[Ii]d\s*[:=]\s*(?:args|params|toolInput|input)\.", "bloqueante",
         "user_id vindo do argumento da tool (o modelo escolhe o usuário)"),
        (r"service_role|SERVICE_ROLE_KEY", "bloqueante",
         "chave service_role referenciada no código do app"),
        (r"(?:sk-[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_\-]{30,})", "bloqueante",
         "possível chave de API em texto no repositório"),
        (r"console\.log\([^)]*(?:card|cartao|cvv|senha|password|token)", "alto",
         "log com dado sensível"),
        (r"\.rpc\(\s*[\"']exec", "bloqueante", "RPC genérica de execução"),
    ]
    tem_feedback = tem_delete = False
    for p in arquivos(raiz):
        if p.suffix not in EXT_CODIGO | {".json", ".env", ".properties"}:
            continue
        txt = p.read_text(encoding="utf-8", errors="ignore")
        rel = str(p.relative_to(raiz))
        if re.search(r"report|denunciar|flag_response", txt, re.I):
            tem_feedback = True
        if re.search(r"delete_?account|excluir_?conta|deleteUser", txt, re.I):
            tem_delete = True
        for padrao, sev, msg in padroes:
            for m in re.finditer(padrao, txt):
                ach.append(Achado(sev, "seguranca-ia", msg, rel,
                                  txt[:m.start()].count("\n") + 1))
    if not tem_feedback:
        ach.append(Achado("bloqueante", "politica-play",
                          "não achei mecanismo de DENÚNCIA de resposta de IA dentro do "
                          "app — o Play exige para apps que geram conteúdo com IA"))
    if not tem_delete:
        ach.append(Achado("alto", "politica-play",
                          "não achei fluxo de exclusão de conta/dados no app"))


# ------------------------------------------- matriz tela -> agente futuro
MAPA_AGENTE = [
    (r"invoice|fatura|card|cartao", "invoices"),
    (r"balance|saldo|account|conta", "balance"),
    (r"goal|meta|objetivo", "goals"),
    (r"transaction|transacao|extrato|lancamento", "transactions"),
    (r"budget|orcamento|categoria", "budget"),
    (r"insight|planning|planejamento|dashboard|home", "planning"),
]


def matriz(telas: list[str]) -> list[dict]:
    linhas = []
    for t in telas:
        agente = next((a for padrao, a in MAPA_AGENTE if re.search(padrao, t, re.I)), None)
        linhas.append({
            "tela": t,
            "agente_futuro": agente or "(decidir)",
            "acao": "trocar UI, reaproveitar repository" if agente else "revisar",
        })
    return linhas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--md", dest="md_out")
    ap.add_argument("--require-target", type=int, default=0,
                    help="falha se o targetSdk for menor que este valor "
                         "(use 36: exigência do Play para atualizações novas)")
    args = ap.parse_args()

    raiz = pathlib.Path(args.repo).resolve()
    if not raiz.is_dir():
        print(f"ERRO: {raiz} não é um diretório")
        return 2

    ach: list[Achado] = []
    identidade = auditar_identidade(raiz, ach)
    layout = auditar_layout(raiz, ach)
    auditar_i18n(raiz, ach)
    auditar_ia(raiz, ach)

    ach.sort(key=lambda a: SEVERIDADES.index(a.sev))
    relatorio = {
        "repo": str(raiz),
        "identidade": identidade,
        "layout": {k: v for k, v in layout.items() if k != "telas"},
        "telas": layout["telas"],
        "matriz_tela_agente": matriz(layout["telas"]),
        "achados": [a.to_dict() for a in ach],
        "resumo": {s: sum(1 for a in ach if a.sev == s) for s in SEVERIDADES},
    }

    print(f"# Auditoria Fase Zero — {raiz.name}\n")
    print("## Identidade de publicação")
    for k, val in (identidade or {"(nada encontrado)": ""}).items():
        print(f"- {k}: {val}")
    print(f"\n## Telas encontradas: {len(layout['telas'])}")
    for linha in relatorio["matriz_tela_agente"][:40]:
        print(f"- {linha['tela']} -> {linha['agente_futuro']}")
    print("\n## Achados")
    for a in ach[:200]:
        local = f" ({a.arquivo}:{a.linha})" if a.arquivo else ""
        print(f"- [{a.sev.upper()}] {a.categoria}: {a.msg}{local}")
    print(f"\n## Resumo: {relatorio['resumo']}")

    if args.json_out:
        pathlib.Path(args.json_out).write_text(
            json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.require_target:
        alvo = int(identidade.get("targetSdk", 0) or 0)
        if alvo < args.require_target:
            print(f"\nPORTA FECHADA: targetSdk={alvo or '?'} < {args.require_target}. "
                  "A Play recusa o upload — corrija o Gradle antes de gerar o AAB.")
            return 1
        print(f"\nPORTA ABERTA: targetSdk={alvo} atende o mínimo {args.require_target}.")

    return 1 if relatorio["resumo"]["bloqueante"] else 0


if __name__ == "__main__":
    sys.exit(main())
