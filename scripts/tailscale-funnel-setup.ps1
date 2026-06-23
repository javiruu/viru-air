param(
  [switch]$InstallIfMissing
)

. (Join-Path $PSScriptRoot "ops-common.ps1")

$ErrorActionPreference = "Stop"

Write-Section "SETUP TAILSCALE FUNNEL"

if ($InstallIfMissing) {
  $install = Ensure-TailscaleInstalled
  if ($install.Changed) {
    Write-Ok $install.Message
  } elseif (-not $install.Installed) {
    Write-Fail $install.Message
    exit 1
  } else {
    Write-Info $install.Message
  }
}

$status = Get-TailscaleFunnelStatus
if (-not $status.Installed) {
  Write-Fail "Tailscale no esta instalado en este equipo."
  Write-Info "Siguiente paso: vuelve a ejecutar este script con -InstallIfMissing o instala Tailscale manualmente."
  exit 1
}

$versionText = if ($status.Version) { $status.Version } else { "desconocida" }
Write-Info ("Version: " + $versionText)

if ($status.BackendState) {
  Write-Info ("Backend state: " + $status.BackendState)
}

if ($status.DnsName) {
  Write-Info ("DNS name: " + $status.DnsName)
}

if ($status.PublicUrl) {
  Write-Ok ("URL publica actual: " + $status.PublicUrl)
}

if ($status.BlockingReason) {
  Write-Warn $status.BlockingReason
}
if ($status.NextStep) {
  Write-Info $status.NextStep
}

if ($status.Ready) {
  Write-Ok "Tailscale Funnel ya esta listo para usar."
  exit 0
}

Write-Warn "Tailscale necesita al menos login y activacion de Funnel para quedar completo."
exit 1
