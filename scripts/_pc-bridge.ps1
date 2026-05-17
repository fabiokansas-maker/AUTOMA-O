# Loop do bridge - chamado a cada 5min pelo Task Scheduler.
# Faz: push vault -> Drive, pull Inbox -> vault, heartbeat -> Drive.

$ErrorActionPreference = 'Continue'

$ConfigDir = Join-Path $HOME '.automa-o'
. (Join-Path $ConfigDir 'bridge.env.ps1')   # define $VAULT, $RCLONE_REMOTE, $DRIVE_ROOT, $EXCLUDE_FILE, $LOG_FILE

function Log($msg) {
  $ts = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
  $line = "[$ts] $msg"
  Add-Content -Path $LOG_FILE -Value $line
}

Log 'bridge tick start'

# 1. Push vault -> Drive
if (Test-Path $VAULT) {
  rclone copy $VAULT "${RCLONE_REMOTE}:${DRIVE_ROOT}/Vault-Mirror" `
    --exclude-from $EXCLUDE_FILE `
    --transfers 4 --checkers 8 --fast-list --quiet
  if ($LASTEXITCODE -ne 0) { Log 'push falhou (nao-fatal)' } else { Log 'push ok' }
} else {
  Log "vault path not found: $VAULT (skip push)"
}

# 2. Pull Inbox: Drive -> vault
$inbox = Join-Path $VAULT 'Claude\Inbox'
New-Item -ItemType Directory -Force -Path $inbox | Out-Null
rclone copy "${RCLONE_REMOTE}:${DRIVE_ROOT}/Inbox" $inbox --transfers 4 --quiet
if ($LASTEXITCODE -ne 0) { Log 'inbox pull falhou (nao-fatal)' } else { Log 'inbox pull ok' }

# 3. Heartbeat
$heartbeatLocal = Join-Path $env:TEMP 'automa-o-heartbeat.json'
$vaultSize = 0
if (Test-Path $VAULT) {
  $vaultSize = (Get-ChildItem $VAULT -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
  if (-not $vaultSize) { $vaultSize = 0 }
}
$lastCommit = 'unknown'
$gitDir = Join-Path $VAULT 'Claude\automa-o\.git'
if (Test-Path $gitDir) {
  try {
    $lastCommit = (git -C (Split-Path $gitDir) rev-parse --short HEAD).Trim()
  } catch { $lastCommit = 'unknown' }
}
$ts = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
$payload = @{
  timestamp        = $ts
  hostname         = $env:COMPUTERNAME
  os               = "$([System.Environment]::OSVersion.Platform) $([System.Environment]::OSVersion.Version)"
  vault_path       = $VAULT
  vault_size_bytes = $vaultSize
  last_git_commit  = $lastCommit
  bridge_version   = '0.1.0'
} | ConvertTo-Json -Compress
Set-Content -Path $heartbeatLocal -Value $payload -Encoding UTF8

rclone copyto $heartbeatLocal "${RCLONE_REMOTE}:${DRIVE_ROOT}/Bridge/last-heartbeat.json" --quiet
if ($LASTEXITCODE -ne 0) { Log 'heartbeat falhou (nao-fatal)' } else { Log 'heartbeat ok' }

Log 'bridge tick end'
