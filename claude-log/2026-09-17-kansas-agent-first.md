# 2026-09-17 — Kansas IA Financeira: diagnóstico da Play Store + núcleo agent-first

> Nota para os outros agentes (ChatGPT/Codex/sessões futuras). Só fato aqui.

## Descobertas que ninguém tinha escrito ainda

1. **O app está PÚBLICO na Play Store, não fora dela.**
   `com.pulsefinanceiro.dreai` — "Dinheiro em Dia" — v1.8.8, atualizado em
   **17/09/2026**. Página responde HTTP 200. O registro do cockpit Supabase
   (`play_store`, `projetos.dinheiro-em-dia`) está **desatualizado desde
   junho**: dizia "teste fechado, re-solicitar produção ~19/06". Foi superado.
   → **atualizar essas linhas no cockpit** quando alguém tiver a informação
   fresca do Play Console.

2. **Prazo real e datado: 30/09/2026 — verificação de desenvolvedor Android.**
   E-mails do `googleplay-noreply@google.com` em 07/08 e 04/09/2026 ("último
   lembrete"): apps não registrados *"serão removidos da plataforma no mundo
   todo"*. >99% foram registrados automaticamente (chave de assinatura do Play).
   Só a home do Play Console diz se este pacote está na lista — não há API.

3. **Target SDK (confirmado na doc do Google, não de memória):** atualização
   nova exige **API 36**; app existente precisa de **API 35** para continuar
   aparecendo a novos usuários em Android recente; prazo 31/08/2026, com
   prorrogação possível até 01/11/2026.

4. **Os dois sintomas do usuário são o mesmo fio:** subir para 35/36 liga
   edge-to-edge no Android 15+, a janela passa a desenhar atrás das barras, e
   menu/botão sem tratamento de inset some embaixo delas.

5. **Onde o app vive:** React Native + Firebase, fonte no PC Windows
   (`C:\Dev`, pelo registro de ações do cockpit). **Não está em nenhum
   repositório GitHub alcançável** — a sessão só enxerga
   `fabiokansas-maker/AUTOMA-O`. Drive não tem espelho do código, e
   `AUTOMA-O/Bridge/last-heartbeat.json` não existe → **a PC bridge deste repo
   não está rodando**.

## O que foi construído (branch `claude/kansas-agent-first-rebuild-ptcc1w`)

Diretório `kansas/`, tudo rodando e testado nesta sessão:

- `db/001..003` — núcleo agent-first: threads, mensagens, memória privada por
  agente, fatos compartilhados, eventos entre agentes, feedback/denúncia de IA,
  exclusão de conta, auditoria. Migrations **aditivas** (rollback = drop schema).
- **Duas fronteiras no banco**: usuário (`auth.uid() = user_id`) e agente
  (`kansas.current_agent() = agent_id` + allowlist do registry).
- `db/run_tests.sh` — sobe Postgres efêmero e roda **29 testes de isolamento**
  que tentam violar as fronteiras de propósito. Verde nesta sessão.
- `backend/` — contexto do JWT, registry, router, tools estreitas validadas,
  serviços financeiros determinísticos (Money em centavos), blocos tipados.
  **30 testes unitários** verdes (`node --experimental-strip-types`).
- `app/` — AgentHome + AgentScreen + BlockRenderer + money.ts, com insets
  (`useSafeAreaInsets`) em vez de padding mágico e `Intl` em vez de `"R$ " +`.
- `tools/audit_app.py` — Fase Zero automática sobre o repo do app; validado
  contra fixture (achou targetSdk 34, `StatusBar.currentHeight`, moeda
  concatenada, `user_id` vindo do modelo, RPC de SQL livre).
- `tools/audit_policies.py` — impede migration futura reabrir buraco. Roda no CI.
- `.github/workflows/kansas-security.yml` — os três checks a cada push.

## Bug que os testes pegaram (e já corrigido)

`routeBySignals("quanto posso gastar sem comprometer minha meta?")` caía só em
`goals`. Faltava "posso gastar" nos sinais de orçamento — sem isso a pergunta
cruzada não subia para o Planejamento. Corrigido em `backend/router.ts`.

## Próximo passo concreto

Assim que o fonte do app for alcançável (repo novo no GitHub, ou a bridge do PC
voltando a rodar): `python3 kansas/tools/audit_app.py <repo>` responde em
segundos o targetSdk real, o inventário de telas e a matriz tela→agente. Nada
antes disso depende de mais informação.
