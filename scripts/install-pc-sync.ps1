# Instalador PC-side do sync AUTOMA-O -> Obsidian (Windows).
# Rode UMA vez no PowerShell (não precisa admin).
#
# Uso:
#   irm https://raw.githubusercontent.com/fabiokansas-maker/automa-o/claude/download-local-files-5hfmT/scripts/install-pc-sync.ps1 | iex
# ou:
#   git clone -b claude/download-local-files-5hfmT https://github.com/fabiokansas-maker/automa-o.git $env:TEMP\automa-o
#   & $env:TEMP\automa-o\scripts\install-pc-sync.ps1

$ErrorActionPreference = 'Stop'

$RepoUrl  = 'https://github.com/fabiokansas-maker/automa-o.git'
$Branch   = 'claude/download-local-files-5hfmT'
$TaskName = 'AutomaOSync'

Write-Host "==> AUTOMA-O - instalador de sync local (Windows)" -ForegroundColor Cyan
Write-Host ""

# Conferir git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  Write-Error "Git não encontrado. Instale: https://git-scm.com/download/win"
  exit 1
}

# Pedir vault
$defaultVault = Join-Path $HOME 'Documents\Obsidian'
$vault = Read-Host "Path do seu vault Obsidian [$defaultVault]"
if ([string]::IsNullOrWhiteSpace($vault)) { $vault = $defaultVault }
if (-not (Test-Path $vault)) {
  $yn = Read-Host "Pasta '$vault' não existe. Criar? [s/N]"
  if ($yn -match '^[sSyY]') { New-Item -ItemType Directory -Force -Path $vault | Out-Null }
  else { Write-Host "Abortado."; exit 1 }
}

$target = Join-Path $vault 'Claude\automa-o'
New-Item -ItemType Directory -Force -Path (Join-Path $vault 'Claude') | Out-Null

# Clone ou atualiza
if (Test-Path (Join-Path $target '.git')) {
  Write-Host "Repo já existe — atualizando."
  git -C $target remote set-url origin $RepoUrl
  git -C $target fetch origin $Branch
  git -C $target checkout $Branch
  git -C $target reset --hard "origin/$Branch"
} else {
  Write-Host "Clonando $RepoUrl em $target"
  git clone --branch $Branch --single-branch $RepoUrl $target
}

# Nota raiz
$aboutPath = Join-Path $vault 'Claude\Sobre.md'
@"
# Claude — workspace

Este diretório é sincronizado automaticamente do repo ``fabiokansas-maker/automa-o``
(branch ``$Branch``) a cada 5 minutos via Task Scheduler.

## Onde olhar

- **``automa-o/claude-log/``** — log do que o Claude está fazendo
- **``automa-o/snapshots/``** — snapshots diários de métricas
- **``automa-o/workflows/``** — workflows n8n
- **``automa-o/README.md``** — visão geral

## Desligar o sync

``Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false``
"@ | Set-Content -Path $aboutPath -Encoding UTF8

# Script de pull
$pullScript = Join-Path $target 'scripts\_pull-loop.ps1'
@"
`$ErrorActionPreference = 'Stop'
Set-Location '$target'
git fetch --quiet origin
git reset --hard --quiet "origin/$Branch"
"@ | Set-Content -Path $pullScript -Encoding UTF8

# Scheduled Task a cada 5 min
$action    = New-ScheduledTaskAction -Execute 'powershell.exe' `
              -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$pullScript`""
$trigger   = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
              -RepetitionInterval (New-TimeSpan -Minutes 5)
$settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd `
              -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings | Out-Null

# Primeira sync
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $pullScript

Write-Host ""
Write-Host "OK Task Scheduler configurado: $TaskName" -ForegroundColor Green
Write-Host "   Sincroniza a cada 5 min. Abra o Obsidian -> pasta 'Claude/'."
Write-Host ''
Write-Host '─────────────────────────────────────────────────────────────'
Write-Host ' QUER O BRIDGE BIDIRECIONAL? (Claude le seu vault e te escreve)'
Write-Host "  irm https://raw.githubusercontent.com/fabiokansas-maker/automa-o/$Branch/scripts/install-pc-bridge.ps1 | iex"
Write-Host '─────────────────────────────────────────────────────────────'
