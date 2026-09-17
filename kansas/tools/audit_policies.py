#!/usr/bin/env python3
"""
Auditor estático das migrations do Kansas.

Impede que uma migration futura reabra um buraco que os testes de runtime
talvez não cubram (tabela nova sem RLS, policy que confia em dado do cliente,
tool com SQL livre). Roda no CI e falha o build.

uso: python3 kansas/tools/audit_policies.py kansas/db
"""
import re
import sys
import pathlib

# Padrões que NUNCA podem aparecer numa policy/função exposta ao cliente.
PROIBIDO = [
    (r"current_setting\(\s*'request\.headers'", "policy confiando em header do cliente"),
    (r"execute\s+format\(\s*'select\s+\*\s+from\s+'\s*\|\|", "SQL dinâmico montado com entrada"),
    (r"\buser_id\s*=\s*current_setting\('kansas\.user", "user_id vindo de GUC em vez do JWT"),
    (r"create\s+policy[\s\S]{0,400}?using\s*\(\s*true\s*\)", "policy com USING (true)"),
    (r"grant\s+all\s+on\s+schema\s+kansas\s+to\s+(anon|authenticated)", "grant amplo para o cliente"),
    (r"security\s+definer[\s\S]{0,200}?set\s+search_path\s*=\s*public", "definer com search_path inseguro"),
]

def main(root: str) -> int:
    d = pathlib.Path(root)
    sqls = sorted(p for p in d.glob("*.sql"))
    if not sqls:
        print(f"ERRO: nenhuma migration em {root}")
        return 1

    texto = "\n".join(p.read_text(encoding="utf-8") for p in sqls)
    baixo = texto.lower()
    falhas: list[str] = []

    # 1. toda tabela de usuário precisa de RLS ligada
    tabelas = set(re.findall(r"create table if not exists kansas\.(\w+)", baixo))
    com_rls = set(re.findall(r"alter table kansas\.(\w+)\s+enable row level security", baixo))
    sem_rls = {t for t in tabelas - com_rls if t != "agents"}
    for t in sorted(sem_rls):
        falhas.append(f"tabela kansas.{t} sem ENABLE ROW LEVEL SECURITY")

    # 2. toda tabela com dado de usuário precisa de coluna user_id
    corpo = {}
    for m in re.finditer(r"create table if not exists kansas\.(\w+)\s*\((.*?)\n\);", texto,
                         re.S | re.I):
        corpo[m.group(1).lower()] = m.group(2).lower()
    for t, c in corpo.items():
        if t in ("agents", "audit_events"):
            continue
        if "user_id" not in c:
            falhas.append(f"tabela kansas.{t} sem coluna user_id")

    # 3. toda policy precisa citar auth.uid() — a identidade vem do JWT
    for m in re.finditer(r"create policy (\w+) on kansas\.(\w+)(.*?);\s*\n", texto,
                         re.S | re.I):
        nome, tabela, corpo_pol = m.group(1), m.group(2).lower(), m.group(3).lower()
        if tabela == "agents":
            continue
        if "auth.uid()" not in corpo_pol:
            falhas.append(f"policy {nome} em kansas.{tabela} não usa auth.uid()")

    # 4. tabelas sensíveis exigem a fronteira de agente além da de usuário
    for tabela, pol in (("agent_memories", "memories_rw"), ("agent_events", "events_read")):
        m = re.search(rf"create policy {pol} on kansas\.{tabela}(.*?);\s*\n", texto, re.S | re.I)
        if not m:
            falhas.append(f"policy {pol} ausente")
        elif "kansas.current_agent()" not in m.group(1).lower():
            falhas.append(f"policy {pol} não impõe a fronteira de agente")

    # 5. padrões proibidos
    for padrao, motivo in PROIBIDO:
        if re.search(padrao, baixo, re.I):
            falhas.append(f"padrão proibido encontrado: {motivo}")

    print(f"Auditoria estática de {len(sqls)} migration(s), {len(tabelas)} tabela(s).")
    if falhas:
        for f in falhas:
            print(f"  FAIL  {f}")
        print(f"\nRESULTADO: VERMELHO — {len(falhas)} problema(s).")
        return 1
    print("  PASS  toda tabela de usuário tem RLS e user_id")
    print("  PASS  toda policy deriva identidade de auth.uid()")
    print("  PASS  memória e eventos impõem também a fronteira de agente")
    print("  PASS  nenhum padrão proibido (USING(true), SQL livre, grant amplo)")
    print("\nRESULTADO: VERDE")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "kansas/db"))
