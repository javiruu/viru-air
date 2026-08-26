. (Join-Path $PSScriptRoot "ops-common.ps1")

$ErrorActionPreference = "Stop"

Write-Section "ESTADO WEB PUBLICA"

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
  Write-Ok ("Tuneles activos: " + $stable.ActiveProvider)
} else {
  Write-Warn "Tuneles activos: ninguno"
}

if ($stable.PublicUrls -and $stable.PublicUrls.Count -gt 0) {
  Write-Ok "URLs publicas detectadas:"
  foreach ($url in $stable.PublicUrls) {
    Write-Ok ("  " + $url)
  }
} else {
  Write-Warn "URLs publicas: aun no detectadas"
}

if ($cloudflare.Installed) {
  if ($cloudflare.Version) {
    Write-Info ("Cloudflare version: " + $cloudflare.Version)
  }
  if ($cloudflare.Running) {
    $cloudflareLabel = if ($cloudflare.Mode -eq "named") { "Cloudflare Tunnel activo (dominio propio)." } else { "Cloudflare Tunnel activo (URL temporal)." }
    Write-Ok $cloudflareLabel
    if ($cloudflare.PublicUrl) {
      Write-Info ("Cloudflare URL: " + $cloudflare.PublicUrl)
    }
  } else {
    Write-Warn "Cloudflare Tunnel no esta activo ahora mismo."
  }
  if ($cloudflare.BlockingReason -and -not $cloudflare.Ready) {
    Write-Warn $cloudflare.BlockingReason
  }
  if ($cloudflare.NextStep -and -not $cloudflare.Ready) {
    Write-Info $cloudflare.NextStep
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
    if ($tailscale.PublicUrl) {
      Write-Info ("Tailscale URL: " + $tailscale.PublicUrl)
    }
  } else {
    Write-Warn "Tailscale Funnel no esta activo ahora mismo."
  }
  if ($tailscale.BlockingReason -and -not $tailscale.Ready) {
    Write-Warn $tailscale.BlockingReason
  }
  if ($tailscale.NextStep -and -not $tailscale.Ready) {
    Write-Info $tailscale.NextStep
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
