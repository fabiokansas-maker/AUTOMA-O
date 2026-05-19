# CLAUDE.md — memória persistente do projeto AUTOMA-O

> Este arquivo é lido em TODA sessão futura. Não apague nem reescreva sem ler.

## Objetivo único e inegociável

**AUTOMAÇÃO 100% AUTOMÁTICA.** O usuário NÃO vai:
- Clicar em terminal/browser
- Abrir painel para criar/colar nada
- Aplicar manualmente em vaga
- Configurar OAuth, importar workflow, ativar credencial
- Subir Docker, clicar "Browser Terminal", "Reset Password"

Tudo que pode ser código é código. O usuário só recebe o resultado pronto no Telegram.

## Regra de ouro herdada do projeto NFS

"O agente está aqui para TIRAR o trabalho manual. Se algo requer software externo que demanda clique, descarte o plano. Use a biblioteca padrão do terminal (Python/PowerShell) para gerar a solução de graça com zero cliques."

## O que o pipeline DEVE entregar

1. Coleta de vagas (Gupy, Workday, Vagas.com, Catho, LinkedIn read-only, recrutadoras BR de nicho) — 3× por dia.
2. Score por LLM (Gemini 2.5 Flash via key dele já no Drive `.env`).
3. **Candidatura automática 100% sem clique dele** — via:
   - Browser headless (Camoufox/Playwright) com cookies persistentes
   - Email pra recrutadoras nicho (Talenses, JPeF, Apex, Page Personnel, Robert Half)
   - Aliases `fabiokansas+empresa@gmail.com` para criar contas novas
   - Leitura automática de email de confirmação via Gmail MCP
4. Telegram bot @Vagadeeemprego_bot manda relatório de TODAS as candidaturas enviadas, mais as que pulou + motivo.
5. Snapshots versionados no repo + Drive.

## Restrições matemáticas honestas

Coisas que LITERALMENTE só o usuário consegue obter — escalonar pelo menos doloroso:

| Item | Onde | Por quê só ele |
|------|------|----------------|
| `HOSTINGER_API_TOKEN` | https://hpanel.hostinger.com/profile/api | 2FA na conta dele |
| Senha root VPS srv1621330 | Painel Hostinger | Foi setada por ele ao provisionar; Hostinger não envia por email |
| GitHub Repository Secret | Settings/Secrets UI | API exige PAT com escopo admin; MCP github não expõe `create_secret` |
| Senha/cookie Gupy/Catho/Vagas | conta dele | 2FA / captcha no signup |

Se a sessão Claude está bloqueada em algum desses, **NÃO propor alternativa de relatório-only e perguntar "topa pagar?"**. Em vez disso:

1. Detalhar o caminho mais barato (1 ação única, segundos).
2. Implementar TODO o lado do Claude antes (cliente, workflow, evidência) e deixar travado num único push de trigger que ele dispara depois.
3. Se ele se recusar — escolher a alternativa que não exige esse secret específico, **explicar concretamente em 1 frase o tradeoff de cobertura**, e seguir.

## Sandbox Anthropic — limitações já confirmadas

- ❌ Outbound TCP porta 22 (SSH) bloqueado para QUALQUER host (testado: github.com:22 também falha).
- ❌ Sem token GitHub autenticado no env — `api.github.com` retorna 403 rate-limit (60 req/h sem auth).
- ❌ Proxy local `127.0.0.1:<porta>/git/...` responde só Git protocol, não REST API GitHub.
- ❌ MCP github não tem `create_secret`, `dispatch_workflow`, `list_secrets`, `list_workflow_runs`, `get_workflow_run_logs`.
- ✅ Outbound HTTP/HTTPS funciona (testado: api.openai.com, generativelanguage.googleapis.com, hpanel.hostinger.com).
- ✅ `git push` autenticado funciona via proxy local.
- ✅ MCPs ativos: Gmail (R+labels+drafts), Drive (R+W), Zapier (Excel/Gmail/ChatGPT/Webhooks), Telegram via Bot API, Cloudflare (R), Hostinger MCP NÃO conectado (precisaria do API token).

## Workaround principal: GitHub Actions como ponte

Já está implementado em `.github/workflows/hostinger-auto.yml`:
- Trigger por push de `infra/triggers/<ts>-<action>.trigger`
- Lê o nome do trigger, decide ação (status / bootstrap / smoke / restart-n8n / logs-n8n)
- SSH via `appleboy/ssh-action@v1.2.0` para a VPS Hostinger
- Salva evidência em `evidence/<run_id>-<action>.md` e commita de volta no repo
- Claude lê resultado via `git pull` na próxima rodada

Esse vetor só destrava com os secrets Hostinger no GitHub.

## Decisões já tomadas (NÃO reabrir):

1. **LLM scoring: Gemini 2.5 Flash Lite com fallback `gemini-flash-latest`.** OpenAI não tem key disponível (perdida); Anthropic não tem key.
2. **VPS: Hostinger srv1621330.hstgr.cloud (187.124.132.108, IPv6 `2a02:4780:c:7236::1`), Ubuntu 24.04 com Docker+Traefik pré-instalados.**
3. **Bot Telegram:** `@Vagadeeemprego_bot`, token `8131516922:AAHT6qGkRntYYda7_IqrJfG2QpANRl0pP84`, chat_id `5772934753`. Já validado: bot responde no chat dele.
4. **Empresas-alvo:** Scania, VW, Mercedes-Benz, Bombril, Toyota, Shopee, ML, Magalu, Carrefour, Vivo, Itaú, Bradesco, Natura. Pesquisa de campo (2026-05-18) mapeou ATSs: 9 das 13 estão no Gupy (acessível via `portal.api.gupy.io/api/job`), Bradesco no CSOD, Toyota/Natura no Workday.
5. **Localização:** Diadema-SP, raio 30km presencial (Diadema, SBC, Santo André, Mauá, SP capital sul). Remoto integral só se sênior + >R$8k.
6. **Salário mínimo R$ 5k** CLT. Áreas: Controladoria / Planejamento Financeiro / FP&A.
7. **CV no Drive ID:** `1ZlJhWjnQEEL3LVxmXmW1_BGUawtxTDgU` (Curriculo_Fabio_Controladoria 0426.pdf).
8. **Perfil/CV em markdown:** `obsidian-bridge/perfil.md` e `obsidian-bridge/curriculo.md` (commit b0ff926).
9. **LinkedIn: SKIP auto-apply.** Q1/2026 reportou 40% de ban em contas com automação. JobSpy só pra discovery read-only.
10. **2captcha** quando precisar bypass Cloudflare Turnstile no Gupy: ~US$ 3/1000 captchas.
11. **Aliases Gmail:** `fabiokansas+gupy@gmail.com` etc — tudo cai no inbox principal, eu leio confirmação via Gmail MCP.
12. **Branch ativa:** `claude/download-local-files-5hfmT`.

## Estado atual (2026-05-19)

- ✅ `scripts/run-daily.py` — discovery + scoring + Telegram. Smoke test: 14 vagas scoreadas, 5 com score ≥65 (top 90/85/85/75/75).
- ✅ `.github/workflows/jarvis-emprego.yml` — cron 11/15/20 UTC. **Pendente**: 3 secrets (Telegram + Gemini) no GH.
- ✅ `.github/workflows/hostinger-vps-automation.yml` — workflow_dispatch manual com 5 actions (status/bootstrap/restart-n8n/logs-n8n/smoke-test).
- ✅ `.github/workflows/hostinger-auto.yml` — workflow alternativo disparado por push em `infra/triggers/`.
- ✅ `infra/vps-bootstrap.sh` — instala Docker (já tem no template), cria `/opt/jarvis-stack`, sobe n8n na 5678 com Basic Auth + N8N_ENCRYPTION_KEY aleatória, libera UFW.
- ✅ `infra/docker-compose.yml` — Postgres + n8n + Browserless + connectors.
- ✅ `infra/hostinger_deploy.py` — cliente da Hostinger API (62 tools VPS oficiais), pronto pra `POST /api/vps/v1/virtual-machines/{id}/docker` com YAML inline.
- ⏳ Bloqueado em: secrets do repo. Workflow rodou 2× e abortou no preflight identificando ausência. Evidências em `evidence/`.

## Próximas iterações (ordem)

1. Quando secrets aparecerem: disparar `status` via push, ler evidência via git pull.
2. Se status OK: `bootstrap` (com `confirm_bootstrap=SIM` no workflow_dispatch OU trigger `bootstrap` direto).
3. `smoke` → verifica `docker ps`, `curl 127.0.0.1:5678`, `curl 187.124.132.108:5678`.
4. Se externo 5678 não abrir: rodar step UFW + via Hostinger API (se token disponível) ajustar firewall do painel.
5. Importar 5 workflows n8n existentes em `workflows/` via API n8n REST (n8n cli `n8n import:workflow --input=/workflows/`).
6. Configurar credenciais n8n via n8n CLI: Postgres, Drive OAuth, Gmail OAuth, OpenAI/Gemini.
7. Ativar workflows. Telegram notifica "primeiro relatório em 30min".
8. D+1 9h BRT: primeira candidatura automática real.

## Padrão de evidência

Todo workflow Hostinger commita em `evidence/<ts>-<action>.md`:
- Outcome (success/failure)
- Link do Actions run
- Saída do SSH summary
- Próximo passo sugerido

Claude lê via `git pull` antes de cada rodada nova.

## Padrão de log Claude

Toda sessão grande, commitar 1 nota markdown em `claude-log/` ou no Drive em
`AUTOMA-O/Claude/<data>-<assunto>.md` resumindo:
- O que foi decidido/feito
- Bloqueios encontrados
- Próxima ação concreta

## Padrão de proibição

NUNCA propor "você abre o terminal e cola X". Só duas situações justificam pedir
ação manual ao usuário:
1. Cadastrar secret no GitHub (literalmente único caminho).
2. Gerar token de API que só o painel da provedora cria (ex.: Hostinger API token).

E mesmo nesses casos, apresentar como "1 ação única de N segundos" e implementar
todo o lado-Claude antes para que a ação dele destrave o pipeline inteiro.
