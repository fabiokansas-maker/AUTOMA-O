# Diagnóstico VPS Hostinger srv1621330 — &lt;YYYY-MM-DD&gt;

Template preenchido pelo ChatGPT via Hostinger MCP. Salvar como `evidence/<YYYY-MM-DD>-diagnostics.md` e commitar.

## 1. vm.info

```
id:        1621330
hostname:  srv1621330.hstgr.cloud
state:    
plan:     
disk_gb:  
ram_gb:   
vcpu:     
ipv4:     
ipv6:     
```

## 2. docker ps

```
NAME           STATUS    PORTS    UPTIME
```

(saída de `docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.RunningFor}}'`)

## 3. Disco

```
df -h /
```

Top 10 maiores em `/var/lib/docker`:
```
du -xhd1 /var/lib/docker 2>/dev/null | sort -h | tail -10
```

## 4. Traefik

```
docker exec traefik traefik healthcheck
```

Rotas registradas:
```
curl -s http://127.0.0.1:8080/api/http/routers | jq '.[] | {name, rule, service, status}'
```

## 5. n8n-mryj — workflows

Via n8nOps MCP:
- count total: 
- count ativos: 
- top 20 nomes (ativos): 

## 6. Apache / Nginx (briefing pede explicitamente)

```
which apache2 nginx
systemctl status apache2 2>/dev/null | head -5
systemctl status nginx 2>/dev/null | head -5
```

## 7. Versões

```
docker --version
docker compose version
docker exec n8n-mryj n8n --version
docker exec n8n-mryj-postgres psql --version
```

## 8. SSH config (read-only)

```
grep -E '^(PermitRootLogin|PasswordAuthentication|PubkeyAuthentication|Port)' /etc/ssh/sshd_config
```

## 9. Cron existente

```
crontab -l 2>/dev/null
ls /etc/cron.d/ /etc/cron.daily/ /etc/cron.hourly/
```

---

## Checklist de padronização n8n-mryj (preencher TRUE/FALSE)

- [ ] `DB_TYPE=postgresdb` (não SQLite)
- [ ] `restart=unless-stopped`
- [ ] `N8N_HOST` setado
- [ ] `WEBHOOK_URL` setado
- [ ] `GENERIC_TIMEZONE=America/Sao_Paulo`
- [ ] `TZ=America/Sao_Paulo`

Para checar, ChatGPT roda:
```
docker inspect n8n-mryj --format '{{json .Config.Env}}' | jq -r '.[]'
docker inspect n8n-mryj --format '{{.HostConfig.RestartPolicy.Name}}'
```

Cada FALSE vira issue na Fase 2 (`infra/n8n/standardization-checklist.md`).
