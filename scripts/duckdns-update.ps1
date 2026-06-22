param(
  [string]$ConfigPath = "$PSScriptRoot\..\infra\duckdns.local.env"
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "ops-common.ps1")

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
  $logPath = Join-Path (Get-LogsDir) "duckdns-update.log"
} elseif (-not [System.IO.Path]::IsPathRooted($logPath)) {
  $logPath = Join-Path (Get-RepoRoot) $logPath
}

$logDir = Split-Path -Parent $logPath
if (-not (Test-Path $logDir)) {
  New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

try {
  $response = Invoke-WebRequest -Uri $updateUrl -UseBasicParsing -TimeoutSec 20
  $content = $response.Content
  if ($content -is [byte[]]) {
    $content = [System.Text.Encoding]::UTF8.GetString($content)
  }
  $result = [string]$content
  $result = $result.Trim()
} catch {
  $result = "ERROR"
  $errorMessage = $_.Exception.Message
  Add-Content -Path $logPath -Value "$timestamp`t$result`t$errorMessage" -Encoding ASCII
  Write-Fail ("DuckDNS update: ERROR - $errorMessage")
  exit 1
}

if ($result -notmatch "^(OK|KO)$") {
  Add-Content -Path $logPath -Value "$timestamp`tUNEXPECTED`t$result" -Encoding ASCII
  Write-Fail ("DuckDNS update: respuesta inesperada - $result")
  exit 1
}

Add-Content -Path $logPath -Value "$timestamp`t$result`t$domain" -Encoding ASCII

if ($result -eq "OK") {
  Write-Ok "DuckDNS update: OK"
  exit 0
}

Write-Fail "DuckDNS update: KO"
exit 1
