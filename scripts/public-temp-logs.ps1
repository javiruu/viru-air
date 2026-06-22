. (Join-Path $PSScriptRoot "ops-common.ps1")

$paths = Get-PublicTunnelPaths
Write-Section "PUBLICO TEMPORAL LOGS"

Write-Info "--- public_temp_tunnel.out.log ---"
if (Test-Path $paths.OutLog) {
  Get-Content -Path $paths.OutLog -Tail 80
} else {
  Write-Warn "No existe aun el log de salida."
}

Write-Info "--- public_temp_tunnel.err.log ---"
if (Test-Path $paths.ErrLog) {
  Get-Content -Path $paths.ErrLog -Tail 80
} else {
  Write-Warn "No existe aun el log de error."
}
