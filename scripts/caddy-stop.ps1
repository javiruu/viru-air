. (Join-Path $PSScriptRoot "ops-common.ps1")

Write-Section "CADDY STOP"
$status = Get-CaddyRuntimeStatus

if (-not $status.Installed) {
  Write-Fail "caddy no esta instalado en esta maquina."
  exit 1
}

if (-not $status.HasPidFile) {
  Write-Info "Caddy aun no estaba arrancado desde este panel."
  exit 0
}

if (-not $status.Running) {
  $paths = Get-CaddyManagedPaths
  if (Test-Path $paths.PidFile) {
    Remove-Item $paths.PidFile -Force -ErrorAction SilentlyContinue
  }
  Write-Info "Caddy ya estaba parado; limpie el PID guardado."
  exit 0
}

try {
  $paths = Get-CaddyManagedPaths
  Stop-Process -Id $status.ProcessId -Force -ErrorAction Stop
  if (Test-Path $paths.PidFile) {
    Remove-Item $paths.PidFile -Force -ErrorAction SilentlyContinue
  }
  Write-Ok "Caddy detenido."
  exit 0
} catch {
  Write-Fail $_.Exception.Message
  exit 1
}
