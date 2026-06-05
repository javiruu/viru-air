param(
  [switch]$Foreground
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$runBackground = -not $Foreground
$backendPython = Join-Path $root "backend\.venv\Scripts\python.exe"
$backendAlembicIni = Join-Path $root "backend\alembic.ini"

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

function Set-ProcessEnvFromDotEnv {
  param(
    [string]$Path
  )

  if (-not (Test-Path $Path)) {
    return
  }

  foreach ($line in Get-Content $Path) {
    if ([string]::IsNullOrWhiteSpace($line)) {
      continue
    }
    if ($line.TrimStart().StartsWith("#")) {
      continue
    }
    $parts = $line -split "=", 2
    if ($parts.Count -ne 2) {
      continue
    }
    $key = $parts[0].Trim()
    if ([string]::IsNullOrWhiteSpace($key)) {
      continue
    }
    $value = $parts[1].Trim().Trim("'`"")
    Set-Item -Path "Env:$key" -Value $value
  }
}

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

Set-ProcessEnvFromDotEnv -Path $backendEnvFile
$env:JWT_SECRET = $jwtSecret

Write-Host "Validando cadena de migraciones Alembic..."
$auditRaw = (& $backendPython -m app.infrastructure.db.alembic_audit --json) -join "`n"
$auditExitCode = $LASTEXITCODE

if ([string]::IsNullOrWhiteSpace($auditRaw)) {
  throw "No se pudo obtener el diagnostico previo de Alembic."
}

try {
  $audit = $auditRaw | ConvertFrom-Json -ErrorAction Stop
} catch {
  throw "No se pudo interpretar el diagnostico previo de Alembic: $auditRaw"
}

if ($audit.untracked_migration_files.Count -gt 0) {
  Write-Host "Aviso: hay migraciones sin trackear en el repo:"
  $audit.untracked_migration_files | ForEach-Object { Write-Host " - $_" }
}

if ($auditExitCode -eq 3) {
  $missing = @($audit.missing_down_revisions)
  $duplicates = @($audit.duplicate_revisions.PSObject.Properties.Name)
  $missingFiles = @($audit.files_missing_identifiers)
  throw @"
Cadena de migraciones Alembic rota en el repo.
missing_down_revisions: $($missing -join ', ')
duplicate_revisions: $($duplicates -join ', ')
files_missing_identifiers: $($missingFiles -join ', ')
Revisa backend/alembic/versions antes de arrancar.
"@
}

if ($auditExitCode -eq 2) {
  $invalidRevisions = @($audit.db_state.invalid_revisions)
  throw @"
La base local tiene un alembic_version invalido para este repo.
Revision(es) huerfana(s): $($invalidRevisions -join ', ')
Esto suele significar que la DB local quedo apuntando a un ID antiguo o renombrado.
Recuperacion local sugerida:
  1. si no necesitas conservar datos, recrea backend/viru.db y vuelve a arrancar;
  2. si necesitas conservarlos, corrige alembic_version para que apunte a una revision existente y valida con:
     cd "$root\backend"
     .\.venv\Scripts\python.exe -m alembic current
"@
}

if ($auditExitCode -eq 4) {
  throw "No se pudo inspeccionar el estado de la base para Alembic: $($audit.db_state.error)"
}

if ($auditExitCode -ne 0) {
  throw "Fallo el diagnostico previo de Alembic (exit $auditExitCode)."
}

Write-Host "Aplicando migraciones del backend antes del arranque..."
$alembicArgs = @("-m", "alembic", "-c", $backendAlembicIni, "upgrade", "head")
$alembic = Start-Process -FilePath $backendPython `
  -ArgumentList $alembicArgs `
  -WorkingDirectory (Join-Path $root "backend") `
  -NoNewWindow `
  -Wait `
  -PassThru

if ($alembic.ExitCode -ne 0) {
  throw "Fallo al ejecutar migraciones Alembic (exit $($alembic.ExitCode))."
}

# Logs (timestamped, no overwrite)
$logsDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
$ts = Get-Date -Format "yyyyMMdd-HHmmss-fff"
$backendLog = Join-Path $logsDir "backend-$ts.log"
$frontendLog = Join-Path $logsDir "frontend-$ts.log"
$frontendBuildDir = Join-Path $root "frontend\.next"

# Mata procesos previos en 3000/8000 para evitar conflictos
$ports = @(3000, 8000)
foreach ($p in $ports) {
  $conns = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
  foreach ($c in $conns) {
    try { Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue } catch {}
  }
}

# Evita errores de chunks huérfanos de Next al reusar builds parciales.
if (Test-Path $frontendBuildDir) {
  Remove-Item -LiteralPath $frontendBuildDir -Recurse -Force -ErrorAction SilentlyContinue
}

if ($runBackground) {
  # Backend (modo background con logs)
  cmd /c "cd /d `"$root\backend`" && start /B `"`" `"$backendPython`" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload > `"$backendLog`" 2>&1" | Out-Null

  # Frontend (modo background con logs)
  cmd /c "cd /d `"$root\frontend`" && set NEXT_PUBLIC_API_URL=/api/v1 && start /B npm run dev > `"$frontendLog`" 2>&1" | Out-Null
} else {
  # Backend (modo foreground en nueva ventana)
  $backendCmd = "title Viru Backend && cd /d `"$root\backend`" && `"$backendPython`" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
  Start-Process -FilePath "cmd.exe" -ArgumentList "/k", $backendCmd | Out-Null

  # Frontend (modo foreground en nueva ventana)
  $frontendCmd = "title Viru Frontend && cd /d `"$root\frontend`" && set NEXT_PUBLIC_API_URL=/api/v1 && npm run dev"
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
