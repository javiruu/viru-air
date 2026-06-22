param(
  [string]$ConfigPath = "$PSScriptRoot\..\infra\duckdns.local.env"
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "ops-common.ps1")

Write-Section "DUCKDNS STATUS"

if (-not (Test-Path $ConfigPath)) {
  Write-Fail "Config no encontrada: $ConfigPath"
  exit 1
}

$config = Read-DotEnv -Path $ConfigPath
$fqdn = $config["DUCKDNS_FQDN"]
$domain = $config["DUCKDNS_DOMAIN"]
$taskName = if ($config.ContainsKey("DUCKDNS_TASK_NAME")) { $config["DUCKDNS_TASK_NAME"] } else { "ViruTracker-DuckDNS" }
$logPath = if ($config.ContainsKey("DUCKDNS_LOG_PATH")) { $config["DUCKDNS_LOG_PATH"] } else { "logs/duckdns-update.log" }

if (-not $fqdn -and $domain) {
  $fqdn = "$domain.duckdns.org"
}

if (-not [System.IO.Path]::IsPathRooted($logPath)) {
  $logPath = Join-Path (Get-RepoRoot) $logPath
}

Write-Info "DuckDNS domain: $fqdn"
Write-Info "Config path:    $ConfigPath"
Write-Info "Log path:       $logPath"

$taskInfo = Get-ScheduledTaskInfo -TaskName $taskName
if ($taskInfo.Present) {
  if ($taskInfo.Enabled) {
    Write-Ok "Scheduled task: OK ($taskName)"
  } else {
    Write-Warn "Scheduled task: DISABLED ($taskName)"
  }
} else {
  Write-Fail "Scheduled task: MISSING ($taskName)"
}

$dnsRows = @(Get-DnsARecords -Name $fqdn)
if ($dnsRows.Count -gt 0) {
  Write-Ok "DNS A records:  $($dnsRows -join ', ')"
} else {
  Write-Warn "DNS A records:  not resolved yet"
}

$lastLog = Get-LastTabLogEntry -Path $logPath
if ($lastLog) {
  if ($lastLog.Result -eq "OK") {
    Write-Ok "Ultimo update:  OK ($($lastLog.Timestamp))"
  } else {
    Write-Warn "Ultimo update:  $($lastLog.Result) ($($lastLog.Timestamp))"
  }
} else {
  Write-Warn "Ultimo update:  sin registros todavia"
}

$portStates = Get-PortListeners -Ports @(80, 443)
foreach ($state in $portStates | Sort-Object Port) {
  if ($state.Listening) {
    Write-Warn (Format-PortLine -PortState $state)
  } else {
    Write-Ok (Format-PortLine -PortState $state)
  }
}

$infraEnv = Read-DotEnv -Path (Get-InfraEnvPath) -AllowMissing
if ($infraEnv.ContainsKey("DOMAIN")) {
  Write-Info "infra/.env DOMAIN: $($infraEnv['DOMAIN'])"
}

$caddy = Get-CaddyRuntimeStatus
if (-not $caddy.DockerAvailable) {
  Write-Warn "Caddy status: docker compose no disponible."
} elseif (-not $caddy.ServiceDefined) {
  Write-Warn "Caddy status: servicio caddy no definido."
} elseif (-not $caddy.Exists) {
  Write-Warn "Caddy status: contenedor aun no creado."
} elseif ($caddy.Running) {
  Write-Ok "Caddy status: corriendo."
} else {
  Write-Warn "Caddy status: creado pero parado ($($caddy.State))."
}

if ($null -ne $caddy.DomainMatchesDuckDns) {
  if ($caddy.DomainMatchesDuckDns) {
    Write-Ok "DOMAIN coincide con DuckDNS."
  } else {
    Write-Fail "DOMAIN no coincide con DuckDNS."
  }
}

if (Test-Path $logPath) {
  Write-Info ""
  Write-Info "Ultimas lineas DuckDNS:"
  Get-Content -Path $logPath -Tail 5
}
