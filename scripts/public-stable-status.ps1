. (Join-Path $PSScriptRoot "ops-common.ps1")

$ErrorActionPreference = "Stop"

Write-Section "ESTADO WEB ESTABLE"

$local = Get-LocalAppStatus
$stable = Get-StableTunnelStatus
$cloudflare = Get-CloudflareTunnelStatus
$tailscale = Get-TailscaleFunnelStatus

if ($local.FrontendReady) {
  Write-Ok "Frontend local activo en 3000."
} else {
  Write-Warn "Frontend local no detectado en 3000."
}

if ($local.BackendReady) {
  Write-Ok "Backend local activo en 8000."
} else {
  Write-Warn "Backend local no detectado en 8000."
}

if ($stable.ActiveProvider) {
  Write-Ok ("Proveedor activo: " + $stable.ActiveProvider)
} else {
  Write-Warn "Proveedor activo: ninguno"
}

if ($stable.PublicUrl) {
  Write-Ok ("URL publica: " + $stable.PublicUrl)
} else {
  Write-Warn "URL publica: aun no detectada"
}

if ($cloudflare.Installed) {
  if ($cloudflare.Version) {
    Write-Info ("Cloudflare version: " + $cloudflare.Version)
  }
  if ($cloudflare.Running) {
    $cloudflareLabel = if ($cloudflare.Mode -eq "named") { "Cloudflare Tunnel activo (dominio propio)." } else { "Cloudflare Tunnel activo (URL temporal)." }
    Write-Ok $cloudflareLabel
  } else {
    Write-Warn "Cloudflare Tunnel no esta activo ahora mismo."
  }
} else {
  Write-Warn "Cloudflare Tunnel no esta instalado en este equipo."
}

if ($tailscale.Installed) {
  if ($tailscale.Version) {
    Write-Info ("Tailscale version: " + $tailscale.Version)
  }
  if ($tailscale.Running) {
    Write-Ok "Tailscale Funnel activo."
  } else {
    Write-Warn "Tailscale Funnel no esta activo ahora mismo."
  }
} else {
  Write-Warn "Tailscale no esta instalado en este equipo."
}

Write-Host ""
if ($stable.Summary) {
  if ($stable.Ready) {
    Write-Ok $stable.Summary
  } else {
    Write-Warn $stable.Summary
  }
}
if ($stable.NextStep) {
  Write-Info $stable.NextStep
}

if ($stable.Ready) {
  exit 0
}
exit 1
