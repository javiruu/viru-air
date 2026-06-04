param(
  [string]$ConfigPath = "$PSScriptRoot\..\infra\duckdns.local.env"
)

$ErrorActionPreference = "Stop"

function Read-DotEnv {
  param([string]$Path)

  if (-not (Test-Path $Path)) {
    throw "Config no encontrada: $Path. Ejecuta scripts/setup-duckdns.ps1 primero."
  }

  $values = @{}
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

$config = Read-DotEnv -Path $ConfigPath
$domain = $config["DUCKDNS_DOMAIN"]
$token = $config["DUCKDNS_TOKEN"]
$updateUrl = $config["DUCKDNS_UPDATE_URL"]
$logPath = $config["DUCKDNS_LOG_PATH"]

if (-not $domain -or -not $token) {
  throw "DUCKDNS_DOMAIN y DUCKDNS_TOKEN son obligatorios en $ConfigPath."
}

if (-not $updateUrl) {
  $updateUrl = "https://www.duckdns.org/update?domains=$domain&token=$token&ip="
}

if (-not $logPath) {
  $logPath = Join-Path (Split-Path -Parent $PSScriptRoot) "logs\duckdns-update.log"
} elseif (-not [System.IO.Path]::IsPathRooted($logPath)) {
  $logPath = Join-Path (Split-Path -Parent $PSScriptRoot) $logPath
}

$logDir = Split-Path -Parent $logPath
if (-not (Test-Path $logDir)) {
  New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$response = Invoke-WebRequest -Uri $updateUrl -UseBasicParsing
$result = $response.Content.Trim()
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$logLine = "$timestamp`t$result`t$domain"
Add-Content -Path $logPath -Value $logLine -Encoding ASCII

if ($result -notmatch "^(OK|KO)$") {
  throw "Respuesta inesperada de DuckDNS: $result"
}

Write-Host "DuckDNS update: $result"
