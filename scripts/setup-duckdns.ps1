param(
  [string]$Domain = "virutracker",
  [string]$Token = "",
  [string]$ConfigPath = "$PSScriptRoot\..\infra\duckdns.local.env",
  [int]$UpdateEveryMinutes = 5
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "ops-common.ps1")

function Normalize-DuckDomain {
  param([string]$RawDomain)

  $trimmed = $RawDomain.Trim().ToLowerInvariant()
  if ($trimmed.EndsWith(".duckdns.org")) {
    $trimmed = $trimmed.Substring(0, $trimmed.Length - ".duckdns.org".Length)
  }
  return $trimmed
}

$repoRoot = Get-RepoRoot
$logsDir = Get-LogsDir

$existingConfig = Read-DotEnv -Path $ConfigPath
$normalizedDomain = Normalize-DuckDomain -RawDomain $Domain

if (-not $normalizedDomain) {
  throw "Debes indicar un subdominio DuckDNS valido."
}

if (-not $Token -and $existingConfig.ContainsKey("DUCKDNS_TOKEN")) {
  $Token = $existingConfig["DUCKDNS_TOKEN"]
}

if (-not $Token) {
  throw "Debes pasar -Token o rellenar DUCKDNS_TOKEN en $ConfigPath."
}

$fqdn = "$normalizedDomain.duckdns.org"
$taskName = "ViruTracker-DuckDNS"
$updateUrl = "https://www.duckdns.org/update?domains=$normalizedDomain&token=$Token&ip="

$configDir = Split-Path -Parent $ConfigPath
if (-not (Test-Path $configDir)) {
  New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}

$configContent = @"
# Local DuckDNS config for viru-tracker.
DUCKDNS_DOMAIN=$normalizedDomain
DUCKDNS_FQDN=$fqdn
DUCKDNS_TOKEN=$Token
DUCKDNS_UPDATE_URL=$updateUrl
DUCKDNS_LOG_PATH=logs/duckdns-update.log
DUCKDNS_TASK_NAME=$taskName
"@

Set-Content -Path $ConfigPath -Value $configContent -Encoding ASCII

Write-Host "Config escrita en: $ConfigPath"
Write-Host "Dominio canonico:  https://$fqdn"

$infraEnv = Ensure-InfraEnv -Domain $fqdn
Write-Host "infra/.env listo:   $($infraEnv.Path)"
if ($infraEnv.JwtGenerated) {
  Write-Host "JWT_SECRET:         generado automaticamente"
}

$updateScript = Join-Path $PSScriptRoot "duckdns-update.ps1"
$taskCommand = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$updateScript`" -ConfigPath `"$ConfigPath`""

schtasks /Create /TN $taskName /TR $taskCommand /SC MINUTE /MO $UpdateEveryMinutes /F | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "No se pudo registrar la tarea programada $taskName."
}

Write-Host "Tarea programada: $taskName (cada $UpdateEveryMinutes minutos)"

$updateSucceeded = $true
try {
  & $updateScript -ConfigPath $ConfigPath
  if ($LASTEXITCODE -ne 0) {
    $updateSucceeded = $false
  }
} catch {
  $updateSucceeded = $false
  Write-Warn ("El update inicial DuckDNS fallo: " + $_.Exception.Message)
}

Write-Host ""
Write-Host "Comprobando si la web estable puede quedar lista..."

if ($updateSucceeded) {
  $stableScript = Join-Path $PSScriptRoot "public-stable-start.ps1"
  & $stableScript -AutoMode
  if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Warn "DuckDNS quedo configurado, pero la web estable aun no ha podido quedarse activa."
  }
} else {
  Write-Host ""
  Write-Warn "DuckDNS quedo configurado, pero el dominio aun no pudo actualizarse correctamente."
}

Write-Host ""
Write-Host "Setup DuckDNS completado."
Write-Host "1. El dominio queda guardado en infra/duckdns.local.env."
Write-Host "2. Usa ESTADO WEB ESTABLE en el panel para comprobar si ya ha quedado publicada."
Write-Host "3. Usa PUBLICAR RAPIDO solo para URLs temporales."
