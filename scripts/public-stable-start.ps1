. (Join-Path $PSScriptRoot "ops-common.ps1")

$ErrorActionPreference = "Stop"

Write-Section "PUBLICAR WEB"

$local = Get-LocalAppStatus
if (-not $local.FrontendReady) {
  Write-Fail "El frontend local no esta activo en 3000."
}
if (-not $local.BackendReady) {
  Write-Fail "El backend local no esta activo en 8000."
}
if (-not $local.FrontendReady -or -not $local.BackendReady) {
  Write-Info "Siguiente paso: inicia VIRU localmente antes de abrir la web publica."
  exit 1
}

Write-Ok "Frontend local activo en 3000."
Write-Ok "Backend local activo en 8000."

$cloudflareInstall = Ensure-CloudflaredInstalled
if ($cloudflareInstall.Changed) {
  Write-Ok $cloudflareInstall.Message
} elseif ($cloudflareInstall.Installed) {
  Write-Info "Cloudflare Tunnel disponible."
} else {
  Write-Warn $cloudflareInstall.Message
}

$tailscaleInstall = Ensure-TailscaleInstalled
if ($tailscaleInstall.Changed) {
  Write-Ok $tailscaleInstall.Message
} elseif ($tailscaleInstall.Installed) {
  Write-Info "Tailscale disponible."
} else {
  Write-Warn $tailscaleInstall.Message
}

$stable = Get-StableTunnelStatus
if ($stable.Ready -and $stable.ReadyProviders.Count -ge 2) {
  Write-Ok "La web ya estaba publicada por Cloudflare y Tailscale."
  foreach ($url in $stable.PublicUrls) {
    Write-Ok ("URL publica: " + $url)
  }
  exit 0
}

if ($stable.ActiveProvider -and -not $stable.Ready) {
  Write-Warn ("Habia tuneles a medio arrancar (" + $stable.ActiveProvider + "). Voy a reiniciarlos.")
  Stop-StableTunnel | Out-Null
}

$cloudflare = $null
$tailscale = $null
$readyUrls = @()
$readyProviders = @()

if ($cloudflareInstall.Installed) {
  Write-Info "Intentando abrir Cloudflare Tunnel..."
  $cloudflare = Start-CloudflareTunnel
  if ($cloudflare.Ready -and $cloudflare.PublicUrl) {
    Write-Ok ("Cloudflare Tunnel activo: " + $cloudflare.PublicUrl)
    if ($cloudflare.Version) {
      Write-Info ("Version: " + $cloudflare.Version)
    }
    if ($cloudflare.Mode -eq "quick") {
      Write-Info "Cloudflare esta en modo quick tunnel."
    } else {
      Write-Info "Cloudflare esta usando tu configuracion de dominio propio."
    }
    $readyUrls += $cloudflare.PublicUrl
    $readyProviders += "cloudflare"
  } else {
    $cloudflareReason = if ($cloudflare.BlockingReason) { $cloudflare.BlockingReason } else { "Cloudflare Tunnel no ha conseguido abrir una URL publica todavia." }
    Write-Warn $cloudflareReason
    if ($cloudflare.NextStep) {
      Write-Info $cloudflare.NextStep
    }
  }
}

if ($tailscaleInstall.Installed) {
  Write-Info "Intentando abrir Tailscale Funnel..."
  $tailscale = Start-TailscaleFunnel
  if ($tailscale.Ready -and $tailscale.PublicUrl) {
    Write-Ok ("Tailscale Funnel activo: " + $tailscale.PublicUrl)
    if ($tailscale.Version) {
      Write-Info ("Version: " + $tailscale.Version)
    }
    $readyUrls += $tailscale.PublicUrl
    $readyProviders += "tailscale"
  } else {
    $tailscaleReason = if ($tailscale.BlockingReason) { $tailscale.BlockingReason } else { "Tailscale Funnel no ha conseguido abrir una URL publica todavia." }
    Write-Warn $tailscaleReason
    if ($tailscale.NextStep) {
      Write-Info $tailscale.NextStep
    }
  }
}

$readyUrls = @($readyUrls | Where-Object { $_ } | Select-Object -Unique)
$readyProviders = @($readyProviders | Where-Object { $_ } | Select-Object -Unique)

if ($readyUrls.Count -gt 0) {
  Write-Host ""
  Write-Ok "URLs publicas disponibles:"
  foreach ($url in $readyUrls) {
    Write-Ok ("  " + $url)
  }
  Write-Info "Puedes abrir cualquiera de esas URLs para entrar a la web."
  Write-StableTunnelState -State ([pscustomobject]@{
    Provider = "combined"
    StartedAt = (Get-Date).ToString("s")
    Providers = $readyProviders
    PublicUrls = $readyUrls
  }) | Out-Null
  exit 0
}

Write-Fail "No he conseguido abrir ninguna URL publica en este intento."
if (-not $cloudflareInstall.Installed -and -not $tailscaleInstall.Installed) {
  Write-Info "Siguiente paso: instala cloudflared o Tailscale para poder publicar la web."
}
exit 1
