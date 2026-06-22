. (Join-Path $PSScriptRoot "ops-common.ps1")

$paths = Get-PublicTunnelPaths
$state = Get-ManagedProcessState -PidFile $paths.PidFile -Label "Tunel temporal"

Write-Section "PUBLICO TEMPORAL STATUS"

if (-not $state.HasPidFile) {
  Write-Warn "No hay tunel temporal activo."
  exit 1
}

if (-not $state.IsRunning) {
  Write-Warn "El PID guardado ya no corresponde a un proceso activo."
  Write-Info "Puedes volver a lanzar PUBLICO TEMPORAL START."
  exit 1
}

Write-Ok ("Tunel temporal activo (PID $($state.ProcessId), $($state.ProcessName)).")
$publicUrl = Get-PublicTunnelUrl
if ($publicUrl) {
  Write-Ok ("URL temporal: $publicUrl")
  exit 0
}

Write-Warn "El proceso sigue vivo, pero la URL aun no aparece en logs."
Write-Info "Revisa los logs o espera unos segundos."
exit 2
