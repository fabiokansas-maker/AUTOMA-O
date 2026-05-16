# AUTOMA-O — Auto-aplicação a vagas (Controladoria/FP&A, ABC paulista)

Pipeline completo: coleta multi-plataforma → matching com LLM → cover letter automática → submissão programática → relatório por e-mail. Roda 24/7 no seu VPS.

## Arquitetura

```
                                ┌─ n8n (docker) ──────────────────────────┐
[Conectores HTTP] ◄── chama ────│ 01-coletor (cron 5min)                  │
  /connectors/:source           │ 03-matcher (cron 10min, LLM)            │
  /apply/:source       ◄── chama │ 04-aplicador-auto (cron 15min, LLM)    │
  /applications                 │ 05-email-status (webhook por apply)     │
                                │ 06-reporter (cron diário 9h BRT)        │
                                └─────────────────────────────────────────┘
        ▲                                       │
        │ Playwright via Browserless            ▼
Gupy / RemoteOK / Indeed (API)            Postgres (dedup + analytics)
LinkedIn jobs+posts (scraper)                    │
Vagas / Catho / Glassdoor / Infojobs             ▼
                                          Drive: AUTOMA-O/Snapshots/ + e-mail
```

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `infra/` | docker-compose (Postgres + Browserless + n8n + connectors), schema SQL, env template |
| `connectors/` | API HTTP (Express + Playwright) — 9 plataformas, endpoints `/connectors/:source`, `/apply/:source`, `/applications` |
| `workflows/` | 5 workflows n8n exportados (`01-coletor`, `03-matcher`, `04-aplicador-auto`, `05-email-status`, `06-reporter`) + 2 housekeeping (`07-snapshot-diario`, `08-claude-log-sync`) |
| `prompts/` | Prompts LLM (matcher, cover-letter, linkedin-post-classifier) |
| `obsidian-bridge/` | `perfil.md` + `curriculo.md` (lidos pelo matcher) + templates |
| `snapshots/` | Snapshot diário commitado pelo workflow 07 |
| `scripts/` | Instalador one-liner de sync PC→vault Obsidian |

## Setup no VPS Hostinger (uma vez)

```bash
# 1. Clone
git clone https://github.com/fabiokansas-maker/automa-o.git
cd automa-o/infra

# 2. Configure
cp .env.example .env
nano .env   # preencha: POSTGRES_PASSWORD, BROWSERLESS_TOKEN, CONNECTORS_API_KEY,
            # N8N_ENCRYPTION_KEY, ANTHROPIC_API_KEY, LINKEDIN_LI_AT, NOTIFY_EMAIL_TO

# 3. Suba stack
docker compose up -d
docker compose ps   # 4 containers healthy: postgres, browserless, connectors, n8n

# 4. Abra n8n em http://<vps-ip>:5678
#    - Crie conta admin (primeira vez)
#    - Settings → Credentials:
#       • Postgres "Postgres automao": host=postgres, db=automao, user/pass do .env
#       • Anthropic API: sua key
#       • Google Drive OAuth2: autorize com fabiokansas@gmail.com
#       • Gmail OAuth2: autorize com fabiokansas@gmail.com
#       • GitHub API: PAT com escopo "repo"
#    - Import: Workflows → cada .json em workflows/
#    - Em cada workflow, substitua os "REPLACE_WITH_*_CRED_ID" pelas credenciais criadas

# 5. Bootstrap perfil/CV no Drive
#    - O matcher precisa de perfil.md e curriculo.md no Drive
#    - Já existem em obsidian-bridge/ neste repo; suba pro Drive em AUTOMA-O/
#    - Anote os file IDs e cole nos REPLACE_WITH_PERFIL_FILE_ID / CURRICULO_FILE_ID
#    - Suba também Curriculo_Fabio_Controladoria_0426.pdf → ID em REPLACE_WITH_CV_PDF_FILE_ID

# 6. Active todos os workflows na UI do n8n
```

## Como verificar

```bash
# Connectors API
curl -H "x-api-key: $CONNECTORS_API_KEY" http://localhost:3000/health
curl -H "x-api-key: $CONNECTORS_API_KEY" "http://localhost:3000/connectors/gupy?q=controladoria&limit=5"

# Postgres
docker compose exec postgres psql -U automao -c "SELECT * FROM daily_metrics LIMIT 5;"
docker compose exec postgres psql -U automao -c "SELECT source, last_run_at, last_error FROM sources_health;"

# n8n logs
docker compose logs -f n8n
```

## Decisões de design

- **Modo AUTO sem confirmação humana** — aceitação consciente do risco de ban (LinkedIn/Gupy ToS). Mitigado por: rate-limit 10 apps/dia/plataforma, jitter 800-3500ms entre ações, parar automaticamente quando `sources_health.last_error` indica bloqueio.
- **Postgres compartilhado n8n+app** — um db `automao` (vagas) + db `n8n` (workflows). Reduz infra.
- **Drive como bridge com Obsidian** — perfil/CV ficam em `AUTOMA-O/` no Drive, sincronizam com vault local. Permite editar pelo celular.
- **LLM via API direta (não SDK)** — n8n usa HTTP Request → `api.anthropic.com/v1/messages`. Sem dependência adicional. Fallback OpenAI fácil.
- **Empresas-alvo configuráveis** via `PROFILE_TARGET_COMPANIES` no `.env` — coletor filtra por nome de empresa. Default: Scania, VW, Mercedes, Bombril, Shopee, ML, Magalu, Carrefour, Vivo, Itaú.

## Onde sigo o histórico desta sessão

- **Drive:** `AUTOMA-O/Claude/` — uma nota por sessão do Claude
- **GitHub:** branch `claude/download-local-files-5hfmT`
- **Plano vivo:** sincronizado em `AUTOMA-O/Claude/PLANO-ATIVO.md`

Para continuar pelo celular: abrir [claude.ai/code](https://claude.ai/code), conectar no repo, pedir "continua AUTOMA-O" — a sessão lê o último log do Drive e retoma de onde parou.
