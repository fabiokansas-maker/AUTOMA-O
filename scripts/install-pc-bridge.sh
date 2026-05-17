#!/usr/bin/env bash
# AUTOMA-O PC Bridge — Linux/macOS installer
# Instalador one-shot do bridge bidirecional vault ↔ Drive.
#
# Uso:
#   bash <(curl -fsSL https://raw.githubusercontent.com/fabiokansas-maker/automa-o/claude/download-local-files-5hfmT/scripts/install-pc-bridge.sh)

set -euo pipefail

REPO_URL="https://github.com/fabiokansas-maker/automa-o.git"
BRANCH="claude/download-local-files-5hfmT"
JOB_NAME="automa-o-bridge"
RCLONE_REMOTE="automao-drive"
DRIVE_ROOT="AUTOMA-O"

c_blue()  { printf "\033[1;34m%s\033[0m\n" "$*"; }
c_green() { printf "\033[1;32m%s\033[0m\n" "$*"; }
c_yellow(){ printf "\033[1;33m%s\033[0m\n" "$*"; }
c_red()   { printf "\033[1;31m%s\033[0m\n" "$*" >&2; }

c_blue "==> AUTOMA-O PC Bridge — instalador (Linux/macOS)"
echo

# 1. Detectar OS
case "$(uname -s)" in
  Linux*)   OS=linux ;;
  Darwin*)  OS=mac ;;
  *) c_red "OS não suportado. Use install-pc-bridge.ps1 no Windows."; exit 1 ;;
esac
echo "OS detectado: $OS"

# 2. Instalar rclone se não tiver
if ! command -v rclone >/dev/null 2>&1; then
  c_yellow "rclone não encontrado. Instalando..."
  if [[ "$OS" == "mac" ]]; then
    if command -v brew >/dev/null 2>&1; then
      brew install rclone
    else
      curl -fsSL https://rclone.org/install.sh | sudo bash
    fi
  else
    if command -v apt-get >/dev/null 2>&1; then
      sudo apt-get update && sudo apt-get install -y rclone
    elif command -v dnf >/dev/null 2>&1; then
      sudo dnf install -y rclone
    elif command -v pacman >/dev/null 2>&1; then
      sudo pacman -S --noconfirm rclone
    else
      curl -fsSL https://rclone.org/install.sh | sudo bash
    fi
  fi
fi
c_green "✓ rclone $(rclone version | head -1 | awk '{print $2}')"

# 3. Path do vault
default_vault="$HOME/Documents/Obsidian"
read -rp "Path do seu vault Obsidian [$default_vault]: " VAULT
VAULT=${VAULT:-$default_vault}
VAULT=$(eval echo "$VAULT")
if [[ ! -d "$VAULT" ]]; then
  read -rp "Pasta '$VAULT' não existe. Criar? [s/N]: " yn
  case "${yn:-n}" in s|sim|y|yes|S|Y) mkdir -p "$VAULT" ;; *) c_red "Abortado."; exit 1 ;; esac
fi
c_green "✓ Vault: $VAULT"

# 4. Setup rclone remote (OAuth interativo se necessário)
if ! rclone listremotes 2>/dev/null | grep -q "^${RCLONE_REMOTE}:$"; then
  c_yellow "Configurando rclone remote '$RCLONE_REMOTE'..."
  echo "Vai abrir o browser pra você autorizar acesso ao Drive. Clica em 'Permitir'."
  rclone config create "$RCLONE_REMOTE" drive scope=drive config_is_local=true || {
    c_red "Falha no OAuth. Tenta de novo manualmente: rclone config"
    exit 1
  }
fi
c_green "✓ rclone remote '$RCLONE_REMOTE' configurado"

# 5. Garante pastas no Drive (idempotente)
for sub in Vault-Mirror Inbox Bridge; do
  rclone mkdir "${RCLONE_REMOTE}:${DRIVE_ROOT}/${sub}" 2>/dev/null || true
done
c_green "✓ Pastas no Drive: ${DRIVE_ROOT}/{Vault-Mirror,Inbox,Bridge}"

# 6. Pasta local do Inbox dentro do vault
mkdir -p "$VAULT/Claude/Inbox"
c_green "✓ Pasta local: $VAULT/Claude/Inbox"

# 7. Copia o exclude file e o loop script pra ~/.automa-o
CONFIG_DIR="$HOME/.automa-o"
mkdir -p "$CONFIG_DIR"

# Baixa os arquivos atuais do repo
curl -fsSL "https://raw.githubusercontent.com/fabiokansas-maker/automa-o/${BRANCH}/bridge/.rclone-exclude" \
  -o "$CONFIG_DIR/rclone-exclude"
curl -fsSL "https://raw.githubusercontent.com/fabiokansas-maker/automa-o/${BRANCH}/scripts/_pc-bridge.sh" \
  -o "$CONFIG_DIR/bridge.sh"
chmod +x "$CONFIG_DIR/bridge.sh"

# Config do bridge (vault path, etc)
cat > "$CONFIG_DIR/bridge.env" <<EOF
VAULT="$VAULT"
RCLONE_REMOTE="$RCLONE_REMOTE"
DRIVE_ROOT="$DRIVE_ROOT"
EXCLUDE_FILE="$CONFIG_DIR/rclone-exclude"
LOG_FILE="$CONFIG_DIR/bridge.log"
EOF
c_green "✓ Config: $CONFIG_DIR/bridge.env"

# 8. Agenda execução a cada 5min
if [[ "$OS" == "linux" ]]; then
  (crontab -l 2>/dev/null | grep -v "$JOB_NAME" || true; \
   echo "*/5 * * * * $CONFIG_DIR/bridge.sh >>$CONFIG_DIR/bridge.log 2>&1 # $JOB_NAME") | crontab -
  c_green "✓ Cron agendado a cada 5min"
else
  PLIST="$HOME/Library/LaunchAgents/${JOB_NAME}.plist"
  mkdir -p "$HOME/Library/LaunchAgents"
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>${JOB_NAME}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${CONFIG_DIR}/bridge.sh</string>
  </array>
  <key>StartInterval</key><integer>300</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>${CONFIG_DIR}/bridge.log</string>
  <key>StandardErrorPath</key><string>${CONFIG_DIR}/bridge.log</string>
</dict>
</plist>
EOF
  launchctl unload "$PLIST" 2>/dev/null || true
  launchctl load "$PLIST"
  c_green "✓ launchd carregado (5min interval)"
fi

# 9. Primeira execução
c_yellow "Rodando primeira sync (pode demorar uns segundos pra subir o vault inteiro)..."
"$CONFIG_DIR/bridge.sh" || c_red "Primeira execução falhou — confere o log em $CONFIG_DIR/bridge.log"

echo
c_green "✅ Bridge instalado e rodando."
echo
echo "Logs:   tail -f $CONFIG_DIR/bridge.log"
echo "Status: rclone ls ${RCLONE_REMOTE}:${DRIVE_ROOT}/Bridge/"
echo
echo "Daqui em diante, sempre que seu PC estiver ligado, o Claude vê seu vault"
echo "no Drive e pode te escrever em $VAULT/Claude/Inbox/"
