. (Join-Path $PSScriptRoot "ops-common.ps1")

$paths = Get-PublicTunnelPaths
Write-Section "PUBLICO TEMPORAL STOP"
$state = Stop-ManagedProcess -PidFile $paths.PidFile

if ($state.IsRunning) {
  Write-Ok ("Tunel temporal detenido (PID $($state.ProcessId)).")
  exit 0
}

if ($state.HasPidFile) {
  Write-Warn "Habia un PID guardado obsoleto; se limpio el estado."
  exit 0
}

Write-Info "No habia tunel temporal activo."
exit 0
