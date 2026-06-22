. (Join-Path $PSScriptRoot "ops-common.ps1")

$paths = Get-PublicTunnelPaths
$state = Get-ManagedProcessState -PidFile $paths.PidFile -Label "Tunel temporal"

Write-Section "PUBLICO TEMPORAL START"

if (-not (Test-CommandAvailable -CommandName "ssh")) {
  Write-Fail "ssh no esta disponible en PATH. Instala OpenSSH Client para usar localhost.run."
  exit 1
}

if ($state.IsRunning) {
  Write-Warn ("Ya existe un tunel temporal activo (PID $($state.ProcessId)).")
  $currentUrl = Get-PublicTunnelUrl
  if ($currentUrl) {
    Write-Ok ("URL temporal: $currentUrl")
  } else {
    Write-Warn "El tunel sigue levantandose; usa PUBLICO TEMPORAL STATUS en unos segundos."
  }
  exit 0
}

if ($state.HasPidFile) {
  Remove-Item $paths.PidFile -Force -ErrorAction SilentlyContinue
  Write-Warn "Habia un PID guardado obsoleto; lo limpie antes de reintentar."
}

if (Test-Path $paths.OutLog) { Remove-Item $paths.OutLog -Force -ErrorAction SilentlyContinue }
if (Test-Path $paths.ErrLog) { Remove-Item $paths.ErrLog -Force -ErrorAction SilentlyContinue }

$ssh = Get-Command ssh -ErrorAction SilentlyContinue
$proc = Start-Process -FilePath $ssh.Source `
  -ArgumentList @(
    "-o", "StrictHostKeyChecking=no",
    "-o", "ServerAliveInterval=30",
    "-R", "80:127.0.0.1:3000",
    "nokey@localhost.run"
  ) `
  -RedirectStandardOutput $paths.OutLog `
  -RedirectStandardError $paths.ErrLog `
  -WindowStyle Hidden `
  -PassThru

Set-Content -Path $paths.PidFile -Value $proc.Id -Encoding ASCII
Write-Info ("Tunel lanzado en background (PID $($proc.Id)). Esperando URL...")

$publicUrl = $null
for ($i = 0; $i -lt 40; $i++) {
  Start-Sleep -Milliseconds 500
  $publicUrl = Get-PublicTunnelUrl
  if ($publicUrl) {
    break
  }
}

if ($publicUrl) {
  Write-Ok ("URL temporal: $publicUrl")
  exit 0
}

Write-Warn "El tunel sigue arrancando y aun no dejo URL en logs."
Write-Info "Usa PUBLICO TEMPORAL STATUS o revisa los logs del tunel."
exit 2
