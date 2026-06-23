. (Join-Path $PSScriptRoot "ops-common.ps1")

$ErrorActionPreference = "Stop"

Write-Section "DETENER TAILSCALE FUNNEL"

$result = Stop-TailscaleFunnel
if ($result.Stopped) {
  Write-Ok "Tailscale Funnel detenido."
  exit 0
}

Write-Info "Tailscale Funnel ya estaba parado."
exit 0
