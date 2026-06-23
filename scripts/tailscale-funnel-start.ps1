. (Join-Path $PSScriptRoot "ops-common.ps1")

$ErrorActionPreference = "Stop"

Write-Section "TAILSCALE FUNNEL"

$local = Get-LocalAppStatus
if (-not $local.FrontendReady -or -not $local.BackendReady) {
  if (-not $local.FrontendReady) {
    Write-Fail "El frontend local no esta activo en 3000."
  }
  if (-not $local.BackendReady) {
    Write-Fail "El backend local no esta activo en 8000."
  }
  Write-Info "Siguiente paso: inicia VIRU localmente y vuelve a intentarlo."
  exit 1
}

$result = Start-TailscaleFunnel
if ($result.Ready) {
  Write-Ok ("Tailscale Funnel activo: " + $result.PublicUrl)
  exit 0
}

$reason = if ($result.BlockingReason) { $result.BlockingReason } else { "Tailscale Funnel no ha conseguido abrir una URL publica todavia." }
Write-Fail $reason
if ($result.NextStep) {
  Write-Info $result.NextStep
}
exit 1
