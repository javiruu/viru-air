. (Join-Path $PSScriptRoot "ops-common.ps1")

Write-Section "Detener VIRU local"
$stopped = @()

foreach ($port in 3000, 8000) {
  $listeners = @(Get-PortListeners -Ports @($port) | Where-Object { $_.Listening })
  if ($listeners.Count -eq 0) {
    Write-Info "Puerto $port ya estaba libre."
    continue
  }

  foreach ($listener in $listeners) {
    try {
      Stop-Process -Id $listener.ProcessId -Force -ErrorAction Stop
      $stopped += $listener
      Write-Ok ("Detenido PID $($listener.ProcessId) ($($listener.ProcessName)) que escuchaba en $port.")
    } catch {
      Write-Fail ("No pude detener PID $($listener.ProcessId) en puerto $port: $($_.Exception.Message)")
      exit 1
    }
  }
}

if ($stopped.Count -eq 0) {
  Write-Info "No habia procesos locales en 3000/8000."
}

exit 0
