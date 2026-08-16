. (Join-Path $PSScriptRoot "ops-common.ps1")

function Stop-ViruConsoleWindows {
  $viruConsoles = @(Get-CimInstance Win32_Process -Filter "Name = 'cmd.exe'" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -match "(?i)\btitle\s+Viru\s+(Backend|Frontend)\b"
  })

  foreach ($console in $viruConsoles) {
    try {
      Stop-Process -Id $console.ProcessId -Force -ErrorAction Stop
      Write-Ok ("Cerrada consola de VIRU (PID $($console.ProcessId)).")
    } catch {
      Write-Fail ("No pude cerrar la consola de VIRU (PID $($console.ProcessId)): $($_.Exception.Message)")
      exit 1
    }
  }
}

function Stop-ViruProcessTree {
  param([Parameter(Mandatory)][int]$ProcessId)

  $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId = $ProcessId" -ErrorAction SilentlyContinue)
  foreach ($child in $children) {
    Stop-ViruProcessTree -ProcessId $child.ProcessId
  }

  $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
  if ($process) {
    Stop-Process -Id $ProcessId -Force -ErrorAction Stop
  }
}

function Stop-ViruLocal {
  Write-Section "Detener VIRU local"
  $stopped = @()

  Stop-ViruConsoleWindows

  foreach ($port in 3000, 8000) {
    $listeners = @(Get-PortListeners -Ports @($port) | Where-Object { $_.Listening })
    if ($listeners.Count -eq 0) {
      Write-Info "Puerto $port ya estaba libre."
      continue
    }

    foreach ($listener in $listeners) {
      try {
        Stop-ViruProcessTree -ProcessId $listener.ProcessId
        $stopped += $listener
        Write-Ok ("Detenido PID $($listener.ProcessId) ($($listener.ProcessName)) que escuchaba en $port.")
      } catch {
        Write-Fail ("No pude detener PID $($listener.ProcessId) en puerto ${port}: $($_.Exception.Message)")
        exit 1
      }
    }
  }

  if ($stopped.Count -eq 0) {
    Write-Info "No habia procesos locales en 3000/8000."
  }
}

if ($MyInvocation.InvocationName -ne ".") {
  Stop-ViruLocal
  exit 0
}
