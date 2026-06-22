param(
  [switch]$ShowTunnelWindow
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "ops-common.ps1")
$root = Get-RepoRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  VIRU PUBLICO TEMPORAL (LAPTOP)"        -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/3] Iniciando VIRU local..." -ForegroundColor Yellow
$bootstrap = Start-Process -FilePath "powershell.exe" `
  -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $root "iniciar_viru.ps1")
  ) `
  -WindowStyle Hidden `
  -PassThru

if (-not $bootstrap.WaitForExit(45000)) {
  Write-Host "El arranque local esta tardando mas de lo esperado; continuo con el tunel." -ForegroundColor Yellow
  Stop-Process -Id $bootstrap.Id -Force -ErrorAction SilentlyContinue
} elseif ($bootstrap.ExitCode -ne 0) {
  throw "No se pudo iniciar VIRU local (exit $($bootstrap.ExitCode))."
}

Write-Host ""
Write-Host "[2/3] Iniciando tunel HTTPS temporal..." -ForegroundColor Yellow
$ssh = Get-Command ssh -ErrorAction SilentlyContinue
if (-not $ssh) {
  throw "ssh no esta disponible en PATH. Instala OpenSSH Client para usar localhost.run."
}

& (Join-Path $PSScriptRoot "public-temp-start.ps1")
$startExit = $LASTEXITCODE
$paths = Get-PublicTunnelPaths
$publicUrl = Get-PublicTunnelUrl

if ($startExit -eq 0 -and $publicUrl) {
  Write-Host ""
  Write-Host "OK: VIRU publico temporal activo" -ForegroundColor Green
  Write-Host "Local:     http://localhost:3000" -ForegroundColor White
  Write-Host "Temporal:  $publicUrl" -ForegroundColor Green
  Write-Host ""
  Write-Host "Para apagar el tunel temporal usa la opcion PUBLICO TEMPORAL STOP del panel." -ForegroundColor Gray
  exit 0
}

Write-Host ""
Write-Host "El tunel sigue iniciando o necesita revision." -ForegroundColor Yellow
Write-Host "Revisa PUBLICO TEMPORAL STATUS o los logs en $($paths.OutLog)." -ForegroundColor Yellow
exit $startExit
