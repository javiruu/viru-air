. (Join-Path $PSScriptRoot "ops-common.ps1")

$ErrorActionPreference = "Stop"

Write-Section "DETENER WEB ESTABLE"

$result = Stop-StableTunnel
if ($result.StoppedProvider) {
  Write-Ok ("Tunel detenido: " + $result.StoppedProvider)
  exit 0
}

Write-Info "No habia ningun tunel estable activo."
exit 0
