# Hostinger Projects Status

Data: 2026-05-23
Fonte: Hostinger MCP + Access Registry v4
Secrets expostos: não

## VPS

| Campo | Valor |
|---|---|
| Host | `srv1621330.hstgr.cloud` |
| virtualMachineId | 1621330 |
| Estado | running |
| Plano | KVM 1 |
| Template | Ubuntu 24.04 with Docker and Traefik |

## Projetos Docker

| Projeto | Status | Observação |
|---|---|---|
| acha-api | running | API |
| cloud-worker | running | Hotmart cloud worker |
| evolution-atde | running | Evolution API |
| n8n-mryj | running | n8n principal (305 workflows, 161 ativos) |
| openclaw-youtube-learning-api | running | OpenClaw YouTube learning |
| traefik | running | Reverse proxy / HTTPS |

## Serviços remotos (rodando 100% na VPS, sem depender do PC)

| Serviço | Runs on | PC off | Health |
|---|---|---:|---|
| n8n | hostinger_vps | True | passed |
| Traefik | hostinger_vps | True | passed |
| vpsOps | hostinger_vps | True | passed |
| API Ops | hostinger_vps | True | passed |
| n8nOps | hostinger_vps | True | passed |
| freelaOps | hostinger_vps | True | passed |
| hotmartOps | hostinger_vps | True | passed |
| Jarvis bridge | hostinger_vps | True | passed |
| Hotmart cloud worker | hostinger_vps | True | passed |
| OpenClaw YouTube learning | hostinger_vps | True | passed |
| API Gateway | hostinger_vps | True | passed |
| Obsidian writer | hostinger_vps | True | passed |

## Healthchecks

- n8nOps: `router_tests_passed=true`, `total=305`, `active=161`
- FreelaOps: `freela_growth_leads_top5` → `ok=true`, `external_actions_sent=false`
- Watchdog disco: `vps-disk-watchdog-v1` / `ewY4AswdZOP90dfj` / ativo a cada 6h
- Limpeza destrutiva executada: não

## Alertas conhecidos

- Gmail registrou alertas Hostinger de uso de disco/quota do VPS — monitorar.
- Aviso de update crítico do n8n recebido por e-mail — avaliar janela de upgrade.

## Próximas ações

- Revalidar HTTPS via Traefik e reverse SSH (autostart).
- Confirmar `API_AUTH_TOKEN` apenas em env/secret store do container.
- Manter `/ops reiniciar` somente com `allow_restart=true` e serviço allowlisted.
- Não publicar Hotmart sem `allow_publish` e credencial validada.

## Regra de segurança

Este documento registra apenas nomes lógicos, status e localização. Nenhum valor real de token, senha, cookie, API key ou chave SSH é gravado aqui.
