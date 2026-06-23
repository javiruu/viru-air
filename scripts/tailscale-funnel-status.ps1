. (Join-Path $PSScriptRoot "ops-common.ps1")

$ErrorActionPreference = "Stop"

Write-Section "ESTADO TAILSCALE FUNNEL"

$status = Get-TailscaleFunnelStatus

if (-not $status.Installed) {
  Write-Fail $status.BlockingReason
  if ($status.NextStep) {
    Write-Info $status.NextStep
  }
  exit 1
}

Write-Ok "Tailscale instalado."

if ($status.Running) {
  Write-Ok "Funnel activo."
} else {
  Write-Warn "Funnel no activo."
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
