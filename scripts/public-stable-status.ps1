param(
  [switch]$SaveCurrentNetworkProfile,
  [string]$ProfileLabel,
  [switch]$SetActive
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "ops-common.ps1")

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
$edge = $preflight.EdgeStatus
$networkDiagnosis = $preflight.NetworkDiagnosis

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

if ($edge.PublicIp) {
  Write-Info ("IP publica:    $($edge.PublicIp)")
}

if ($edge.UpnpExternalIp) {
  Write-Info ("UPnP externa:  $($edge.UpnpExternalIp)")
}

if ($edge.DoubleNatDetected) {
  Write-Fail "Topologia:     doble NAT detectado"
} elseif ($edge.UpnpSupported) {
  Write-Ok "Topologia:     sin doble NAT evidente en UPnP"
}

if ($networkDiagnosis.Current.LocalIp) {
  Write-Info ("IP del PC:     $($networkDiagnosis.Current.LocalIp)")
}

if ($networkDiagnosis.Current.Gateway) {
  Write-Info ("Router actual: $($networkDiagnosis.Current.Gateway)")
}

if ($networkDiagnosis.DetectedProfile) {
  Write-Info ("Perfil de red: $($networkDiagnosis.DetectedProfile.label)")
} elseif ($networkDiagnosis.IsNewNetwork) {
  Write-Warn "Perfil de red: red nueva detectada"
}

if ($networkDiagnosis.ActiveProfileId -and $networkDiagnosis.ActiveProfileId -ne "auto" -and $networkDiagnosis.ActiveProfile) {
  Write-Info ("Perfil activo: $($networkDiagnosis.ActiveProfile.label)")
} else {
  Write-Info ("Perfil activo: auto")
}

if ($networkDiagnosis.CurrentMode -eq "double_nat") {
  Write-Info "Modo de red:   router intermedio"
} elseif ($networkDiagnosis.CurrentMode -eq "direct_router") {
  Write-Info "Modo de red:   router directo"
} else {
  Write-Info "Modo de red:   sin clasificar"
}

if ($status.Healthy) {
  Write-Ok "Web estable:  activa"
  Write-Info ("Puertos:      " + ($status.PublishedPorts -join ", "))
} elseif ($status.HasPidFile -and $status.Running -and -not $status.TlsReady) {
  Write-Warn "Web estable:  el proceso esta vivo, pero HTTPS aun no esta listo."
} elseif ($status.HasPidFile -and $status.Running) {
  Write-Warn "Web estable:  el proceso esta vivo, pero no detecte los puertos 80/443 publicados."
} elseif ($status.HasPidFile) {
  Write-Warn "Web estable:  habia un PID guardado, pero el proceso ya no sigue vivo."
} else {
  Write-Warn "Web estable:  aun no esta levantada."
}

if ($status.TlsReady) {
  Write-Ok "TLS:          certificado o handshake HTTPS listos"
} elseif ($status.TlsDetail -and $status.TlsDetail.Error) {
  Write-Warn ("TLS:          " + $status.TlsDetail.Error)
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
if ($networkDiagnosis -and $networkDiagnosis.Summary) {
  if ($networkDiagnosis.CaseCode -eq "A") {
    Write-Ok $networkDiagnosis.Summary
  } else {
    Write-Warn $networkDiagnosis.Summary
  }
}
if ($networkDiagnosis -and $networkDiagnosis.NextStep) {
  Write-Info $networkDiagnosis.NextStep
}

if ($SaveCurrentNetworkProfile) {
  if (-not $publicDomain) {
    Write-Fail "No puedo guardar el perfil porque aun no hay dominio estable configurado."
    exit 1
  }

  try {
    $saveResult = Save-PublicStableNetworkProfile -Domain $publicDomain -CurrentNetwork $networkDiagnosis.Current -EdgeStatus $edge -Label $ProfileLabel -SetActive:$SetActive
    Write-Info ("Perfil guardado en: " + $saveResult.Path)
    Write-Ok ("Perfil guardado: " + $saveResult.Profile.label)
    if ($SetActive) {
      Write-Info ("Perfil activo nuevo: " + $saveResult.Profile.id)
    }
  } catch {
    Write-Fail $_.Exception.Message
    exit 1
  }
}

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
