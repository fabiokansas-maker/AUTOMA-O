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

## Estado atual (2026-05-19 23:00 BRT)

### Infra HOJE no VPS Hostinger srv1621330 (Ubuntu 24.04, Docker+Traefik pré-instalados)

VPS está **RUNNING** com 6 stacks já em produção (mapeadas pelo ChatGPT via Hostinger MCP em `2026-05-19 22:40`):

| Stack | Função | Status |
|-------|--------|--------|
| **n8n-mryj** | n8n core — 305 workflows total, 161 ativos | running |
| traefik | Reverse proxy TLS | running (503 sem rota pública pra `*.hstgr.cloud`) |
| acha-api | API própria do user | running |
| cloud-worker | worker de cloud | running |
| evolution-atde | Evolution API (WhatsApp) | running |
| openclaw-youtube-learning-api | OpenClaw bots / YouTube | running |

### Quem tem qual MCP

| MCP | ChatGPT (Cursor) | Claude (esta sessão) |
|-----|:----------------:|:--------------------:|
| Hostinger | ✅ vmid=1621330 validado | ❌ não conectado |
| n8nOps | ✅ router test passou | ❌ não carregado |
| Gmail | ✅ | ✅ |
| Drive | ✅ | ✅ |
| Zapier | ✅ | ✅ |
| GitHub | ✅ | ✅ |
| FreelaOps | ✅ | ❌ |
| OpenClaw | ✅ parcial | ❌ |
| vpsOps (próprio) | ✅ criado local em `C:\Users\fabio\Downloads\access-registry-vpsops\` | ❌ não publicado |
| ops_api_gateway | ✅ criado local | ❌ não publicado |

**Implicação prática**: pra alterar workflows n8n, eu (Claude) **não tenho `N8N_BASE_URL` nem `N8N_API_KEY`** no env. O ChatGPT tem. Pra eu importar o pipeline AUTOMA-O no n8n existente, ou:
- (a) ChatGPT importa via n8nOps MCP (vai no PC dele), ou
- (b) o user me passa `N8N_BASE_URL` + `N8N_API_KEY` (mas registry registra esses valores em variável env só, sem expor)

### Artefatos do ChatGPT (locais no PC do user, fora do repo AUTOMA-O)

Pasta-base: `C:\Users\fabio\Downloads\access-registry-vpsops\`

- `secure_access_registry.json` + `.md` — 16 serviços, sem secrets em texto
- `vps_ops_mcp_server.py` — 11 tools (healthcheck, docker ps/logs, traefik, n8n, mcps, restart seguro, obsidian report). URL planejada `http://127.0.0.1:8794/mcp` local / `/aiops/vpsops/mcp` remoto.
- `ops_api_gateway.py` — endpoints `/api/ops/health|services|n8n|mcps|jarvis|traefik|restart-safe`, autenticado por `API_AUTH_TOKEN`. Testes locais: health/services OK, restart sem `allow_restart` bloqueado 403.
- `JARVIS_OPS_COMMANDS_SPEC.md` — spec dos comandos `/ops` para o Telegram bot Jarvis. Patch no workflow ainda não aplicado.
- `CHATGPT_ACCESS_REQUIREMENTS.md` — checklist do que ChatGPT pode usar.
- `deploy/systemd/`, `deploy/traefik/` — snippets prontos.

Estado dos testes locais:
- `validate_no_secrets`: True (sem secret em texto plano)
- `GET /api/ops/health`: True
- `GET /api/ops/services`: count=16
- `POST /api/ops/restart-safe` sem `allow_restart`: bloqueado 403

### Docs no Drive (lidos por mim, links de referência)

- Status v2: https://docs.google.com/document/d/1TfALMev-7BxyOYDEEKCScvRn9wm02wOmiEx2ZitUnuE
- Registry v2: https://docs.google.com/document/d/1GxeJ0W58RemjwLsgFL1v5uzceQX_-NWxsy6gJ1-9xZI

### Pendências reais (em ordem de prioridade)

1. **Disco da VPS** com alerta Hostinger de quota — ChatGPT vê via Hostinger MCP. Eu posso ajudar via script `infra/hostinger_deploy.py` se token vier por env.
2. **Publicar `vpsOps` + `ops_api_gateway` na VPS** — depende de SSH/admin validado sem expor segredo. ChatGPT pode disparar via Hostinger MCP `vps.execute()` ou similar. Eu não, sem token.
3. **`API_AUTH_TOKEN` remoto seguro** fora de Markdown — gerar via `openssl rand -hex 32`, armazenar em env seguro (não no repo).
4. **Aplicar comandos `/ops` no workflow Jarvis (n8n)** com backup antes — patch via n8nOps (ChatGPT) ou n8n REST API (se eu tiver URL+key).
5. Importar workflows do AUTOMA-O (`workflows/01-coletor.json` ... `06-reporter.json`) no n8n-mryj — depende de URL+key n8n.
6. Cron 3×/dia do `scripts/run-daily.py` no GitHub Actions (já pronto, falta os 3 secrets simples: Telegram + Gemini).

### Pipeline AUTOMA-O do meu lado (Claude) — pronto para integrar

- `scripts/run-daily.py` — discovery Gupy + Natura Workday + scoring Gemini + Telegram. Smoke: 14 vagas, 5 com score ≥65. Funciona standalone.
- `.github/workflows/jarvis-emprego.yml` — cron 8h/12h/17h BRT. Pendente: 3 secrets simples.
- `.github/workflows/hostinger-auto.yml` — trigger via push de `infra/triggers/*.trigger`, salva evidência commitada em `evidence/`. **Não dependerá mais de SSH direto se rodar comandos via Hostinger MCP/n8nOps que o ChatGPT já tem.**

**Decisão arquitetural**: como o n8n já existe na VPS com 305 workflows, NÃO subir novo n8n próprio. Reaproveitar o `n8n-mryj` importando os 5 workflows do projeto AUTOMA-O nele.


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

---

## Plano migração PC → VPS (2026-05-22) — 8 fases

Estratégia central: `n8n-mryj` é o ORQUESTRADOR. Tudo que era ia ser cron Linux
agora é workflow n8n. Claude commita código; ChatGPT executa no VPS via Hostinger
MCP + n8nOps MCP. Detalhes em `infra/diagnostics/runbook.md`,
`infra/n8n/standardization-checklist.md`, `infra/security/runbook.md`,
`infra/migration/migration-decision-matrix.md`.

Workflows infra adicionados ao manifest (`workflows/manifest.json`):
- `09-backup-daily.json` — cron 03h00, Postgres+vol+/opt → /opt/backups + Drive
- `10-healthcheck-5min.json` — 7 serviços, Telegram com rate-limit 30min
- `11-disk-watch.json` — Hostinger API, alerta ≥80%, prune ≥90%
- `12-doc-sync.json` — README+CLAUDE do repo → /opt/

Limpeza F0 aplicada:
- `infra/docker-compose.yml` → `infra/docker-compose.connectors.yml` (sem service n8n)
- `infra/vps-bootstrap.sh` → `infra/_archive/`
- `.github/workflows/hostinger-vps-automation.yml` → `.github/workflows/_archive/`
- `hostinger-auto.yml` perdeu o step `bootstrap`

O que falta o usuário fazer (gates externos):
1. Cadastrar GH Secrets: `HOSTINGER_API_TOKEN`, `TELEGRAM_BOT_TOKEN`,
   `TELEGRAM_CHAT_ID`, `GEMINI_API_KEY` (UI única vez).
2. ChatGPT executa F1 (diagnóstico) e commita `evidence/<data>-diagnostics.md`.
3. Confirmar no Telegram a lista de scripts do PC aprovados (F5).
