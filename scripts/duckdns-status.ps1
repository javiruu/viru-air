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

Write-Info "Dominio DuckDNS: $fqdn"
Write-Info "Config path:     $ConfigPath"
Write-Info "Log path:        $logPath"

$taskInfo = Get-ScheduledTaskInfo -TaskName $taskName
if ($taskInfo.Present) {
  if ($taskInfo.Enabled) {
    Write-Ok "Actualizacion automatica: activa ($taskName)"
  } else {
    Write-Warn "Actualizacion automatica: pausada ($taskName)"
  }
} else {
  Write-Fail "Actualizacion automatica: falta la tarea $taskName"
}

$dnsRows = @(Get-DnsARecords -Name $fqdn)
if ($dnsRows.Count -gt 0) {
  Write-Ok "DNS activo:              $($dnsRows -join ', ')"
} else {
  Write-Warn "DNS activo:              aun no resuelve"
}

$lastLog = Get-LastTabLogEntry -Path $logPath
if ($lastLog) {
  if ($lastLog.Result -eq "OK") {
    Write-Ok "Ultimo update:           OK ($($lastLog.Timestamp))"
  } else {
    Write-Warn "Ultimo update:           $($lastLog.Result) ($($lastLog.Timestamp))"
  }
} else {
  Write-Warn "Ultimo update:           sin registros todavia"
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
  Write-Info "Dominio web estable:     $($infraEnv['DOMAIN'])"
}

$caddy = Get-CaddyRuntimeStatus
$edge = Get-NetworkEdgeStatus
if (-not $caddy.Installed) {
  Write-Warn "Web estable:             falta el servicio web de entrada."
} elseif (-not $caddy.HasPidFile) {
  Write-Warn "Web estable:             aun no levantada."
} elseif ($caddy.Healthy) {
  Write-Ok "Web estable:             activa."
} elseif ($caddy.Running -and -not $caddy.TlsReady) {
  Write-Warn "Web estable:             Caddy corre, pero HTTPS aun no esta listo."
} else {
  Write-Warn "Web estable:             PID guardado, pero proceso o puertos no saludables."
}

if ($edge.PublicIp) {
  Write-Info "IP publica actual:       $($edge.PublicIp)"
}

if ($edge.UpnpExternalIp) {
  Write-Info "UPnP IP externa:         $($edge.UpnpExternalIp)"
}

if ($edge.DoubleNatDetected) {
  Write-Fail "Topologia de red:        doble NAT detectado."
}

if ($null -ne $caddy.DomainMatchesDuckDns) {
  if ($caddy.DomainMatchesDuckDns) {
    Write-Ok "Dominio web:             coincide con DuckDNS."
  } else {
    Write-Fail "Dominio web:             no coincide con DuckDNS."
  }
}

if (Test-Path $logPath) {
  Write-Info ""
  Write-Info "Ultimas lineas DuckDNS:"
  Get-Content -Path $logPath -Tail 5
}
