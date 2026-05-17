# PC Bridge — vault Obsidian ↔ Claude (via Drive)

Bridge bidirecional entre seu vault Obsidian local e o Drive. Quando o PC está ligado, o Claude consegue ler o que está no vault e te escrever de volta. Quando o PC está desligado, nada quebra — o Claude só vê o último estado sincronizado.

## Como funciona

```
USER PC (quando ligado)                          CLOUD (Drive)
┌──────────────────────────────┐                 ┌────────────────────────────┐
│ <vault>/                     │ → rclone push → │ AUTOMA-O/Vault-Mirror/     │
│   (vault inteiro,            │   a cada 5min   │   espelho read-only        │
│    menos secrets/.env/etc)   │                 │                            │
│                              │                 │ AUTOMA-O/Inbox/            │
│ <vault>/Claude/Inbox/  ←─────│ ← rclone pull ← │   Claude escreve aqui      │
│   (Claude posta msgs aqui)   │   a cada 5min   │                            │
│                              │ → heartbeat →   │ AUTOMA-O/Bridge/           │
│                              │   a cada 5min   │   last-heartbeat.json      │
└──────────────────────────────┘                 └────────────────────────────┘
```

## Instalação (uma vez)

### Linux/macOS

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/fabiokansas-maker/automa-o/claude/download-local-files-5hfmT/scripts/install-pc-bridge.sh)
```

### Windows (PowerShell)

```powershell
irm https://raw.githubusercontent.com/fabiokansas-maker/automa-o/claude/download-local-files-5hfmT/scripts/install-pc-bridge.ps1 | iex
```

O instalador:
1. Instala `rclone` se não tiver (apt/brew/winget ou download direto)
2. Pergunta path do vault Obsidian (default `~/Documents/Obsidian`)
3. Abre browser pra você autorizar acesso ao Drive (OAuth, **uma vez**)
4. Cria as pastas no Drive: `AUTOMA-O/Vault-Mirror/`, `AUTOMA-O/Inbox/`, `AUTOMA-O/Bridge/`
5. Agenda execução a cada 5min (cron / launchd / Task Scheduler)
6. Roda primeira execução pra você ver funcionando

## O que NÃO é sincronizado

`.rclone-exclude` define o que fica só no PC e nunca sobe pro Drive:

- `.git/` (repos clonados)
- `.obsidian/workspace*`, `.obsidian/cache` (estado UI do Obsidian)
- `.trash/`
- `secrets/`, `.env`, `.env.*`, `*.key`, `*.pem`

Quer ajustar? Edita `bridge/.rclone-exclude` no PC depois do install.

## Verificação

```bash
# Logs do bridge
tail -f ~/.automa-o/bridge.log

# Status no Drive (qualquer browser/celular)
# https://drive.google.com/drive/folders/<AUTOMA-O folder ID>
# Confere: Vault-Mirror/ tem o conteúdo do vault, Bridge/last-heartbeat.json
# tem timestamp recente.
```

## Como Claude usa o bridge

- **Lê seu vault:** via Drive MCP, busca em `Vault-Mirror/*`
- **Escreve pra você:** posta `.md` em `Inbox/`, aparece no vault em até 5min em `<vault>/Claude/Inbox/`
- **Sabe se o PC tá online:** lê `Bridge/last-heartbeat.json` e checa o timestamp

## Desligar

### Linux
```bash
crontab -l | grep -v automa-o-bridge | crontab -
```

### macOS
```bash
launchctl unload ~/Library/LaunchAgents/automa-o-bridge.plist
rm ~/Library/LaunchAgents/automa-o-bridge.plist
```

### Windows
```powershell
Unregister-ScheduledTask -TaskName AutomaOBridge -Confirm:$false
```

Pra deletar o token do rclone:
```bash
rclone config delete automao-drive   # Linux/macOS
```
```powershell
rclone config delete automao-drive   # Windows
```

## Privacidade

- O token OAuth do rclone fica em `~/.config/rclone/rclone.conf` (Linux/Mac) ou `%APPDATA%\rclone\rclone.conf` (Win). Não vai pro Git.
- O rclone tem permissão de Drive completa (limitação dele), mas o bridge só toca em `AUTOMA-O/*`. Se quiser scope estrito, gere uma service account scoped ao folder e troque a config (avançado).
- O Claude (sessão cloud) só lê `Vault-Mirror/` e escreve em `Inbox/`. Nunca toca em `Vault-Mirror/` no Drive (read-only do lado dele).
