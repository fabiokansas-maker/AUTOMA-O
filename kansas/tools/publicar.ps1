<#
.SYNOPSIS
  Uma linha, uma vez. Pega sua chave de assinatura, entrega ao GitHub e
  dispara o build assinado do Kansas IA Financeira na nuvem.

.DESCRIPTION
  O que ele faz, sozinho:
    1. procura no PC a keystore do app com.pulsefinanceiro.dreai
    2. lê as senhas do gradle.properties (nunca imprime nenhuma)
    3. instala git e gh se faltarem (winget), e faz login no GitHub se preciso
    4. grava as secrets de assinatura no repositório fabiokansas-maker/AUTOMA-O
    5. dispara o workflow que compila o AAB assinado
    6. espera terminar e baixa o AAB pronto para o seu Desktop

  O que ele NÃO faz: publicar sem você saber. O envio à Play só acontece se
  a conta de serviço existir como secret; caso contrário você recebe o AAB
  assinado e pronto na mão.

.EXAMPLE
  irm https://raw.githubusercontent.com/fabiokansas-maker/AUTOMA-O/claude/download-local-files-5hfmT/kansas/tools/publicar.ps1 | iex
#>
[CmdletBinding()]
param(
  [string] $Package   = "com.pulsefinanceiro.dreai",
  [string] $Repo      = "fabiokansas-maker/AUTOMA-O",
  [string] $Ref       = "claude/kansas-agent-first-rebuild-ptcc1w",
  [string] $Track     = "internal",
  [string] $KeystorePath = "",
  [switch] $DryRun
)

$ErrorActionPreference = 'Stop'
function Log($m, $c = 'Gray') { Write-Host $m -ForegroundColor $c }
function Falhar($m) { Log "ERRO: $m" 'Red'; throw $m }

Log '=== Kansas — publicar ===' 'Cyan'
if ($DryRun) { Log '(ENSAIO: nada será gravado nem disparado)' 'Yellow' }

# ---------------------------------------------------------- 1. a keystore
function Find-Keystore {
  param([string]$Package)

  $raizes = @('C:\Dev', 'D:\Dev', (Join-Path $HOME 'Downloads'),
              (Join-Path $HOME 'Documents'), (Join-Path $HOME 'source'),
              (Join-Path $HOME 'AndroidStudioProjects'), $HOME) |
            Where-Object { $_ -and (Test-Path $_) } | Select-Object -Unique

  # primeiro: keystore ao lado do projeto que tem o applicationId certo
  foreach ($raiz in $raizes) {
    Log "procurando em $raiz ..."
    $gradles = Get-ChildItem $raiz -Recurse -Filter 'build.gradle*' -File -Depth 6 `
                 -ErrorAction SilentlyContinue |
               Where-Object { $_.FullName -notmatch '[\\/](node_modules|build|\.gradle)[\\/]' }
    foreach ($g in $gradles) {
      $txt = Get-Content -Raw -LiteralPath $g.FullName -ErrorAction SilentlyContinue
      if ($txt -and $txt -match [regex]::Escape($Package)) {
        $projeto = Split-Path (Split-Path $g.FullName -Parent) -Parent
        $ks = Get-ChildItem $projeto -Recurse -Include '*.keystore', '*.jks' -File `
                -Depth 4 -ErrorAction SilentlyContinue |
              Where-Object { $_.Name -notmatch 'debug' } | Select-Object -First 1
        if ($ks) { return @{ keystore = $ks.FullName; projeto = $projeto } }
        return @{ keystore = $null; projeto = $projeto }
      }
    }
  }
  # segundo: qualquer keystore de release no perfil
  foreach ($raiz in $raizes) {
    $ks = Get-ChildItem $raiz -Recurse -Include '*.keystore', '*.jks' -File `
            -Depth 5 -ErrorAction SilentlyContinue |
          Where-Object { $_.Name -notmatch 'debug' } | Select-Object -First 1
    if ($ks) { return @{ keystore = $ks.FullName; projeto = $null } }
  }
  return @{ keystore = $null; projeto = $null }
}

if ($KeystorePath -and (Test-Path $KeystorePath)) {
  $achado = @{ keystore = (Resolve-Path $KeystorePath).Path; projeto = $null }
} else {
  $achado = Find-Keystore -Package $Package
}

if (-not $achado.keystore) {
  Log 'Não achei a keystore de release neste PC.' 'Red'
  Log 'Se você sabe onde ela está, rode de novo com:' 'Yellow'
  Log '  irm <url> | iex; publicar -KeystorePath "C:\caminho\da\chave.jks"' 'Yellow'
  Falhar 'sem chave não há envio: a Play recusa qualquer AAB com outra assinatura'
}
Log "chave encontrada: $(Split-Path $achado.keystore -Leaf)" 'Green'
if ($achado.projeto) { Log "projeto original: $($achado.projeto)" }

# ------------------------------------------------------------ 2. as senhas
$props = @{}
$candidatos = @()
if ($achado.projeto) {
  $candidatos += (Join-Path $achado.projeto 'gradle.properties')
  $candidatos += (Join-Path $achado.projeto 'android/gradle.properties')
}
$candidatos += (Join-Path $HOME '.gradle/gradle.properties')
foreach ($f in ($candidatos | Where-Object { Test-Path $_ })) {
  foreach ($linha in Get-Content -LiteralPath $f) {
    if ($linha -match '^\s*([A-Za-z0-9_.]+)\s*=\s*(.+?)\s*$') { $props[$Matches[1]] = $Matches[2] }
  }
}
function Achar-Prop([string]$padrao) {
  $k = $props.Keys | Where-Object { $_ -match $padrao } | Select-Object -First 1
  if ($k) { return $props[$k] } else { return $null }
}
$senhaStore = Achar-Prop 'STORE_PASSWORD|KEYSTORE_PASSWORD'
$alias      = Achar-Prop 'KEY_ALIAS'
$senhaKey   = Achar-Prop 'KEY_PASSWORD'

if (-not $senhaStore -or -not $alias) {
  Log 'não achei as senhas no gradle.properties — vou pedir aqui, sem gravar em disco' 'Yellow'
  if (-not $alias)      { $alias = Read-Host 'alias da chave' }
  if (-not $senhaStore) { $senhaStore = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
      [Runtime.InteropServices.Marshal]::SecureStringToBSTR((Read-Host 'senha da keystore' -AsSecureString))) }
  if (-not $senhaKey)   { $senhaKey = $senhaStore }
}
if (-not $senhaKey) { $senhaKey = $senhaStore }
Log "alias: $alias  ·  senhas: obtidas (não serão exibidas)" 'Green'

# confere que a chave abre com essas credenciais antes de gravar nada
if (Get-Command keytool -ErrorAction SilentlyContinue) {
  $teste = & keytool -list -keystore $achado.keystore -storepass $senhaStore -alias $alias 2>&1
  if ($LASTEXITCODE -ne 0) { Falhar "a chave não abre com essa senha/alias — nada foi enviado" }
  Log 'chave validada com keytool' 'Green'
}

# ---------------------------------------------------------- 3. git e gh
function Garantir($nome, $wingetId) {
  if (Get-Command $nome -ErrorAction SilentlyContinue) { Log "$nome ok"; return $true }
  Log "instalando $nome ..." 'Yellow'
  winget install -e --id $wingetId --silent --accept-package-agreements --accept-source-agreements | Out-Null
  $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' +
              [Environment]::GetEnvironmentVariable('Path','User')
  return [bool](Get-Command $nome -ErrorAction SilentlyContinue)
}
if ($DryRun) {
  Log '[ensaio] gravaria as secrets e dispararia o build' 'Yellow'
  Log "[ensaio] repo $Repo · ref $Ref · faixa $Track"
  return
}
if (-not (Garantir 'gh' 'GitHub.cli')) { Falhar 'preciso do GitHub CLI (gh)' }

& gh auth status 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
  Log 'abrindo o login do GitHub no navegador (uma vez só)...' 'Yellow'
  & gh auth login --web --git-protocol https --scopes 'repo,workflow'
  if ($LASTEXITCODE -ne 0) { Falhar 'login não concluído' }
}

# ------------------------------------------------------- 4. grava secrets
$b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($achado.keystore))
$b64        | & gh secret set ANDROID_KEYSTORE_BASE64   --repo $Repo
$senhaStore | & gh secret set ANDROID_KEYSTORE_PASSWORD --repo $Repo
$alias      | & gh secret set ANDROID_KEY_ALIAS         --repo $Repo
$senhaKey   | & gh secret set ANDROID_KEY_PASSWORD      --repo $Repo
Log 'secrets gravadas no GitHub (nunca aparecem em log)' 'Green'

# ------------------------------------------------- 5. dispara o build
Log "disparando o build assinado (ref $Ref, faixa $Track) ..." 'Cyan'
& gh workflow run kansas-release.yml --repo $Repo --ref $Ref -f track=$Track
if ($LASTEXITCODE -ne 0) { Falhar 'não consegui disparar o workflow' }
Start-Sleep -Seconds 8

$runId = (& gh run list --repo $Repo --workflow kansas-release.yml --limit 1 --json databaseId `
          --jq '.[0].databaseId').Trim()
Log "run: https://github.com/$Repo/actions/runs/$runId"
& gh run watch $runId --repo $Repo --exit-status
$okBuild = ($LASTEXITCODE -eq 0)

# --------------------------------------------- 6. traz o AAB pronto
$destino = Join-Path ([Environment]::GetFolderPath('Desktop')) 'kansas-aab'
New-Item -ItemType Directory -Force -Path $destino | Out-Null
& gh run download $runId --repo $Repo --dir $destino 2>$null
$aab = Get-ChildItem $destino -Recurse -Filter '*.aab' -ErrorAction SilentlyContinue |
       Select-Object -First 1

if ($aab) {
  Log "" ; Log "AAB ASSINADO PRONTO: $($aab.FullName)" 'Green'
  Log 'Se a conta de serviço da Play estiver configurada, ele já subiu para a' 'Green'
  Log 'faixa interna. Se não, este arquivo é o que a Play aceita — e ele está' 'Green'
  Log 'assinado com a SUA chave, então atualiza o app existente.' 'Green'
} elseif ($okBuild) {
  Log 'build terminou, mas não achei o .aab nos artefatos. Veja o run acima.' 'Yellow'
} else {
  Log 'o build falhou — o log do run acima diz exatamente onde.' 'Red'
}
