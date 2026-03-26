param(
  [switch]$Foreground
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$runBackground = -not $Foreground
$backendPython = Join-Path $root "backend\.venv\Scripts\python.exe"

if (-not (Test-Path $backendPython)) {
  throw @"
No existe el entorno virtual del backend en: $backendPython
Inicializalo con Python 3.14:
  cd "$root\backend"
  py -3.14 -m venv .venv
  .\.venv\Scripts\python.exe -m pip install -e .[dev]
"@
}

$backendEnvFile = Join-Path $root "backend\.env"
$jwtSecret = $null

if (Test-Path $backendEnvFile) {
  foreach ($line in Get-Content $backendEnvFile) {
    if ($line -match "^\s*JWT_SECRET\s*=\s*(.+)\s*$") {
      $jwtSecret = $matches[1].Trim().Trim("'`"")
      break
    }
  }
}

if ([string]::IsNullOrWhiteSpace($jwtSecret) -or $jwtSecret -eq "change-me") {
  $bytes = New-Object byte[] 48
  $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  $rng.GetBytes($bytes)
  $rng.Dispose()
  $jwtSecret = [Convert]::ToBase64String($bytes).TrimEnd("=").Replace("+", "-").Replace("/", "_")

  $envContent = @"
DB_URL=sqlite:///./viru.db
JWT_SECRET=$jwtSecret
JWT_ALG=HS256
ACCESS_TOKEN_MINUTES=30
APP_ENV=local
"@
  Set-Content -Path $backendEnvFile -Value $envContent -Encoding UTF8
  Write-Host "Se genero backend/.env con un JWT_SECRET seguro para desarrollo local."
}

$env:JWT_SECRET = $jwtSecret

# Logs (timestamped, no overwrite)
$logsDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$backendLog = Join-Path $logsDir "backend-$ts.log"
$frontendLog = Join-Path $logsDir "frontend-$ts.log"

# Mata procesos previos en 3000/8000 para evitar conflictos
$ports = @(3000, 8000)
foreach ($p in $ports) {
  $conns = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
  foreach ($c in $conns) {
    try { Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue } catch {}
  }
}

if ($runBackground) {
  # Backend (modo background con logs)
  cmd /c "cd /d `"$root\backend`" && start /B `"`" `"$backendPython`" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload > `"$backendLog`" 2>&1" | Out-Null

  # Frontend (modo background con logs)
  cmd /c "cd /d `"$root\frontend`" && set NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1 && start /B npm run dev > `"$frontendLog`" 2>&1" | Out-Null
} else {
  # Backend (modo foreground en nueva ventana)
  $backendCmd = "title Viru Backend && cd /d `"$root\backend`" && `"$backendPython`" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
  Start-Process -FilePath "cmd.exe" -ArgumentList "/k", $backendCmd | Out-Null

  # Frontend (modo foreground en nueva ventana)
  $frontendCmd = "title Viru Frontend && cd /d `"$root\frontend`" && set NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1 && npm run dev"
  Start-Process -FilePath "cmd.exe" -ArgumentList "/k", $frontendCmd | Out-Null
}

Start-Sleep -Seconds 8

try {
  $api = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 10
  $web = Invoke-WebRequest -Uri "http://127.0.0.1:3000" -UseBasicParsing -TimeoutSec 10
  Write-Host "Backend:" $api.StatusCode
  Write-Host "Frontend:" $web.StatusCode
  Write-Host "Abre: http://localhost:3000"
} catch {
  Write-Host "Servicios arrancados, pero aun calentando. Abre: http://localhost:3000 en 10-20s"
}
