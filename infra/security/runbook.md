# Runbook de hardening — VPS Hostinger

Executado pelo ChatGPT via Hostinger MCP `vps.execute`.

## Pré-condições

- F1 (diagnóstico) concluída.
- F3 (backup) concluída — usuário tem backup salvo no Drive ANTES de rodar este runbook.
- Acesso SSH alternativo testado (caso fail2ban bane o IP por engano).

## Sequência

### 1. Upload do script no VPS

```
vps.execute(cmd="mkdir -p /opt/security")
vps.execute(cmd="cat > /opt/security/harden.sh <<'SCRIPT_EOF'\\n<conteúdo do infra/security/harden.sh>\\nSCRIPT_EOF\\nchmod +x /opt/security/harden.sh")
```

OU sincronizar via workflow 12 (doc-sync) estendido para incluir `infra/security/harden.sh`.

### 2. Dry-run

```
vps.execute(cmd="bash -n /opt/security/harden.sh && echo SYNTAX_OK")
```

Esperado: `SYNTAX_OK`.

### 3. Execução

```
vps.execute(cmd="sudo /opt/security/harden.sh 2>&1 | tee /tmp/harden-$(date +%s).log")
```

Capturar últimas 50 linhas em `evidence/<data>-harden.md`.

### 4. Validação imediata

```
vps.execute(cmd="ufw status verbose")
vps.execute(cmd="systemctl is-active fail2ban")
vps.execute(cmd="fail2ban-client status sshd")
vps.execute(cmd="ls -la /etc/traefik/dynamic/")
vps.execute(cmd="docker exec traefik traefik healthcheck")
```

Esperado:
- `ufw` ativo, regras 22/80/443.
- fail2ban ativo, jail `sshd` carregada.
- `/etc/traefik/dynamic/n8n-auth.yml` e `/etc/traefik/dynamic/n8n-htpasswd` existem.

### 5. Entrega da senha

Senha em `/root/.n8n-auth-secret`. Ler UMA VEZ e enviar ao usuário no Telegram (não commitar, não logar no journal):

```
vps.execute(cmd="cat /root/.n8n-auth-secret")
# Pegar conteúdo → enviar via mensagem Telegram normal
# Depois: vps.execute(cmd="echo 'senha lida e enviada — não precisa reler' > /var/log/automao-secret-delivered.log")
```

### 6. Smoke de acesso

```
curl -sI https://srv1621330.hstgr.cloud
# Esperado: 401 Unauthorized

curl -u fabio:<senha> -sI https://srv1621330.hstgr.cloud
# Esperado: 200 OK
```

## Rollback

| Item | Rollback |
|------|----------|
| UFW ativo | `ufw disable` |
| fail2ban rodando | `systemctl stop fail2ban && systemctl disable fail2ban` |
| Traefik basic-auth | `rm /etc/traefik/dynamic/n8n-auth.yml && docker kill --signal=HUP traefik` |
| Senha esquecida | Apagar `/root/.n8n-auth-secret` e rodar `harden.sh` de novo — regenera + envia nova senha pelo Telegram |
| IP banido por engano | Acessar via console Hostinger (browser terminal); `fail2ban-client set sshd unbanip <IP>` |

## Limitação conhecida — Docker bypassa UFW

Containers que expõem portas no compose (`ports: ["X:Y"]`) ficam acessíveis na 0.0.0.0 mesmo com UFW deny. Mitigações aplicáveis caso a caso:

1. Remover bind 0.0.0.0 do `ports:` quando o container deve ser interno → usar redes Docker.
2. Adicionar regras `iptables -I DOCKER-USER` se precisar bloquear porta específica de fora.

Não é necessário pra n8n-mryj porque o acesso público é via Traefik (com basic-auth), não pela porta 5678 direto. Diagnóstico (F1) deve confirmar que 5678 NÃO está bindada em 0.0.0.0.

## Próxima etapa

Após harden OK + smoke OK: F8 (HTTPS + Traefik router + Let's Encrypt). Já com basic-auth no lugar, o roteador HTTPS apenas adiciona TLS.
