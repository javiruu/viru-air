. (Join-Path $PSScriptRoot "ops-common.ps1")

Write-Section "CADDY STATUS"
$status = Get-CaddyRuntimeStatus

if (-not $status.Installed) {
  Write-Fail "caddy no esta instalado en esta maquina."
  exit 1
}

if (-not $status.InfraEnvExists) {
  Write-Warn "Falta infra/.env, asi que DOMAIN aun no esta definido para Caddy."
}

if ($status.Domain) {
  Write-Info ("DOMAIN actual: $($status.Domain)")
}

if (-not $status.HasPidFile) {
  Write-Warn "Caddy aun no fue arrancado desde este panel."
  exit 1
}

if ($status.Running) {
  Write-Ok ("Caddy corriendo (PID $($status.ProcessId), proceso $($status.ProcessName)).")
  if ($status.PublishedPorts.Count -gt 0) {
    Write-Ok ("Puertos publicados: $($status.PublishedPorts -join ', ')")
  } else {
    Write-Warn "Caddy corre, pero no detecte puertos publicados."
  }
} else {
  Write-Warn "Habia un PID guardado para Caddy, pero el proceso ya no esta vivo."
}

if ($null -ne $status.DomainMatchesDuckDns) {
  if ($status.DomainMatchesDuckDns) {
    Write-Ok "DOMAIN coincide con el FQDN configurado en DuckDNS."
  } else {
    Write-Fail "DOMAIN no coincide con el FQDN configurado en DuckDNS."
  }
}

if ($status.Healthy) { exit 0 }
exit 1
