. (Join-Path $PSScriptRoot "ops-common.ps1")

$ports = Get-PortListeners -Ports @(3000, 8000)
Write-Section "Estado local de VIRU"

$frontend = @($ports | Where-Object { $_.Port -eq 3000 -and $_.Listening })
$backend = @($ports | Where-Object { $_.Port -eq 8000 -and $_.Listening })

if ($frontend.Count -gt 0) {
  foreach ($item in $frontend) {
    Write-Ok ("Frontend en 3000 activo (PID $($item.ProcessId), $($item.ProcessName)).")
  }
} else {
  Write-Warn "Frontend en 3000 no esta escuchando."
}

if ($backend.Count -gt 0) {
  foreach ($item in $backend) {
    Write-Ok ("Backend en 8000 activo (PID $($item.ProcessId), $($item.ProcessName)).")
  }
} else {
  Write-Warn "Backend en 8000 no esta escuchando."
}

if ($frontend.Count -gt 0 -and $backend.Count -gt 0) {
  Write-Info "URLs esperadas:"
  Write-Info "  http://localhost:3000"
  Write-Info "  http://localhost:8000/health"
  exit 0
}

exit 1
