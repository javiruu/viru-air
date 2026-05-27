param(
  [switch]$ShowTunnelWindow
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$logsDir = Join-Path $root "logs"
$pidFile = Join-Path $logsDir "cf_quick_tunnel.pid"
$outLog = Join-Path $logsDir "cf_quick_tunnel.out.log"
$errLog = Join-Path $logsDir "cf_quick_tunnel.err.log"

if (-not (Test-Path $logsDir)) {
  New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
}

function Stop-PreviousQuickTunnel {
  if (-not (Test-Path $pidFile)) { return }
  $raw = (Get-Content $pidFile -Raw -ErrorAction SilentlyContinue).Trim()
  $existing = 0
  [void][int]::TryParse($raw, [ref]$existing)
  if ($existing -gt 0) {
    $proc = Get-Process -Id $existing -ErrorAction SilentlyContinue
    if ($proc) {
      Stop-Process -Id $existing -Force -ErrorAction SilentlyContinue
      Start-Sleep -Milliseconds 300
    }
  }
  Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  VIRU PUBLICO RAPIDO (LAPTOP)"          -ForegroundColor Cyan
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
Write-Host "[2/3] Iniciando tunel HTTPS publico..." -ForegroundColor Yellow
$cf = Get-Command cloudflared -ErrorAction SilentlyContinue
$cloudflaredPath = $null
if ($cf) {
  $cloudflaredPath = $cf.Source
} else {
  $wingetCf = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like "Cloudflare.cloudflared*" } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  if ($wingetCf) {
    $candidate = Join-Path $wingetCf.FullName "cloudflared.exe"
    if (Test-Path $candidate) {
      $cloudflaredPath = $candidate
    }
  }
}
if (-not $cloudflaredPath) {
  throw "cloudflared no esta instalado. Instala con: winget install --id Cloudflare.cloudflared"
}

Stop-PreviousQuickTunnel
if (Test-Path $outLog) { Remove-Item $outLog -Force -ErrorAction SilentlyContinue }
if (Test-Path $errLog) { Remove-Item $errLog -Force -ErrorAction SilentlyContinue }

$windowStyle = if ($ShowTunnelWindow) { "Normal" } else { "Hidden" }
$proc = Start-Process -FilePath $cloudflaredPath `
  -ArgumentList @("tunnel", "--url", "http://localhost:3000") `
  -RedirectStandardOutput $outLog `
  -RedirectStandardError $errLog `
  -WindowStyle $windowStyle `
  -PassThru

Set-Content -Path $pidFile -Value $proc.Id -Encoding ASCII

Write-Host ""
Write-Host "[3/3] Esperando URL publica..." -ForegroundColor Yellow
$publicUrl = $null
for ($i = 0; $i -lt 40; $i++) {
  Start-Sleep -Milliseconds 500
  $line = @(
    Get-Content $outLog -ErrorAction SilentlyContinue
    Get-Content $errLog -ErrorAction SilentlyContinue
  ) | Where-Object { $_ -match "https://[-a-z0-9]+\.trycloudflare\.com" } |
    Select-Object -Last 1
  if ($line) {
    $m = [regex]::Match($line, "https://[-a-z0-9]+\.trycloudflare\.com")
    if ($m.Success) {
      $publicUrl = $m.Value
      break
    }
  }
}

if (-not $publicUrl) {
  Write-Host "No pude leer la URL aun. Revisa logs: $outLog" -ForegroundColor Yellow
  Write-Host "El tunel sigue iniciando. En 5-10s deberia aparecer la URL." -ForegroundColor Yellow
  exit 0
}

Write-Host ""
Write-Host "OK: VIRU publico activo" -ForegroundColor Green
Write-Host "Local:   http://localhost:3000" -ForegroundColor White
Write-Host "Publico: $publicUrl" -ForegroundColor Green
Write-Host ""
Write-Host "Para apagar el tunel rapido:" -ForegroundColor Gray
Write-Host "  powershell -ExecutionPolicy Bypass -Command `"if(Test-Path '$pidFile'){Stop-Process -Id [int](Get-Content '$pidFile') -Force; Remove-Item '$pidFile' -Force}`"" -ForegroundColor Gray
