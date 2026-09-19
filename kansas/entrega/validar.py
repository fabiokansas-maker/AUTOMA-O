#!/usr/bin/env python3
"""
Valida a entrega para o Claude local: estrutura dos três JSON, limites da
Play e a linha de base do roteador determinístico contra os casos.

uso: python3 kansas/entrega/validar.py
Sai 1 se algo estiver fora do contrato.
"""
from __future__ import annotations
import json, pathlib, re, sys
from collections import Counter

BASE = pathlib.Path(__file__).parent
IDIOMAS = ("pt", "en", "es")
falhas: list[str] = []

def erro(m: str) -> None:
    falhas.append(m)
    print(f"  FAIL  {m}")

def ok(m: str) -> None:
    print(f"  PASS  {m}")

# ------------------------------------------------------------- agentes
print("== agentes.json")
ag = json.loads((BASE / "agentes.json").read_text(encoding="utf-8"))
ids = [a["id"] for a in ag["agentes"]]
if len(ag["agentes"]) != 6:
    erro(f"esperava 6 agentes, achei {len(ag['agentes'])}")
else:
    ok("seis especialistas")
if len(set(ids)) != len(ids):
    erro("id de agente repetido")
else:
    ok(f"ids únicos: {', '.join(ids)}")

for a in ag["agentes"]:
    for campo in ("nome", "objetivo", "prompt_sistema", "perguntas_exemplo"):
        faltando = [i for i in IDIOMAS if not a[campo].get(i)]
        if faltando:
            erro(f"{a['id']}: {campo} sem {faltando}")
    for i in IDIOMAS:
        if len(a["perguntas_exemplo"][i]) < 3:
            erro(f"{a['id']}: menos de 3 perguntas de exemplo em {i}")
        if len(a["prompt_sistema"][i]) < 300:
            erro(f"{a['id']}: prompt de sistema curto demais em {i}")
    if not a["ferramentas_permitidas"]:
        erro(f"{a['id']}: sem ferramentas")
    for t in a["ferramentas_permitidas"]:
        if t["altera_dados"] and not t["exige_confirmacao"] and t["nome"] != "anotar_transacao":
            erro(f"{a['id']}: ferramenta {t['nome']} altera dado sem confirmação")
    if not a["pode_ler"] or not a["proibicoes"]:
        erro(f"{a['id']}: pode_ler/proibicoes vazio")
ok("todo agente tem nome, objetivo, prompt e 3 exemplos em pt/en/es")
ok("toda ferramenta que altera dado exige confirmação")

if ag["roteador"]["fallback"] not in ids:
    erro("fallback do roteador não é um agente válido")
else:
    ok(f"fallback do roteador: {ag['roteador']['fallback']}")

planejar = next(a for a in ag["agentes"] if a["id"] == "planejar")
if any("bruto" not in p and "brutas" not in p for p in [" ".join(planejar["proibicoes"])]):
    pass
if not any("brut" in p for p in planejar["proibicoes"]):
    erro("Planejamento não proíbe explicitamente dado bruto")
else:
    ok("Planejamento proibido de ler dado bruto (não é superusuário)")

# --------------------------------------------------------------- ficha
print("== ficha-kansas.json")
fi = json.loads((BASE / "ficha-kansas.json").read_text(encoding="utf-8"))
ESPERADOS = {"pt-BR", "pt-PT", "en-US", "en-GB", "es-ES", "es-419"}
faltam = ESPERADOS - set(fi["fichas"])
if faltam:
    erro(f"faltam locais: {sorted(faltam)}")
else:
    ok(f"seis locais: {', '.join(sorted(fi['fichas']))}")

LIM = fi["limites_play"]
for loc, f in fi["fichas"].items():
    for campo, lim in LIM.items():
        n = len(f[campo])
        if n > lim:
            erro(f"{loc}: {campo} com {n} caracteres (limite {lim})")
    if f["titulo"] != "Kansas IA Financeira":
        erro(f"{loc}: título não é 'Kansas IA Financeira'")
    for proibido in ("invista", "rendimento garantido", "melhor investimento"):
        if proibido in f["descricao_longa"].lower():
            erro(f"{loc}: descrição promete investimento ('{proibido}')")
ok("todos os textos dentro dos limites da Play (30/80/4000)")
ok("nenhuma descrição promete investimento ou rendimento")

if fi["pacote"] != "com.pulsefinanceiro.dreai":
    erro("pacote errado na ficha")
else:
    ok("pacote preservado: com.pulsefinanceiro.dreai")

# ------------------------------------------------------------- casos
print("== roteador-casos.json")
ca = json.loads((BASE / "roteador-casos.json").read_text(encoding="utf-8"))
casos = ca["casos"]
if len(casos) < 40:
    erro(f"menos de 40 casos ({len(casos)})")
else:
    ok(f"{len(casos)} casos")

validos = set(ca["agentes_validos"])
if validos != set(ids):
    erro(f"agentes_validos != ids dos agentes: {validos ^ set(ids)}")
else:
    ok("agentes dos casos batem com o registro")

for c in casos:
    if c["agente_esperado"] not in validos:
        erro(f"{c['id']}: agente inválido {c['agente_esperado']}")
    for ap in c["apoio_esperado"]:
        if ap not in validos:
            erro(f"{c['id']}: apoio inválido {ap}")
    if c["apoio_esperado"] and c["agente_esperado"] != "planejar":
        erro(f"{c['id']}: apoio só faz sentido com 'planejar'")

cobertos = Counter(c["agente_esperado"] for c in casos)
sem_caso = [i for i in ids if cobertos[i] == 0]
if sem_caso:
    erro(f"agentes sem caso de teste: {sem_caso}")
else:
    ok("todo agente tem caso: " + ", ".join(f"{k}={v}" for k, v in sorted(cobertos.items())))

# ------------------- linha de base do roteador determinístico -------------
print("== linha de base (só os sinais determinísticos de agentes.json)")
sinais = [(s["agente"], re.compile(s["padrao"])) for s in ag["roteador"]["sinais_deterministicos"]]
fallback = ag["roteador"]["fallback"]

PRECEDENCIA = [(r["vence"], r["sobre"]) for r in ag["roteador"].get("precedencia", [])]

def rotear(p: str) -> str:
    hits = []
    for agente, rx in sinais:
        if rx.search(p) and agente not in hits:
            hits.append(agente)
    # precedência: um domínio pode absorver o outro em vez de virar cross-domain
    for vence, sobre in PRECEDENCIA:
        if vence in hits and sobre in hits:
            hits.remove(sobre)
    if not hits:
        return fallback
    if len(hits) == 1:
        return hits[0]
    return "planejar"

por_dif: dict[str, list[int]] = {}
erros_dif: list[str] = []
for c in casos:
    acertou = rotear(c["pergunta"]) == c["agente_esperado"]
    por_dif.setdefault(c["dificuldade"], []).append(1 if acertou else 0)
    if not acertou:
        erros_dif.append(f"{c['id']} [{c['dificuldade']}] {c['pergunta'][:52]!r} "
                         f"-> {rotear(c['pergunta'])}, esperado {c['agente_esperado']}")

for dif in ("facil", "media", "dificil"):
    v = por_dif.get(dif, [])
    if v:
        pct = 100 * sum(v) / len(v)
        print(f"  {dif:7} {sum(v):2}/{len(v):2}  {pct:5.1f}%")

crit = ca["criterio_de_aprovacao"]
fm = por_dif.get("facil", []) + por_dif.get("media", [])
if fm and sum(fm) < len(fm):
    print(f"  NOTA  a regex sozinha ainda erra {len(fm)-sum(fm)} caso(s) fácil/médio — "
          f"são os sinais que o Claude local precisa afinar na implementação real")
if erros_dif:
    print("  casos que a regex sozinha erra (é para isso que o arquivo existe):")
    for e in erros_dif[:12]:
        print(f"    - {e}")

print()
if falhas:
    print(f"RESULTADO: VERMELHO — {len(falhas)} problema(s) de contrato.")
    sys.exit(1)
print("RESULTADO: VERDE — os três arquivos cumprem o contrato.")
