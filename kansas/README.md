# Kansas IA Financeira — núcleo agent-first

Núcleo pronto para ser acoplado ao app **Dinheiro em Dia**
(`com.pulsefinanceiro.dreai`, React Native) sem trocar a identidade de
publicação e sem reescrita cega.

> Diagnóstico factual da Play Store (com evidências e com o que eu **não**
> consegui verificar): **[AUDITORIA-PLAY-STORE.md](AUDITORIA-PLAY-STORE.md)**

## A regra que o código inteiro obedece

> **O modelo de IA não é a barreira de segurança.**

O `user_id` sai do JWT verificado, entra num `AgentRequestContext` imutável e é
o backend que o injeta em toda consulta. O modelo pode pedir *"as transações
dos últimos 30 dias"*; ele não pode dizer **de quem**.

```
app  ──JWT──>  Edge Function  ──begin; set role authenticated;
                    │            set_agent('invoices'); …
                    │
                    ├─ registry (quem pode qual tool)
                    ├─ tools estreitas e validadas   ──> services determinísticos
                    └─ contexto mínimo para o modelo
                                    │
                            Postgres + RLS   <- fronteira real
```

Duas fronteiras, as duas no banco:

| Fronteira | Como é imposta | Testes |
|---|---|---|
| usuário A × usuário B | `auth.uid() = user_id` no RLS | 10 |
| agente × agente | `kansas.current_agent() = agent_id` + allowlist do registry | 19 |

## Rodar os testes (zero clique, zero nuvem)

```bash
bash kansas/db/run_tests.sh                                   # 29 testes de isolamento
node --experimental-strip-types kansas/backend/tests/unit.test.ts   # 30 testes unitários
python3 kansas/tools/audit_policies.py kansas/db              # auditoria estática
```

Os três rodam no CI a cada push (`.github/workflows/kansas-security.yml`).

## Auditar o app (Fase Zero automática)

```bash
python3 kansas/tools/audit_app.py /caminho/do/app --json auditoria.json
```

Responde sozinho: `applicationId`, `targetSdk`, `versionCode`, signing config,
telas existentes mapeadas para agentes, paddings mágicos e
`StatusBar.currentHeight`, moeda concatenada na mão, `user_id` escolhido pelo
modelo, SQL livre, segredo no repositório, ausência de denúncia de conteúdo de
IA e de exclusão de conta. Sai com código 1 se achar bloqueante.

## Mapa dos arquivos

```
db/001_agent_core.sql      tabelas: threads, mensagens, memória privada,
                           fatos compartilhados, eventos, feedback,
                           exclusão de conta, auditoria
db/002_rls_and_api.sql     RLS das duas fronteiras + API estreita
                           (recall, remember, publish_event, inbox, purge)
db/003_agents_seed.sql     os 6 agentes e suas permissões
db/tests/                  fixtures e a suíte que tenta violar as fronteiras

backend/context.ts         AgentRequestContext — identidade vem do JWT
backend/registry.ts        AgentRegistry — permissão mora aqui, não no prompt
backend/router.ts          escolhe QUEM responde; não ganha acesso a nada
backend/tools/index.ts     catálogo estreito e validado (sem SQL livre)
backend/tools/finance.ts   cálculo determinístico: Money em centavos
backend/blocks.ts          catálogo de blocos; bloco fora dele vira texto
backend/index.ts           Edge Function `kansas-agent`

app/AgentHome.tsx          central de especialistas, colunas por largura
app/AgentScreen.tsx        conversa + blocos + 👍 👎 ⚑ denunciar
app/blocks/                renderizador tipado
app/money.ts               Intl por contexto — nunca "R$ " + valor

tools/audit_app.py         Fase Zero automática
tools/audit_policies.py    impede migration futura reabrir buraco
docs/PLAY-CONSOLE-CHECKLIST.md
```

## Decisões que este núcleo trava de propósito

1. **`applicationId` não muda.** A marca visível vira Kansas IA Financeira; a
   identidade de instalação continua `com.pulsefinanceiro.dreai`, senão a Play
   trata o envio como outro app e os usuários atuais não atualizam.
2. **Nenhum agente é superusuário.** Planejamento recebe *resumos*
   (`get_financial_capacity_summary`), nunca transação bruta nem conversa alheia.
3. **Não existe `queryDatabase(sql)`.** Há teste que falha se alguém criar.
4. **Dinheiro é `{cents, currency}`.** Somar moedas diferentes é exceção, não
   arredondamento. `JPY` não é dividido por 100.
5. **Memória é curada, não é o histórico inteiro.** Cada fato tem origem,
   sensibilidade e validade; o que expira some da leitura sozinho.
6. **O schema `kansas` fica fora dos "Exposed schemas" do Supabase**, então o
   PostgREST não serve essas tabelas ao cliente. O app fala só com a Edge
   Function.

## O que falta para plugar no app (e por que não fiz)

O fonte do app não está em nenhum repositório alcançável por esta sessão — só
`fabiokansas-maker/AUTOMA-O` está. Detalhes e evidência na auditoria, seção 5.

Quando o código chegar, a ordem é: rodar `audit_app.py` → aplicar as migrations
→ implementar `FinanceServices` sobre os repositories que o app **já tem**
(reaproveitamento, não reescrita) → ligar a home nova atrás de feature flag.
