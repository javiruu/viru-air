. (Join-Path $PSScriptRoot "ops-common.ps1")

Write-Section "CADDY STATUS"
$status = Get-CaddyRuntimeStatus

if (-not $status.DockerAvailable) {
  Write-Fail "docker compose no esta disponible."
  exit 1
}

if (-not $status.InfraEnvExists) {
  Write-Warn "Falta infra/.env, asi que DOMAIN aun no esta definido para Caddy."
}

if ($status.Domain) {
  Write-Info ("DOMAIN actual: $($status.Domain)")
}

if (-not $status.ServiceDefined) {
  Write-Fail "El servicio caddy no esta definido en los compose de infra."
  exit 1
}

if (-not $status.Exists) {
  Write-Warn "El contenedor de Caddy aun no fue creado."
  exit 1
}

if ($status.Running) {
  Write-Ok ("Caddy corriendo (container $($status.ContainerId), estado $($status.State)).")
  if ($status.PublishedPorts.Count -gt 0) {
    Write-Ok ("Puertos publicados: $($status.PublishedPorts -join ', ')")
  } else {
    Write-Warn "Caddy corre, pero no detecte puertos publicados."
  }
} else {
  Write-Warn ("Contenedor de Caddy existe, pero esta en estado '$($status.State)'.")
}

if ($null -ne $status.DomainMatchesDuckDns) {
  if ($status.DomainMatchesDuckDns) {
    Write-Ok "DOMAIN coincide con el FQDN configurado en DuckDNS."
  } else {
    Write-Fail "DOMAIN no coincide con el FQDN configurado en DuckDNS."
  }
}

if ($status.Running) { exit 0 }
exit 1
