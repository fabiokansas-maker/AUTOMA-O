# AUTOMA-O PC Bridge — Windows installer
# Uso (PowerShell, não precisa admin):
#   irm https://raw.githubusercontent.com/fabiokansas-maker/automa-o/claude/download-local-files-5hfmT/scripts/install-pc-bridge.ps1 | iex

$ErrorActionPreference = 'Stop'

$Branch       = 'claude/download-local-files-5hfmT'
$TaskName     = 'AutomaOBridge'
$RcloneRemote = 'automao-drive'
$DriveRoot    = 'AUTOMA-O'

Write-Host '==> AUTOMA-O PC Bridge - instalador (Windows)' -ForegroundColor Cyan
Write-Host ''

# 1. Instalar rclone se nao tiver
if (-not (Get-Command rclone -ErrorAction SilentlyContinue)) {
  Write-Host 'rclone nao encontrado. Instalando via winget...' -ForegroundColor Yellow
  if (Get-Command winget -ErrorAction SilentlyContinue) {
    winget install -e --id Rclone.Rclone --silent --accept-package-agreements --accept-source-agreements
    # Atualiza PATH na sessao atual
    $env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path','User')
  } else {
    Write-Error 'winget nao disponivel. Instala rclone manualmente: https://rclone.org/downloads/'
    exit 1
  }
}
$rcloneVer = (rclone version | Select-Object -First 1)
Write-Host "OK rclone: $rcloneVer" -ForegroundColor Green

# 2. Path do vault
$defaultVault = Join-Path $HOME 'Documents\Obsidian'
$vault = Read-Host "Path do seu vault Obsidian [$defaultVault]"
if ([string]::IsNullOrWhiteSpace($vault)) { $vault = $defaultVault }
if (-not (Test-Path $vault)) {
  $yn = Read-Host "Pasta '$vault' nao existe. Criar? [s/N]"
  if ($yn -match '^[sSyY]') { New-Item -ItemType Directory -Force -Path $vault | Out-Null }
  else { Write-Error 'Abortado.'; exit 1 }
}
Write-Host "OK Vault: $vault" -ForegroundColor Green

# 3. Setup rclone remote (OAuth)
$remotes = (rclone listremotes) -split "`n"
if (-not ($remotes -contains "${RcloneRemote}:")) {
  Write-Host "Configurando rclone remote '$RcloneRemote'..." -ForegroundColor Yellow
  Write-Host "Vai abrir o browser. Clica em 'Permitir' pro Drive." -ForegroundColor Yellow
  rclone config create $RcloneRemote drive scope=drive config_is_local=true
}
Write-Host "OK rclone remote '$RcloneRemote' configurado" -ForegroundColor Green

# 4. Pastas no Drive (idempotente)
foreach ($sub in @('Vault-Mirror','Inbox','Bridge')) {
  rclone mkdir "${RcloneRemote}:${DriveRoot}/${sub}" 2>$null
}
Write-Host "OK Pastas no Drive: ${DriveRoot}/{Vault-Mirror,Inbox,Bridge}" -ForegroundColor Green

# 5. Pasta local Inbox
$inboxLocal = Join-Path $vault 'Claude\Inbox'
New-Item -ItemType Directory -Force -Path $inboxLocal | Out-Null
Write-Host "OK Pasta local: $inboxLocal" -ForegroundColor Green

# 6. Config dir e download dos arquivos auxiliares
$ConfigDir = Join-Path $HOME '.automa-o'
New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null

$excludeUrl = "https://raw.githubusercontent.com/fabiokansas-maker/automa-o/$Branch/bridge/.rclone-exclude"
$bridgeUrl  = "https://raw.githubusercontent.com/fabiokansas-maker/automa-o/$Branch/scripts/_pc-bridge.ps1"
$excludePath = Join-Path $ConfigDir 'rclone-exclude'
$bridgePath  = Join-Path $ConfigDir 'bridge.ps1'

Invoke-WebRequest -Uri $excludeUrl -OutFile $excludePath -UseBasicParsing
Invoke-WebRequest -Uri $bridgeUrl  -OutFile $bridgePath  -UseBasicParsing

# Env file lido pelo bridge.ps1
$envContent = @"
`$VAULT='$vault'
`$RCLONE_REMOTE='$RcloneRemote'
`$DRIVE_ROOT='$DriveRoot'
`$EXCLUDE_FILE='$excludePath'
`$LOG_FILE='$($ConfigDir + '\bridge.log')'
"@
Set-Content -Path (Join-Path $ConfigDir 'bridge.env.ps1') -Value $envContent -Encoding UTF8
Write-Host "OK Config: $ConfigDir" -ForegroundColor Green

# 7. Scheduled Task a cada 5min
$action   = New-ScheduledTaskAction -Execute 'powershell.exe' `
              -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$bridgePath`""
$trigger  = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
              -RepetitionInterval (New-TimeSpan -Minutes 5)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd `
              -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings | Out-Null
Write-Host 'OK Task Scheduler agendado a cada 5min' -ForegroundColor Green

# 8. Primeira execucao
Write-Host 'Rodando primeira sync...' -ForegroundColor Yellow
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $bridgePath

Write-Host ''
Write-Host 'OK Bridge instalado e rodando.' -ForegroundColor Green
Write-Host ''
Write-Host "Logs:   Get-Content -Tail 50 -Wait $ConfigDir\bridge.log"
Write-Host "Status: rclone ls ${RcloneRemote}:${DriveRoot}/Bridge/"
Write-Host ''
Write-Host 'Daqui em diante, sempre que seu PC estiver ligado, o Claude ve seu vault'
Write-Host "no Drive e pode te escrever em $vault\Claude\Inbox\"
