. (Join-Path $PSScriptRoot "ops-common.ps1")

$ErrorActionPreference = "Stop"

Write-Section "DETENER CLOUDFLARE TUNNEL"

$result = Stop-CloudflareTunnel
if ($result.Stopped) {
  Write-Ok "Cloudflare Tunnel detenido."
  exit 0
}

Write-Info "Cloudflare Tunnel ya estaba parado."
exit 0
