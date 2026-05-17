#!/usr/bin/env bash
# Loop do bridge: chamado a cada 5min pelo cron/launchd.
# Faz: push vault → Drive, pull Inbox → vault, heartbeat → Drive.

set -euo pipefail

# Carrega config (VAULT, RCLONE_REMOTE, DRIVE_ROOT, EXCLUDE_FILE, LOG_FILE)
CONFIG_DIR="$HOME/.automa-o"
# shellcheck disable=SC1091
source "$CONFIG_DIR/bridge.env"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
log() { echo "[$(ts)] $*"; }

log "bridge tick start"

# 1. Push vault → Drive (one-way, vault é source-of-truth)
if [[ -d "$VAULT" ]]; then
  rclone copy "$VAULT" "${RCLONE_REMOTE}:${DRIVE_ROOT}/Vault-Mirror" \
    --exclude-from "$EXCLUDE_FILE" \
    --transfers 4 \
    --checkers 8 \
    --fast-list \
    --quiet || log "push falhou (não-fatal)"
  log "push ok"
else
  log "vault path not found: $VAULT (skip push)"
fi

# 2. Pull Inbox: Drive → vault
mkdir -p "$VAULT/Claude/Inbox"
rclone copy "${RCLONE_REMOTE}:${DRIVE_ROOT}/Inbox" "$VAULT/Claude/Inbox" \
  --transfers 4 \
  --quiet || log "inbox pull falhou (não-fatal)"
log "inbox pull ok"

# 3. Heartbeat: timestamp + hostname + tamanho do vault
HEARTBEAT_FILE="/tmp/automa-o-heartbeat.json"
VAULT_SIZE=$(du -sb "$VAULT" 2>/dev/null | awk '{print $1}' || echo 0)
LAST_COMMIT="unknown"
if [[ -d "$VAULT/Claude/automa-o/.git" ]]; then
  LAST_COMMIT=$(git -C "$VAULT/Claude/automa-o" rev-parse --short HEAD 2>/dev/null || echo "unknown")
fi
cat > "$HEARTBEAT_FILE" <<EOF
{
  "timestamp": "$(ts)",
  "hostname": "$(hostname)",
  "os": "$(uname -s) $(uname -r)",
  "vault_path": "$VAULT",
  "vault_size_bytes": $VAULT_SIZE,
  "last_git_commit": "$LAST_COMMIT",
  "bridge_version": "0.1.0"
}
EOF
rclone copyto "$HEARTBEAT_FILE" "${RCLONE_REMOTE}:${DRIVE_ROOT}/Bridge/last-heartbeat.json" \
  --quiet || log "heartbeat falhou (não-fatal)"
log "heartbeat ok"

log "bridge tick end"
