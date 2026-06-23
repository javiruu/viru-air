. (Join-Path $PSScriptRoot "ops-common.ps1")

$ErrorActionPreference = "Stop"

Write-Section "DETENER WEB PUBLICA"

$result = Stop-StableTunnel
if ($result.StoppedProviders -and $result.StoppedProviders.Count -gt 0) {
  Write-Ok ("Tuneles detenidos: " + ($result.StoppedProviders -join ", "))
  exit 0
}

Write-Info "No habia ningun tunel publico activo."
exit 0
