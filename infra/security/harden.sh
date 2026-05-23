#!/usr/bin/env bash
# infra/security/harden.sh
# Idempotente. Executado pelo ChatGPT via Hostinger MCP `vps.execute`.
# Não toca em itens que já estão OK. Cada bloco loga decisão em /var/log/automao-harden.log.

set -Eeuo pipefail

LOG=/var/log/automao-harden.log
mkdir -p "$(dirname "$LOG")"
exec > >(tee -a "$LOG") 2>&1

echo "===== $(date -u +%FT%TZ) automao-harden start ====="

# ----- 1. UFW -----
if ! command -v ufw >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y ufw
fi

if ! ufw status | grep -q "Status: active"; then
  echo "[ufw] inactive — configurando default deny incoming + 22/80/443 allow"
  ufw default deny incoming
  ufw default allow outgoing
  ufw allow 22/tcp
  ufw allow 80/tcp
  ufw allow 443/tcp
  ufw --force enable
else
  echo "[ufw] já ativo — checando regras"
  for port in 22 80 443; do
    ufw status | grep -E "^${port}/tcp\\s+ALLOW" >/dev/null || ufw allow ${port}/tcp
  done
fi
ufw status verbose | head -20

# ----- 2. fail2ban -----
if ! command -v fail2ban-client >/dev/null 2>&1; then
  apt-get install -y fail2ban
fi

JAIL=/etc/fail2ban/jail.local
if [ ! -f "$JAIL" ]; then
  cat > "$JAIL" <<'EOF'
[DEFAULT]
bantime  = 1h
findtime = 10m
maxretry = 5
backend  = systemd

[sshd]
enabled = true
port    = ssh
filter  = sshd
logpath = %(sshd_log)s

[recidive]
enabled  = true
filter   = recidive
logpath  = /var/log/fail2ban.log
bantime  = 1w
findtime = 1d
maxretry = 3
EOF
fi

systemctl enable --now fail2ban
fail2ban-client status sshd 2>&1 | head -10 || true

# ----- 3. sshd_config — read-only check, sem brick -----
if grep -qE '^\s*PasswordAuthentication\s+yes' /etc/ssh/sshd_config; then
  echo "[ssh] WARN: PasswordAuthentication=yes. Não desativando automaticamente p/ evitar brick. Configure chave SSH e revise manualmente."
fi
if grep -qE '^\s*PermitRootLogin\s+yes' /etc/ssh/sshd_config; then
  echo "[ssh] WARN: PermitRootLogin=yes. Considere mudar para 'prohibit-password' após confirmar acesso por chave."
fi

# ----- 4. Traefik basic-auth no n8n-mryj -----
TRAEFIK_DYN=/etc/traefik/dynamic
SECRET_FILE=/root/.n8n-auth-secret
HTPASSWD_FILE="$TRAEFIK_DYN/n8n-htpasswd"
AUTH_YAML="$TRAEFIK_DYN/n8n-auth.yml"

mkdir -p "$TRAEFIK_DYN"

if [ ! -f "$SECRET_FILE" ]; then
  echo "[traefik] gerando senha basic-auth"
  PASS=$(openssl rand -base64 24 | tr -d '/+=' | head -c 28)
  USER=fabio
  # htpasswd via openssl (sem precisar apache2-utils)
  HASH=$(openssl passwd -apr1 "$PASS")
  echo "${USER}:${HASH}" > "$HTPASSWD_FILE"
  chmod 600 "$HTPASSWD_FILE"
  printf 'user: %s\npassword: %s\n' "$USER" "$PASS" > "$SECRET_FILE"
  chmod 600 "$SECRET_FILE"
  echo "[traefik] senha gravada em $SECRET_FILE — enviar UMA vez ao usuário via Telegram (separado)"
else
  echo "[traefik] $SECRET_FILE já existe — mantendo senha atual"
fi

cat > "$AUTH_YAML" <<EOF
http:
  middlewares:
    n8n-auth:
      basicAuth:
        usersFile: $HTPASSWD_FILE
        realm: "n8n-mryj"
EOF

# Reload Traefik (se containerizado, restart suave do container)
if docker ps --format '{{.Names}}' | grep -q '^traefik$'; then
  docker kill --signal=HUP traefik 2>/dev/null || docker restart traefik
fi

# ----- 5. Docker bypassa UFW — documentar -----
if iptables -L DOCKER-USER -n 2>/dev/null | head -1 >/dev/null; then
  echo "[docker-ufw] DOCKER-USER chain existe — UFW NÃO bloqueia portas expostas por containers. Documentado em CLAUDE.md."
fi

echo "===== $(date -u +%FT%TZ) automao-harden end ====="
