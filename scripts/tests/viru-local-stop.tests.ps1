$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "..\viru-local-stop.ps1")

$closedProcessIds = [System.Collections.Generic.List[int]]::new()

function Get-CimInstance {
  param([string]$ClassName, [string]$Filter)

  if ($Filter -eq "ParentProcessId = 200") {
    return @([pscustomobject]@{ ProcessId = 201; CommandLine = $null })
  }

  if ($Filter -eq "ParentProcessId = 201") {
    return @()
  }

  return @(
    [pscustomobject]@{ ProcessId = 101; CommandLine = "cmd.exe /k title Viru Backend && python -m uvicorn" },
    [pscustomobject]@{ ProcessId = 102; CommandLine = "cmd.exe /k title Viru Frontend && npm run dev" },
    [pscustomobject]@{ ProcessId = 103; CommandLine = "cmd.exe /k title Una consola ajena" }
  )
}

function Stop-Process {
  param([int]$Id)

  $closedProcessIds.Add($Id)
}

function Get-Process {
  param([int]$Id)

  return [pscustomobject]@{ Id = $Id }
}

Stop-ViruConsoleWindows

if (@($closedProcessIds).Count -ne 2 -or $closedProcessIds -notcontains 101 -or $closedProcessIds -notcontains 102) {
  throw "Expected only the Viru Backend and Viru Frontend console processes to be closed."
}

if ($closedProcessIds -contains 103) {
  throw "A non-Viru console must not be closed."
}

Stop-ViruProcessTree -ProcessId 200

if (@($closedProcessIds).Count -ne 4 -or $closedProcessIds[2] -ne 201 -or $closedProcessIds[3] -ne 200) {
  throw "Expected the listener process tree to stop from child to parent."
}

Write-Host "PASS: local stop closes only the VIRU console windows and their listener trees."
