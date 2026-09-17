<#
.SYNOPSIS
  Tira o app do PC e coloca o build na nuvem. Roda UMA vez.

.DESCRIPTION
  Depois disto, atualizar o app na Play não depende mais desta máquina:

    1. acha sozinho o fonte do app (procura o build.gradle com o applicationId)
    2. lê os fatos: targetSdk, versionCode, applicationId, config de assinatura
    3. monta uma CÓPIA LIMPA (sem node_modules, build, keystore, .env) —
       história antiga não vai junto, então segredo antigo não vaza
    4. cria um repositório PRIVADO e sobe essa cópia
    5. grava as secrets de assinatura pelo gh (nunca imprime, nunca commita)
    6. instala os workflows de release e de vigia no repositório novo
    7. avisa no Telegram que terminou

  Nada aqui publica nada na Play. O envio continua sendo um passo explícito.

.EXAMPLE
  # ensaio: mostra tudo que faria, sem tocar em nada
  pwsh -File bootstrap-app-to-cloud.ps1 -DryRun

.EXAMPLE
  pwsh -File bootstrap-app-to-cloud.ps1
#>
[CmdletBinding()]
param(
  [string] $AppPath  = "",
  [string] $Repo     = "kansas-app",
  [string] $Owner    = "",
  [string] $Package  = "com.pulsefinanceiro.dreai",
  [string] $SourceRepoRaw =
    "https://raw.githubusercontent.com/fabiokansas-maker/AUTOMA-O/claude/kansas-agent-first-rebuild-ptcc1w",
  [switch] $DryRun,
  [string] $TelegramToken = $env:TELEGRAM_BOT_TOKEN,
  [string] $TelegramChat  = $env:TELEGRAM_CHAT_ID
)

$ErrorActionPreference = 'Stop'
$script:Passos = [System.Collections.Generic.List[string]]::new()

function Log([string]$m, [string]$cor = 'Gray') {
  Write-Host $m -ForegroundColor $cor
  $script:Passos.Add($m)
}
function Falhar([string]$m) { Log "ERRO: $m" 'Red'; throw $m }

# ---------------------------------------------------------------- descoberta
function Find-AppSource {
  param([string]$Package)

  $raizes = @(
    'C:\Dev', 'D:\Dev',
    (Join-Path $HOME 'Downloads'), (Join-Path $HOME 'Documents'),
    (Join-Path $HOME 'source'), (Join-Path $HOME 'Projects'), $HOME
  ) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -Unique

  foreach ($raiz in $raizes) {
    Log "procurando em $raiz ..."
    $candidatos = Get-ChildItem -Path $raiz -Recurse -Filter 'build.gradle*' `
                    -File -Depth 6 -ErrorAction SilentlyContinue |
                  Where-Object { $_.FullName -notmatch '[\\/](node_modules|build|\.gradle)[\\/]' }
    foreach ($g in $candidatos) {
      $txt = Get-Content -Raw -LiteralPath $g.FullName -ErrorAction SilentlyContinue
      if ($txt -and $txt -match [regex]::Escape($Package)) {
        # .../android/app/build.gradle  ->  raiz do projeto RN
        $proj = Split-Path (Split-Path (Split-Path $g.FullName -Parent) -Parent) -Parent
        if (Test-Path (Join-Path $proj 'package.json')) { return $proj }
        return (Split-Path (Split-Path $g.FullName -Parent) -Parent)
      }
    }
  }
  return $null
}

function Read-GradleFacts {
  param([string]$AppPath)

  $fatos = @{}
  $gradles = Get-ChildItem -Path $AppPath -Recurse -Filter 'build.gradle*' -File `
               -Depth 4 -ErrorAction SilentlyContinue |
             Where-Object { $_.FullName -notmatch '[\\/]node_modules[\\/]' }

  $mapa = @{
    applicationId = 'applicationId\s*=?\s*["'']([\w.]+)["'']'
    targetSdk     = 'targetSdk(?:Version)?\s*=?\s*(\d+)'
    compileSdk    = 'compileSdk(?:Version)?\s*=?\s*(\d+)'
    minSdk        = 'minSdk(?:Version)?\s*=?\s*(\d+)'
    versionCode   = 'versionCode\s*=?\s*(\d+)'
    versionName   = 'versionName\s*=?\s*["'']([^"'']+)["'']'
    storeFile     = 'storeFile\s+file\(["'']?([^"'')]+)'
    keyAlias      = 'keyAlias\s+["'']?([^"''\s]+)'
  }
  foreach ($g in $gradles) {
    $txt = Get-Content -Raw -LiteralPath $g.FullName
    foreach ($k in $mapa.Keys) {
      if (-not $fatos.ContainsKey($k)) {
        $m = [regex]::Match($txt, $mapa[$k])
        if ($m.Success) { $fatos[$k] = $m.Groups[1].Value }
      }
    }
  }
  return $fatos
}

function Read-SigningProps {
  param([string]$AppPath)

  $props = @{}
  $arquivos = @(
    (Join-Path $AppPath 'gradle.properties'),
    (Join-Path $AppPath 'android/gradle.properties'),
    (Join-Path $HOME '.gradle/gradle.properties')
  ) | Where-Object { Test-Path $_ }

  foreach ($f in $arquivos) {
    foreach ($linha in Get-Content -LiteralPath $f) {
      if ($linha -match '^\s*([A-Za-z0-9_.]+)\s*=\s*(.+?)\s*$') {
        $props[$Matches[1]] = $Matches[2]
      }
    }
  }
  return $props
}

function Find-Keystore {
  param([string]$AppPath, [hashtable]$Fatos, [hashtable]$Props)

  $pistas = @()
  if ($Fatos.storeFile)  { $pistas += $Fatos.storeFile }
  foreach ($k in $Props.Keys) {
    if ($k -match 'STORE_FILE|KEYSTORE_FILE') { $pistas += $Props[$k] }
  }
  foreach ($p in $pistas) {
    foreach ($base in @((Join-Path $AppPath 'android/app'), (Join-Path $AppPath 'android'), $AppPath)) {
      $cheio = Join-Path $base $p
      if (Test-Path -LiteralPath $cheio) { return (Resolve-Path $cheio).Path }
    }
    if (Test-Path -LiteralPath $p) { return (Resolve-Path $p).Path }
  }
  $achado = Get-ChildItem -Path $AppPath -Recurse -Include '*.keystore', '*.jks' -File `
              -Depth 5 -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -notmatch 'debug' } | Select-Object -First 1
  if ($achado) { return $achado.FullName }
  return $null
}

# ------------------------------------------------------------------- cópia
$Excluidos = @(
  'node_modules', 'build', '.gradle', '.git', 'Pods', 'DerivedData',
  '.expo', 'dist', 'coverage', '.idea', '__pycache__'
)
$ExcluidosArquivo = @('*.keystore', '*.jks', '*.jks.bak', '.env', '.env.*',
                      'local.properties', '*.pem', '*.p12', '*.log')

function New-CleanCopy {
  param([string]$AppPath, [string]$Destino)

  if (Test-Path $Destino) { Remove-Item -Recurse -Force $Destino }
  New-Item -ItemType Directory -Force -Path $Destino | Out-Null

  $raiz = (Resolve-Path $AppPath).Path.TrimEnd('\', '/')
  $copiados = 0
  Get-ChildItem -Path $raiz -Recurse -File -Force -ErrorAction SilentlyContinue | ForEach-Object {
    $rel = $_.FullName.Substring($raiz.Length).TrimStart('\', '/')
    $partes = $rel -split '[\\/]'
    if ($partes | Where-Object { $Excluidos -contains $_ }) { return }
    foreach ($pad in $ExcluidosArquivo) { if ($_.Name -like $pad) { return } }

    $alvo = Join-Path $Destino $rel
    $pasta = Split-Path $alvo -Parent
    if (-not (Test-Path $pasta)) { New-Item -ItemType Directory -Force -Path $pasta | Out-Null }

    if ($_.Name -eq 'gradle.properties') {
      # gradle.properties costuma guardar senha de keystore em texto puro.
      # A cópia vai sem essas linhas: no CI elas entram como secret.
      $limpas = Get-Content -LiteralPath $_.FullName | Where-Object {
        $_ -notmatch '(?i)(PASSWORD|SECRET|TOKEN|API[_-]?KEY|STORE_FILE)\s*='
      }
      $tiradas = (Get-Content -LiteralPath $_.FullName).Count - $limpas.Count
      Set-Content -Path $alvo -Value $limpas -Encoding UTF8
      if ($tiradas -gt 0) { Log "sanitizado $rel ($tiradas linha(s) de segredo removida(s))" 'Yellow' }
    } else {
      Copy-Item -LiteralPath $_.FullName -Destination $alvo -Force
    }
    $script:copiados = $copiados++
  }
  return (Get-ChildItem -Path $Destino -Recurse -File).Count
}

function Write-Gitignore {
  param([string]$Destino)
  $conteudo = @'
# gerado pelo bootstrap do Kansas — o que nunca deve subir
node_modules/
build/
.gradle/
.expo/
dist/
coverage/
Pods/
*.keystore
*.jks
*.pem
*.p12
.env
.env.*
local.properties
*.log
'@
  Set-Content -Path (Join-Path $Destino '.gitignore') -Value $conteudo -Encoding UTF8
}

function Get-Workflows {
  param([string]$Destino, [string]$Base, [switch]$DryRun)
  $pasta = Join-Path $Destino '.github/workflows'
  New-Item -ItemType Directory -Force -Path $pasta | Out-Null
  $pasta2 = Join-Path $Destino 'kansas/tools'
  New-Item -ItemType Directory -Force -Path $pasta2 | Out-Null

  $arquivos = @{
    '.github/workflows/kansas-release.yml' = "$Base/.github/workflows/kansas-release.yml"
    '.github/workflows/kansas-watch.yml'   = "$Base/.github/workflows/kansas-watch.yml"
    'kansas/tools/audit_app.py'            = "$Base/kansas/tools/audit_app.py"
    'kansas/tools/play_status.py'          = "$Base/kansas/tools/play_status.py"
    'kansas/tools/play_watch.py'           = "$Base/kansas/tools/play_watch.py"
  }
  foreach ($rel in $arquivos.Keys) {
    $alvo = Join-Path $Destino $rel
    $pai = Split-Path $alvo -Parent
    if (-not (Test-Path $pai)) { New-Item -ItemType Directory -Force -Path $pai | Out-Null }
    if ($DryRun) { Log "[ensaio] baixaria $rel"; continue }
    Invoke-WebRequest -Uri $arquivos[$rel] -OutFile $alvo -UseBasicParsing
    Log "instalado $rel"
  }
}


function Assert-NoSecrets {
  param([string]$Destino)

  # Padrões que NUNCA podem sair desta máquina dentro de um commit.
  $graves = @(
    @{ re = '-----BEGIN [A-Z ]*PRIVATE KEY-----'; nome = 'chave privada' },
    @{ re = '(?i)(password|senha)\s*[:=]\s*\S{4,}';  nome = 'senha em texto' },
    @{ re = 'sk-[A-Za-z0-9]{20,}';                 nome = 'chave de API estilo OpenAI' },
    @{ re = '(?i)service_account.*private_key';    nome = 'service account do Google' }
  )
  $achados = @()
  Get-ChildItem -Path $Destino -Recurse -File -Force | ForEach-Object {
    if ($_.Length -gt 2MB) { return }
    if ($_.Extension -in @('.png', '.jpg', '.jpeg', '.webp', '.ttf', '.otf', '.aab', '.apk')) { return }
    $txt = Get-Content -Raw -LiteralPath $_.FullName -ErrorAction SilentlyContinue
    if (-not $txt) { return }
    foreach ($g in $graves) {
      if ($txt -match $g.re) {
        $achados += "$($_.FullName.Substring($Destino.Length).TrimStart('\','/')): $($g.nome)"
      }
    }
  }
  return $achados
}

# ------------------------------------------------------------------ ferramentas
function Ensure-Tool {
  param([string]$Nome, [string]$WingetId)
  if (Get-Command $Nome -ErrorAction SilentlyContinue) { Log "$Nome ok"; return $true }
  if (-not $IsWindows) { Log "$Nome ausente (fora do Windows, não instalo)" 'Yellow'; return $false }
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Log "$Nome ausente e sem winget" 'Yellow'; return $false
  }
  Log "instalando $Nome via winget ..." 'Yellow'
  winget install -e --id $WingetId --silent --accept-package-agreements --accept-source-agreements | Out-Null
  $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
              [Environment]::GetEnvironmentVariable('Path', 'User')
  return [bool](Get-Command $Nome -ErrorAction SilentlyContinue)
}

function Send-Telegram {
  param([string]$Texto)
  if (-not $TelegramToken -or -not $TelegramChat) { return }
  try {
    Invoke-RestMethod -Method Post -Uri "https://api.telegram.org/bot$TelegramToken/sendMessage" `
      -Body @{ chat_id = $TelegramChat; text = $Texto } | Out-Null
    Log 'aviso enviado no Telegram'
  } catch { Log "não consegui avisar no Telegram: $($_.Exception.Message)" 'Yellow' }
}

# =========================================================== execução
Log '=== bootstrap do app para a nuvem ===' 'Cyan'
if ($DryRun) { Log '(ENSAIO: nada será criado, enviado ou alterado)' 'Yellow' }

if (-not $AppPath) {
  Log "procurando o fonte de $Package ..."
  $AppPath = Find-AppSource -Package $Package
}
if (-not $AppPath -or -not (Test-Path $AppPath)) {
  Falhar "não achei o fonte de $Package. Rode com -AppPath C:\caminho\do\projeto"
}
$AppPath = (Resolve-Path $AppPath).Path
Log "fonte: $AppPath" 'Green'

$fatos = Read-GradleFacts -AppPath $AppPath
$props = Read-SigningProps -AppPath $AppPath
Log "applicationId: $($fatos.applicationId)"
Log "targetSdk: $($fatos.targetSdk)  compileSdk: $($fatos.compileSdk)  minSdk: $($fatos.minSdk)"
Log "versionCode: $($fatos.versionCode)  versionName: $($fatos.versionName)"

if ($fatos.applicationId -and $fatos.applicationId -ne $Package) {
  Falhar "applicationId '$($fatos.applicationId)' != '$Package'. Confirme o projeto certo."
}
$alvo = 0
[void][int]::TryParse("$($fatos.targetSdk)", [ref]$alvo)
if ($alvo -lt 36) {
  Log "ATENÇÃO: targetSdk=$($fatos.targetSdk) — a Play recusa atualização abaixo de 36." 'Yellow'
  Log 'O fonte sobe de qualquer forma; o workflow de release barra o envio até corrigir.' 'Yellow'
}

$keystore = Find-Keystore -AppPath $AppPath -Fatos $fatos -Props $props
if ($keystore) { Log "keystore encontrada: $(Split-Path $keystore -Leaf)" 'Green' }
else { Log 'keystore NÃO encontrada — release ficará bloqueado até ela existir' 'Yellow' }

$stage = Join-Path ([IO.Path]::GetTempPath()) 'kansas-app-stage'
Log "montando cópia limpa em $stage ..."
$n = New-CleanCopy -AppPath $AppPath -Destino $stage
Write-Gitignore -Destino $stage
Log "$n arquivo(s) na cópia (sem node_modules, build, keystore, .env)" 'Green'
Get-Workflows -Destino $stage -Base $SourceRepoRaw -DryRun:$DryRun

$vazamentos = Assert-NoSecrets -Destino $stage
if ($vazamentos.Count -gt 0) {
  Log 'PAREI: a cópia ainda contém segredo. Nada foi enviado.' 'Red'
  $vazamentos | ForEach-Object { Log "  - $_" 'Red' }
  Falhar 'remova/mova esses arquivos e rode de novo'
}
Log 'varredura de segredos na cópia: limpa' 'Green'

$temGit = Ensure-Tool -Nome 'git' -WingetId 'Git.Git'
$temGh  = Ensure-Tool -Nome 'gh'  -WingetId 'GitHub.cli'

if ($DryRun) {
  Log '[ensaio] criaria o repositório privado, subiria a cópia e gravaria as secrets'
  Log "[ensaio] secrets: ANDROID_KEYSTORE_BASE64$(if($props.Count){', senhas do gradle.properties'})"
  $relatorio = Join-Path ([IO.Path]::GetTempPath()) 'kansas-bootstrap-ensaio.json'
  @{ fonte = $AppPath; fatos = $fatos; keystore = $keystore; arquivos = $n;
     passos = $script:Passos } | ConvertTo-Json -Depth 5 |
    Set-Content -Path $relatorio -Encoding UTF8
  Log "relatório do ensaio: $relatorio" 'Cyan'
  return
}

if (-not $temGit -or -not $temGh) { Falhar 'preciso de git e gh instalados' }

# login do gh (uma vez; se já estiver logado, não pede nada)
& gh auth status 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
  Log 'abrindo o login do GitHub no navegador (uma vez só) ...' 'Yellow'
  & gh auth login --web --git-protocol https --scopes 'repo,workflow'
  if ($LASTEXITCODE -ne 0) { Falhar 'login do GitHub não concluído' }
}
if (-not $Owner) { $Owner = (& gh api user --jq .login).Trim() }
$destinoRepo = "$Owner/$Repo"
Log "repositório destino: $destinoRepo (privado)"

Push-Location $stage
try {
  & git init -q
  & git checkout -q -b main
  & git add -A
  & git -c user.name='kansas-bootstrap' -c user.email='noreply@anthropic.com' `
        commit -q -m "fonte do app $Package (cópia limpa, sem história antiga)"

  & gh repo view $destinoRepo 2>$null | Out-Null
  if ($LASTEXITCODE -ne 0) {
    & gh repo create $destinoRepo --private --disable-wiki `
        --description "Fonte do app $Package — build e release por CI" | Out-Null
    Log 'repositório privado criado' 'Green'
  } else { Log 'repositório já existia' }

  & git remote remove origin 2>$null | Out-Null
  & git remote add origin "https://github.com/$destinoRepo.git"
  & git push -u origin main --force
  Log 'fonte enviado' 'Green'

  if ($keystore) {
    $b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($keystore))
    $b64 | & gh secret set ANDROID_KEYSTORE_BASE64 --repo $destinoRepo
    Log 'secret ANDROID_KEYSTORE_BASE64 gravada (não aparece em log nenhum)' 'Green'
  }
  $deParaSecret = @{
    ANDROID_KEYSTORE_PASSWORD = 'STORE_PASSWORD|KEYSTORE_PASSWORD'
    ANDROID_KEY_ALIAS         = 'KEY_ALIAS'
    ANDROID_KEY_PASSWORD      = 'KEY_PASSWORD'
  }
  foreach ($nome in $deParaSecret.Keys) {
    $chave = $props.Keys | Where-Object { $_ -match $deParaSecret[$nome] } | Select-Object -First 1
    if ($chave) {
      $props[$chave] | & gh secret set $nome --repo $destinoRepo
      Log "secret $nome gravada"
    } else { Log "secret $nome não encontrada no gradle.properties" 'Yellow' }
  }
  if ($TelegramToken) { $TelegramToken | & gh secret set TELEGRAM_BOT_TOKEN --repo $destinoRepo }
  if ($TelegramChat)  { $TelegramChat  | & gh secret set TELEGRAM_CHAT_ID   --repo $destinoRepo }
} finally { Pop-Location }

$resumo = @"
Kansas: fonte do app saiu do PC.
repo privado: https://github.com/$destinoRepo
applicationId: $($fatos.applicationId)
targetSdk: $($fatos.targetSdk) | versionCode: $($fatos.versionCode)
keystore: $(if($keystore){'gravada como secret'}else{'NAO encontrada'})
Falta so a service account da Play para o envio rodar sozinho.
"@
Log $resumo 'Cyan'
Send-Telegram -Texto $resumo
Log 'pronto. Daqui pra frente o build roda no GitHub, com o PC desligado.' 'Green'
