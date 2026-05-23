#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/jarvis-stack}"
TZ_VALUE="${TZ_VALUE:-America/Sao_Paulo}"
N8N_PORT="${N8N_PORT:-5678}"
N8N_HOST_VALUE="${N8N_HOST_VALUE:-0.0.0.0}"
N8N_PROTOCOL_VALUE="${N8N_PROTOCOL_VALUE:-http}"
WEBHOOK_URL_VALUE="${WEBHOOK_URL_VALUE:-}"

log() { printf '\n[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
need_root() {
  if [ "$(id -u)" -ne 0 ]; then
    echo "ERRO: rode como root ou via sudo." >&2
    exit 1
  fi
}
install_docker() {
  if command -v docker >/dev/null 2>&1; then
    log "Docker ja instalado: $(docker --version)"
  else
    log "Instalando Docker"
    apt-get update -y
    apt-get install -y ca-certificates curl gnupg lsb-release ufw jq git
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    . /etc/os-release
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" > /etc/apt/sources.list.d/docker.list
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    systemctl enable --now docker
  fi
}
write_env() {
  mkdir -p "$APP_DIR/n8n_data" "$APP_DIR/logs"
  chmod 700 "$APP_DIR/n8n_data"
  if [ ! -f "$APP_DIR/.env" ]; then
    log "Criando .env inicial"
    local enc_key
    enc_key="$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')"
    cat > "$APP_DIR/.env" <<ENVEOF
TZ=${TZ_VALUE}
N8N_PORT=${N8N_PORT}
N8N_HOST=${N8N_HOST_VALUE}
N8N_PROTOCOL=${N8N_PROTOCOL_VALUE}
WEBHOOK_URL=${WEBHOOK_URL_VALUE}
N8N_ENCRYPTION_KEY=${enc_key}
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=${N8N_BASIC_AUTH_USER:-fabio}
N8N_BASIC_AUTH_PASSWORD=${N8N_BASIC_AUTH_PASSWORD:-troque-essa-senha-agora}
ENVEOF
    chmod 600 "$APP_DIR/.env"
  else
    log ".env ja existe; nao vou sobrescrever secrets"
  fi
}
write_compose() {
  log "Gravando docker-compose.yml"
  cat > "$APP_DIR/docker-compose.yml" <<'YAMLEOF'
services:
  n8n:
    image: n8nio/n8n:latest
    container_name: n8n
    restart: unless-stopped
    ports:
      - "${N8N_PORT:-5678}:5678"
    environment:
      - TZ=${TZ:-America/Sao_Paulo}
      - N8N_HOST=${N8N_HOST:-0.0.0.0}
      - N8N_PORT=5678
      - N8N_PROTOCOL=${N8N_PROTOCOL:-http}
      - WEBHOOK_URL=${WEBHOOK_URL:-}
      - N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
      - N8N_BASIC_AUTH_ACTIVE=${N8N_BASIC_AUTH_ACTIVE:-true}
      - N8N_BASIC_AUTH_USER=${N8N_BASIC_AUTH_USER:-fabio}
      - N8N_BASIC_AUTH_PASSWORD=${N8N_BASIC_AUTH_PASSWORD}
    volumes:
      - ./n8n_data:/home/node/.n8n
YAMLEOF
}
firewall() {
  if command -v ufw >/dev/null 2>&1; then
    log "Configurando UFW: 22, 80, 443, ${N8N_PORT}"
    ufw allow 22/tcp || true
    ufw allow 80/tcp || true
    ufw allow 443/tcp || true
    ufw allow "${N8N_PORT}/tcp" || true
    ufw --force enable || true
  fi
}
up_services() {
  log "Subindo containers"
  cd "$APP_DIR"
  docker compose pull
  docker compose up -d
}
status() {
  log "STATUS DOCKER"
  docker --version || true
  docker compose version || true
  docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' || true
  log "TESTE LOCAL N8N"
  curl -I "http://127.0.0.1:${N8N_PORT}" || true
}
main() {
  need_root
  export DEBIAN_FRONTEND=noninteractive
  install_docker
  write_env
  write_compose
  firewall
  up_services
  status
  log "BOOTSTRAP FINALIZADO. Se estiver usando IP direto, teste: http://187.124.132.108:${N8N_PORT}"
  log "IMPORTANTE: troque N8N_BASIC_AUTH_PASSWORD em ${APP_DIR}/.env e rode: cd ${APP_DIR} && docker compose up -d"
}
main "$@"
