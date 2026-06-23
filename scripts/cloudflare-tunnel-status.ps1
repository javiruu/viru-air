. (Join-Path $PSScriptRoot "ops-common.ps1")

$ErrorActionPreference = "Stop"

Write-Section "ESTADO CLOUDFLARE TUNNEL"

$status = Get-CloudflareTunnelStatus

if (-not $status.Installed) {
  Write-Fail $status.BlockingReason
  if ($status.NextStep) {
    Write-Info $status.NextStep
  }
  exit 1
}

Write-Ok "Cloudflare instalado."
Write-Info ("Modo configurado: " + $status.Mode)

if ($status.Running) {
  Write-Ok "Proceso activo."
} else {
  Write-Warn "Proceso no activo."
}

if ($status.PublicUrl) {
  Write-Ok ("URL publica: " + $status.PublicUrl)
}

if ($status.BlockingReason -and -not $status.Ready) {
  Write-Warn $status.BlockingReason
}
if ($status.NextStep) {
  Write-Info $status.NextStep
}

if ($status.Ready) {
  exit 0
}
exit 1
