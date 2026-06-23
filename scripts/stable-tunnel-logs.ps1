. (Join-Path $PSScriptRoot "ops-common.ps1")

$ErrorActionPreference = "Stop"

Write-Section "LOGS DE TUNELES"

$stable = Get-StableTunnelStatus
$shown = $false

if ($stable.ActiveProvider -eq "cloudflare" -or -not $stable.ActiveProvider) {
  $cloudflarePaths = Get-CloudflareTunnelPaths
  if (Test-Path $cloudflarePaths.LogFile) {
    Write-Info ("Cloudflare log: " + $cloudflarePaths.LogFile)
    Get-Content -Tail 40 $cloudflarePaths.LogFile
    $shown = $true
  }
}

if ($stable.ActiveProvider -eq "tailscale" -or -not $stable.ActiveProvider) {
  $tailscalePaths = Get-TailscaleFunnelPaths
  if (Test-Path $tailscalePaths.LogFile) {
    if ($shown) {
      Write-Host ""
    }
    Write-Info ("Tailscale log: " + $tailscalePaths.LogFile)
    Get-Content -Tail 40 $tailscalePaths.LogFile
    $shown = $true
  }
}

if (-not $shown) {
  Write-Warn "Todavia no hay logs de tunel para mostrar."
  exit 1
}

exit 0
