#!/usr/bin/env bash
# Instalador PC-side do sync AUTOMA-O → Obsidian.
# Roda UMA vez no seu PC (Linux ou macOS). No Windows, use install-pc-sync.ps1.
#
# O que faz:
#   1. Pergunta onde está seu vault Obsidian
#   2. Clona este repo em <vault>/Claude/automa-o (read-only, branch claude/download-local-files-5hfmT)
#   3. Cria um job (cron no Linux / launchd no macOS) que faz `git pull` a cada 5 min
#   4. As notas em claude-log/ e snapshots/ aparecem no Obsidian em até 5 min
#
# Uso:
#   bash <(curl -fsSL https://raw.githubusercontent.com/fabiokansas-maker/automa-o/claude/download-local-files-5hfmT/scripts/install-pc-sync.sh)
# ou:
#   git clone -b claude/download-local-files-5hfmT https://github.com/fabiokansas-maker/automa-o.git /tmp/automa-o
#   bash /tmp/automa-o/scripts/install-pc-sync.sh

set -euo pipefail

REPO_URL="https://github.com/fabiokansas-maker/automa-o.git"
BRANCH="claude/download-local-files-5hfmT"
JOB_NAME="automa-o-sync"

echo "==> AUTOMA-O — instalador de sync local"
echo

# 1. Detectar OS
case "$(uname -s)" in
  Linux*)   OS=linux ;;
  Darwin*)  OS=mac ;;
  *)        echo "OS não suportado por este script. Use install-pc-sync.ps1 no Windows." >&2; exit 1 ;;
esac
echo "OS detectado: $OS"

# 2. Pedir o path do vault Obsidian
default_vault="$HOME/Documents/Obsidian"
read -rp "Path do seu vault Obsidian [$default_vault]: " VAULT
VAULT=${VAULT:-$default_vault}
VAULT=$(eval echo "$VAULT")  # expandir ~
if [[ ! -d "$VAULT" ]]; then
  read -rp "Pasta '$VAULT' não existe. Criar? [s/N]: " yn
  case ${yn,,} in s|sim|y|yes) mkdir -p "$VAULT" ;; *) echo "Abortado."; exit 1 ;; esac
fi

TARGET="$VAULT/Claude/automa-o"
mkdir -p "$VAULT/Claude"

# 3. Clone (se já existe, só atualiza remote/branch)
if [[ -d "$TARGET/.git" ]]; then
  echo "Repo já existe em $TARGET — atualizando."
  git -C "$TARGET" remote set-url origin "$REPO_URL"
  git -C "$TARGET" fetch origin "$BRANCH"
  git -C "$TARGET" checkout "$BRANCH"
  git -C "$TARGET" reset --hard "origin/$BRANCH"
else
  echo "Clonando $REPO_URL em $TARGET"
  git clone --branch "$BRANCH" --single-branch "$REPO_URL" "$TARGET"
fi

# 4. Criar uma nota raiz dentro do Obsidian apontando o conteúdo
cat > "$VAULT/Claude/Sobre.md" <<EOF
# Claude — workspace

Este diretório é sincronizado automaticamente do repo \`fabiokansas-maker/automa-o\`
(branch \`$BRANCH\`) a cada 5 minutos via cron/launchd.

## Onde olhar

- **\`automa-o/claude-log/\`** — log do que o Claude está fazendo (uma nota por intervenção)
- **\`automa-o/snapshots/\`** — snapshot diário de métricas (vagas vistas, aplicadas, matches)
- **\`automa-o/workflows/\`** — workflows n8n exportados (importar manualmente no seu n8n)
- **\`automa-o/README.md\`** — visão geral

## Como desligar o sync

\`\`\`bash
$([ "$OS" = "linux" ] && echo "crontab -l | grep -v '$JOB_NAME' | crontab -" || echo "launchctl unload ~/Library/LaunchAgents/$JOB_NAME.plist && rm ~/Library/LaunchAgents/$JOB_NAME.plist")
\`\`\`
EOF

# 5. Setup cron/launchd
SYNC_SCRIPT="$TARGET/scripts/_pull-loop.sh"
cat > "$SYNC_SCRIPT" <<'EOF'
#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
git fetch --quiet origin
git reset --hard --quiet "origin/$(git rev-parse --abbrev-ref HEAD)"
EOF
chmod +x "$SYNC_SCRIPT"

if [[ "$OS" == "linux" ]]; then
  # cron a cada 5 min
  (crontab -l 2>/dev/null | grep -v "$JOB_NAME" || true; \
   echo "*/5 * * * * $SYNC_SCRIPT >/tmp/$JOB_NAME.log 2>&1 # $JOB_NAME") | crontab -
  echo
  echo "✅ Cron instalado. Próxima sync em até 5 min."
  echo "   Pra ver o log: tail -f /tmp/$JOB_NAME.log"
else
  # launchd
  PLIST="$HOME/Library/LaunchAgents/$JOB_NAME.plist"
  mkdir -p "$HOME/Library/LaunchAgents"
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>          <string>$JOB_NAME</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$SYNC_SCRIPT</string>
  </array>
  <key>StartInterval</key>  <integer>300</integer>
  <key>RunAtLoad</key>      <true/>
  <key>StandardOutPath</key><string>/tmp/$JOB_NAME.log</string>
  <key>StandardErrorPath</key><string>/tmp/$JOB_NAME.log</string>
</dict>
</plist>
EOF
  launchctl unload "$PLIST" 2>/dev/null || true
  launchctl load "$PLIST"
  echo
  echo "✅ launchd carregado. Próxima sync em até 5 min."
  echo "   Pra ver o log: tail -f /tmp/$JOB_NAME.log"
fi

# 6. Primeira sync já
"$SYNC_SCRIPT" && echo "✅ Primeira sync ok."

echo
echo "Pronto. Abra o Obsidian e olhe a pasta 'Claude/' do seu vault."
echo "Tudo que eu commitar no GitHub aparece lá em até 5 min."
echo
echo "─────────────────────────────────────────────────────────────"
echo " QUER O BRIDGE BIDIRECIONAL? (Claude lê seu vault e te escreve)"
echo " bash <(curl -fsSL https://raw.githubusercontent.com/fabiokansas-maker/automa-o/$BRANCH/scripts/install-pc-bridge.sh)"
echo "─────────────────────────────────────────────────────────────"
