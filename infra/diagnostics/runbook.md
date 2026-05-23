# Runbook diagnóstico — Hostinger MCP

Sequência determinística que o ChatGPT executa via MCP para preencher `evidence/<YYYY-MM-DD>-diagnostics.md`.

## Pré-requisitos

- Hostinger MCP conectado, vmid=1621330 validado
- n8nOps MCP conectado, router_tests_passed=true
- GitHub MCP conectado ao repo `fabiokansas-maker/AUTOMA-O`

## Sequência

### Bloco A — Hostinger MCP (read-only)

1. `vps.info(vmid=1621330)` → preencher seção 1 do template.
2. `vps.execute(cmd="docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.RunningFor}}'")` → seção 2.
3. `vps.execute(cmd="df -h /")` → seção 3 parte 1.
4. `vps.execute(cmd="du -xhd1 /var/lib/docker 2>/dev/null | sort -h | tail -10")` → seção 3 parte 2.
5. `vps.execute(cmd="docker exec traefik traefik healthcheck 2>&1 || echo 'traefik healthcheck falhou'")` → seção 4 parte 1.
6. `vps.execute(cmd="curl -s http://127.0.0.1:8080/api/http/routers 2>/dev/null | head -200")` → seção 4 parte 2.
7. `vps.execute(cmd="which apache2 nginx; systemctl status apache2 2>/dev/null | head -5; systemctl status nginx 2>/dev/null | head -5")` → seção 6.
8. `vps.execute(cmd="docker --version; docker compose version; docker exec n8n-mryj n8n --version 2>/dev/null; docker exec n8n-mryj-postgres psql --version 2>/dev/null")` → seção 7.
9. `vps.execute(cmd="grep -E '^(PermitRootLogin|PasswordAuthentication|PubkeyAuthentication|Port)' /etc/ssh/sshd_config")` → seção 8.
10. `vps.execute(cmd="crontab -l 2>/dev/null; ls /etc/cron.d/ /etc/cron.daily/ /etc/cron.hourly/")` → seção 9.

### Bloco B — n8nOps MCP

11. `workflows.list(active=true, limit=1000)` → seção 5: count e top 20 nomes.
12. `workflows.list(active=false, limit=1000)` → contagem para diff (305 total vs 161 ativos do registry).

### Bloco C — Padronização

13. `vps.execute(cmd="docker inspect n8n-mryj --format '{{json .Config.Env}}' | jq -r '.[]'")` → checar `DB_TYPE`, `N8N_HOST`, `WEBHOOK_URL`, `GENERIC_TIMEZONE`, `TZ`.
14. `vps.execute(cmd="docker inspect n8n-mryj --format '{{.HostConfig.RestartPolicy.Name}}'")` → confirmar `unless-stopped`.

### Bloco D — Commit via GitHub MCP

15. `create_or_update_file(path="evidence/<data>-diagnostics.md", content=<template preenchido>, branch="claude/download-local-files-5hfmT", message="evidence: diagnóstico inicial VPS")`.

## Critério de sucesso

- Arquivo `evidence/<data>-diagnostics.md` existe com ≥7 seções preenchidas.
- Cada checkbox na seção "checklist de padronização" tem TRUE ou FALSE.
- Cada FALSE vira issue em `infra/n8n/standardization-checklist.md`.

## Sem secret no log

Nenhum comando deste runbook expõe senha, token ou env var sensível. Tudo o que se lê é metadado de runtime ou config de rede.
