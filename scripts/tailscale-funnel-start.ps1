. (Join-Path $PSScriptRoot "ops-common.ps1")

$ErrorActionPreference = "Stop"

Write-Section "TAILSCALE FUNNEL"

$install = Ensure-TailscaleInstalled
if ($install.Changed) {
  Write-Ok $install.Message
} elseif (-not $install.Installed) {
  Write-Fail $install.Message
  exit 1
}

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
  $versionText = if ($result.Version) { $result.Version } else { "desconocida" }
  Write-Info ("Version: " + $versionText)
  exit 0
}

$reason = if ($result.BlockingReason) { $result.BlockingReason } else { "Tailscale Funnel no ha conseguido abrir una URL publica todavia." }
Write-Fail $reason
if ($result.NextStep) {
  Write-Info $result.NextStep
}
exit 1
