#!/usr/bin/env python3
"""Testes da validação do vigia — o que NUNCA pode virar estado bom."""
import importlib.util, pathlib, sys

spec = importlib.util.spec_from_file_location(
    "pw", pathlib.Path(__file__).parent / "play_watch.py")
pw = importlib.util.module_from_spec(spec); spec.loader.exec_module(pw)

boa = {"http": 200, "titulo": "Dinheiro em Dia", "versao": "1.8.8"}
casos = [
    (boa,                                              None,  "ficha boa passa"),
    ({**boa, "http": 404},                             "HTTP", "404 não vira estado"),
    ({**boa, "http": 503},                             "HTTP", "503 não vira estado"),
    ({**boa, "titulo": "<!--"},                        "título", "HTML cortado não vira título"),
    ({**boa, "titulo": ""},                            "sem título", "título vazio barra"),
    ({**boa, "titulo": None},                          "sem título", "título ausente barra"),
    ({**boa, "titulo": "https://play.google.com"},     "título", "URL não é nome de app"),
    ({**boa, "versao": None},                          "sem número", "sem versão barra"),
]
falhas = 0
for ficha, esperado, nome in casos:
    got = pw.ficha_valida(ficha)
    ok = (got is None and esperado is None) or (got and esperado and esperado in got)
    print(("PASS  " if ok else "FAIL  ") + nome + ("" if ok else f" -> {got!r}"))
    falhas += 0 if ok else 1

# marcos de aviso não podem repetir
assert pw.MARCOS_DIAS and 13 not in pw.MARCOS_DIAS and 7 in pw.MARCOS_DIAS
print("PASS  marcos de aviso configurados (13 dias não avisa, 7 avisa)")

print(f"\nRESULTADO: {'VERMELHO' if falhas else 'VERDE'} — {len(casos)+1-falhas} teste(s) ok")
sys.exit(1 if falhas else 0)
