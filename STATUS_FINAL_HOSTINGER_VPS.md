# STATUS_FINAL_HOSTINGER_VPS.md — DEPRECATED (2026-05-22)

Documento obsoleto. A VPS já está em produção com 6 stacks (n8n-mryj, traefik, acha-api, cloud-worker, evolution-atde, openclaw-youtube-learning-api). Não bootstrappar nada novo.

Estratégia atual: `n8n-mryj` é o orquestrador central; workflows AUTOMA-O importados nele via n8nOps MCP (ChatGPT); operação remota via Hostinger MCP + GH Actions runners.

Consulte:
- `CLAUDE.md`
- `infra/diagnostics/runbook.md`
- `infra/n8n/standardization-checklist.md`
- `infra/security/runbook.md`
- `infra/migration/migration-decision-matrix.md`
- `workflows/manifest.json`
