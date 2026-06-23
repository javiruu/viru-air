. (Join-Path $PSScriptRoot "ops-common.ps1")

$ErrorActionPreference = "Stop"

Write-Section "PUBLICAR WEB ESTABLE"

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

$stable = Get-StableTunnelStatus
if ($stable.ActiveProvider -and $stable.Ready -and $stable.PublicUrl) {
  Write-Ok ("La web estable ya esta activa con " + $stable.ActiveProvider + ": " + $stable.PublicUrl)
  exit 0
}

if ($stable.ActiveProvider -and -not $stable.Ready) {
  Write-Warn ("Habia un tunel " + $stable.ActiveProvider + " a medio arrancar. Voy a reiniciarlo.")
  Stop-StableTunnel | Out-Null
}

Write-Info "Intentando abrir la web estable con Cloudflare Tunnel..."
$cloudflare = Start-CloudflareTunnel
if ($cloudflare.Ready -and $cloudflare.PublicUrl) {
  Write-Ok ("Cloudflare Tunnel activo: " + $cloudflare.PublicUrl)
  if ($cloudflare.Mode -eq "quick") {
    Write-Info "Ahora mismo estas usando una URL temporal de Cloudflare. Si luego quieres un dominio propio, prepara un tunel named en infra/cloudflare-tunnel.local.yml."
  } else {
    Write-Info "Cloudflare Tunnel esta funcionando en modo dominio propio."
  }
  exit 0
}

$cloudflareReason = if ($cloudflare.BlockingReason) { $cloudflare.BlockingReason } else { "Cloudflare Tunnel no ha conseguido abrir una URL publica todavia." }
Write-Fail $cloudflareReason
if ($cloudflare.NextStep) {
  Write-Info $cloudflare.NextStep
}

$tailscale = Get-TailscaleFunnelStatus
if (-not $tailscale.Installed) {
  Write-Info "Alternativa disponible: instala Tailscale si quieres publicar la web estable por Funnel."
} else {
  Write-Info "Alternativa disponible: usa la opcion Tailscale Funnel del panel."
}
exit 1
