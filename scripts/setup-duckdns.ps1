param(
  [string]$Domain = "virutracker",
  [string]$Token = "",
  [string]$ConfigPath = "$PSScriptRoot\..\infra\duckdns.local.env",
  [int]$UpdateEveryMinutes = 5
)

$ErrorActionPreference = "Stop"

function Normalize-DuckDomain {
  param([string]$RawDomain)

  $trimmed = $RawDomain.Trim().ToLowerInvariant()
  if ($trimmed.EndsWith(".duckdns.org")) {
    $trimmed = $trimmed.Substring(0, $trimmed.Length - ".duckdns.org".Length)
  }
  return $trimmed
}

function Read-DotEnv {
  param([string]$Path)

  $values = @{}
  if (-not (Test-Path $Path)) {
    return $values
  }

  foreach ($line in Get-Content -Path $Path) {
    $trimmed = $line.Trim()
    if (-not $trimmed -or $trimmed.StartsWith("#")) {
      continue
    }

    $parts = $trimmed -split "=", 2
    if ($parts.Count -eq 2) {
      $values[$parts[0].Trim()] = $parts[1].Trim()
    }
  }

  return $values
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$logsDir = Join-Path $repoRoot "logs"
if (-not (Test-Path $logsDir)) {
  New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
}

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

$updateScript = Join-Path $PSScriptRoot "duckdns-update.ps1"
$taskCommand = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$updateScript`" -ConfigPath `"$ConfigPath`""

schtasks /Create /TN $taskName /TR $taskCommand /SC MINUTE /MO $UpdateEveryMinutes /F | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "No se pudo registrar la tarea programada $taskName."
}

Write-Host "Tarea programada: $taskName (cada $UpdateEveryMinutes minutos)"

& $updateScript -ConfigPath $ConfigPath

Write-Host ""
Write-Host "Setup DuckDNS completado."
Write-Host "1. Ajusta DOMAIN=$fqdn en tus envs de despliegue."
Write-Host "2. Usa Caddy para el dominio estable."
Write-Host "3. Usa PUBLICAR RAPIDO solo para URLs temporales."
