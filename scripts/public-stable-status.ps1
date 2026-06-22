. (Join-Path $PSScriptRoot "ops-common.ps1")

$ErrorActionPreference = "Stop"

function Show-Line {
  param(
    [Parameter(Mandatory)][ValidateSet("ok", "warn", "fail", "info")] [string]$Level,
    [Parameter(Mandatory)][string]$Text
  )

  switch ($Level) {
    "ok" { Write-Ok $Text }
    "warn" { Write-Warn $Text }
    "fail" { Write-Fail $Text }
    default { Write-Info $Text }
  }
}

Write-Section "ESTADO WEB ESTABLE"

$duck = Read-DotEnv -Path (Get-DuckDnsConfigPath) -AllowMissing
$infra = Read-DotEnv -Path (Get-InfraEnvPath) -AllowMissing
$status = Get-CaddyRuntimeStatus
$preflight = Get-PublicDomainPreflight

$publicDomain = if ($infra.ContainsKey("DOMAIN") -and $infra["DOMAIN"]) { $infra["DOMAIN"] } elseif ($duck.ContainsKey("DUCKDNS_FQDN")) { $duck["DUCKDNS_FQDN"] } else { $null }
if ($publicDomain) {
  Write-Info ("URL esperada: https://$publicDomain")
} else {
  Write-Warn "Aun no hay un dominio web estable configurado."
}

if ($duck.ContainsKey("DUCKDNS_FQDN")) {
  Write-Info ("DuckDNS:      $($duck['DUCKDNS_FQDN'])")
}

$lastUpdate = $preflight.LastDuckUpdate
if ($lastUpdate) {
  if ($lastUpdate.Result -eq "OK") {
    Write-Ok ("Ultima actualizacion del dominio: OK ($($lastUpdate.Timestamp))")
  } else {
    Write-Warn ("Ultima actualizacion del dominio: $($lastUpdate.Result) ($($lastUpdate.Timestamp))")
  }
}

if ($preflight.DnsRecords.Count -gt 0 -and $publicDomain) {
  Write-Ok ("DNS activo:   $($preflight.DnsRecords -join ', ')")
} elseif ($publicDomain) {
  Write-Warn "DNS:          el dominio aun no resuelve desde fuera."
}

$taskInfo = $preflight.TaskInfo
if ($taskInfo.Present -and $taskInfo.Enabled) {
  Write-Ok ("DuckDNS auto: activo ($($taskInfo.State))")
} elseif ($taskInfo.Present) {
  Write-Warn "DuckDNS auto: pausado"
} else {
  Write-Fail "DuckDNS auto: no existe la tarea automatica"
}

if ($status.Healthy) {
  Write-Ok "Web estable:  activa"
  Write-Info ("Puertos:      " + ($status.PublishedPorts -join ", "))
} elseif ($status.HasPidFile -and $status.Running) {
  Write-Warn "Web estable:  el proceso esta vivo, pero no detecte los puertos 80/443 publicados."
} elseif ($status.HasPidFile) {
  Write-Warn "Web estable:  habia un PID guardado, pero el proceso ya no sigue vivo."
} else {
  Write-Warn "Web estable:  aun no esta levantada."
}

$frontendOk = @($preflight.Checks | Where-Object { $_.Name -eq "Frontend local" -and $_.Status -eq "ok" }).Count -gt 0
$backendOk = @($preflight.Checks | Where-Object { $_.Name -eq "Backend local" -and $_.Status -eq "ok" }).Count -gt 0

if ($frontendOk) {
  Write-Ok "Frontend:     activo en 3000"
} else {
  Write-Warn "Frontend:     no detectado en 3000"
}

if ($backendOk) {
  Write-Ok "Backend:      activo en 8000"
} else {
  Write-Warn "Backend:      no detectado en 8000"
}

$busyPorts = @(Get-PortListeners -Ports @(80, 443) | Where-Object { $_.Listening -and $_.ProcessName -ne "caddy" })
if ($busyPorts.Count -gt 0) {
  foreach ($busy in $busyPorts | Sort-Object Port, ProcessId -Unique) {
    Write-Warn ("Puerto $($busy.Port) ocupado por PID $($busy.ProcessId) ($($busy.ProcessName))")
  }
}

Write-Host ""
if ($status.Healthy) {
  Write-Ok "La web estable esta publicada y lista para entrar desde fuera."
  exit 0
}

if ($preflight.Ready) {
  Write-Warn "El dominio ya esta listo, pero la web estable todavia no se ha levantado."
  Write-Info "Usa la opcion PUBLICAR WEB ESTABLE para arrancarla."
  exit 1
}

Write-Warn "Todavia faltan piezas antes de dar la web por publicada."
exit 1
