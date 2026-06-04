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
$fqdn = $config["DUCKDNS_FQDN"]
$domain = $config["DUCKDNS_DOMAIN"]
$taskName = $config["DUCKDNS_TASK_NAME"]
$logPath = $config["DUCKDNS_LOG_PATH"]

if (-not $fqdn) {
  $fqdn = "$domain.duckdns.org"
}

if (-not $logPath) {
  $logPath = Join-Path (Split-Path -Parent $PSScriptRoot) "logs\duckdns-update.log"
} elseif (-not [System.IO.Path]::IsPathRooted($logPath)) {
  $logPath = Join-Path (Split-Path -Parent $PSScriptRoot) $logPath
}

Write-Host "DuckDNS domain: $fqdn"
Write-Host "Config path:    $ConfigPath"
Write-Host "Log path:       $logPath"

if ($taskName) {
  $taskQuery = schtasks /Query /TN $taskName 2>$null
  if ($LASTEXITCODE -eq 0) {
    Write-Host "Scheduled task: OK ($taskName)"
  } else {
    Write-Host "Scheduled task: MISSING ($taskName)"
  }
}

try {
  $dnsRows = Resolve-DnsName -Name $fqdn -Type A -ErrorAction Stop |
    Where-Object { $_.IPAddress } |
    Select-Object -ExpandProperty IPAddress
  if ($dnsRows) {
    Write-Host "DNS A records:  $($dnsRows -join ', ')"
  } else {
    Write-Host "DNS A records:  none detected"
  }
} catch {
  Write-Host "DNS A records:  not resolved yet"
}

if (Test-Path $logPath) {
  Write-Host ""
  Write-Host "Ultimas lineas DuckDNS:"
  Get-Content -Path $logPath -Tail 5
} else {
  Write-Host "Log:            sin actualizaciones todavia"
}
