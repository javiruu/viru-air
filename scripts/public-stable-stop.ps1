. (Join-Path $PSScriptRoot "ops-common.ps1")

$ErrorActionPreference = "Stop"

Write-Section "DETENER WEB ESTABLE"

$status = Get-CaddyRuntimeStatus
$paths = Get-CaddyManagedPaths

if (-not $status.HasPidFile) {
  Write-Info "La web estable ya estaba apagada."
  exit 0
}

if (-not $status.Running) {
  if (Test-Path $paths.PidFile) {
    Remove-Item $paths.PidFile -Force -ErrorAction SilentlyContinue
  }
  Write-Info "La web estable ya estaba parada; he limpiado el PID guardado."
  exit 0
}

try {
  Stop-Process -Id $status.ProcessId -Force -ErrorAction Stop
  if (Test-Path $paths.PidFile) {
    Remove-Item $paths.PidFile -Force -ErrorAction SilentlyContinue
  }
  Write-Ok "Web estable detenida."
  exit 0
} catch {
  Write-Fail $_.Exception.Message
  exit 1
}
