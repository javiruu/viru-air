. (Join-Path $PSScriptRoot "ops-common.ps1")

$ErrorActionPreference = "Stop"

Write-Section "CLOUDFLARE TUNNEL"

$install = Ensure-CloudflaredInstalled
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

$result = Start-CloudflareTunnel
if ($result.Ready) {
  Write-Ok ("Cloudflare Tunnel activo: " + $result.PublicUrl)
  $versionText = if ($result.Version) { $result.Version } else { "desconocida" }
  Write-Info ("Version: " + $versionText)
  if ($result.Mode -eq "quick") {
    Write-Info "Modo actual: quick tunnel de Cloudflare."
  } else {
    Write-Info "Modo actual: tunel named con dominio propio."
  }
  exit 0
}

$reason = if ($result.BlockingReason) { $result.BlockingReason } else { "Cloudflare Tunnel no ha conseguido abrir una URL publica todavia." }
Write-Fail $reason
if ($result.NextStep) {
  Write-Info $result.NextStep
}
exit 1
