param(
  [switch]$Foreground
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$runBackground = -not $Foreground
$backendDir = Join-Path $root "backend"
$backendPython = Join-Path $root "backend\.venv\Scripts\python.exe"
$backendAlembicIni = Join-Path $root "backend\alembic.ini"
$backendDbPath = Join-Path $backendDir "viru.db"
$backendDbUrl = "sqlite:///$($backendDbPath.Replace('\', '/'))"

function Invoke-PythonCommand {
  param(
    [Parameter(Mandatory)]
    [pscustomobject]$Candidate,
    [Parameter(Mandatory)]
    [string[]]$Arguments,
    [switch]$CaptureOutput,
    [switch]$AllowFailure,
    [string]$WorkingDirectory = $root
  )

  $allArgs = @($Candidate.PrefixArgs) + $Arguments
  if ($CaptureOutput) {
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    Push-Location $WorkingDirectory
    try {
      $output = & $Candidate.FilePath @allArgs 2>&1
      $exitCode = $LASTEXITCODE
    } finally {
      Pop-Location
      $ErrorActionPreference = $previousErrorActionPreference
    }
    if (-not $AllowFailure -and $exitCode -ne 0) {
      throw "Fallo al ejecutar $($Candidate.DisplayName) (exit $exitCode)."
    }
    return [pscustomobject]@{
      Output = @($output)
      ExitCode = $exitCode
    }
  }

  $process = Start-Process -FilePath $Candidate.FilePath `
    -ArgumentList $allArgs `
    -WorkingDirectory $WorkingDirectory `
    -NoNewWindow `
    -Wait `
    -PassThru

  if (-not $AllowFailure -and $process.ExitCode -ne 0) {
    throw "Fallo al ejecutar $($Candidate.DisplayName) (exit $($process.ExitCode))."
  }

  return $process.ExitCode
}

function Get-PythonVersionInfo {
  param(
    [Parameter(Mandatory)]
    [pscustomobject]$Candidate
  )

  $result = Invoke-PythonCommand -Candidate $Candidate `
    -Arguments @("-c", "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}')") `
    -CaptureOutput `
    -AllowFailure

  if ($result.ExitCode -ne 0 -or $result.Output.Count -eq 0) {
    return $null
  }

  $rawVersion = ($result.Output[-1].ToString()).Trim()
  try {
    $version = [version]$rawVersion
  } catch {
    return $null
  }

  return [pscustomobject]@{
    Version = $version
    RawVersion = $rawVersion
  }
}

function Get-AvailablePythonCandidates {
  $candidates = @()
  $repoPython = Join-Path $root "Python\pythoncore-3.14-64\python.exe"
  if (Test-Path $repoPython) {
    $candidates += [pscustomobject]@{
      DisplayName = "Python 3.14 embebido del repo"
      FilePath = $repoPython
      PrefixArgs = @()
    }
  }

  if (Get-Command py -ErrorAction SilentlyContinue) {
    $candidates += [pscustomobject]@{
      DisplayName = "Python Launcher py -3.14"
      FilePath = "py"
      PrefixArgs = @("-3.14")
    }
    $candidates += [pscustomobject]@{
      DisplayName = "Python Launcher py -3.13"
      FilePath = "py"
      PrefixArgs = @("-3.13")
    }
    $candidates += [pscustomobject]@{
      DisplayName = "Python Launcher py -3.12"
      FilePath = "py"
      PrefixArgs = @("-3.12")
    }
  }

  if (Get-Command python -ErrorAction SilentlyContinue) {
    $candidates += [pscustomobject]@{
      DisplayName = "python en PATH"
      FilePath = "python"
      PrefixArgs = @()
    }
  }

  return $candidates
}

function Resolve-BackendBootstrapPython {
  $minimumVersion = [version]"3.12.0"

  foreach ($candidate in Get-AvailablePythonCandidates) {
    $versionInfo = Get-PythonVersionInfo -Candidate $candidate
    if ($null -eq $versionInfo) {
      continue
    }

    if ($versionInfo.Version -ge $minimumVersion) {
      return [pscustomobject]@{
        Candidate = $candidate
        Version = $versionInfo.Version
        RawVersion = $versionInfo.RawVersion
      }
    }
  }

  return $null
}

function Test-FrontendTooling {
  $nodeOk = Get-Command node -ErrorAction SilentlyContinue
  $npmOk = Get-Command npm -ErrorAction SilentlyContinue

  if (-not $nodeOk) {
    throw @"
No se encontro Node.js en el PATH.
Es necesario para arrancar el frontend de VIRU.
Instalacion sugerida: https://nodejs.org/
"@
  }

  if (-not $npmOk) {
    throw @"
No se encontro npm en el PATH.
npm deberia venir con Node.js. Revisa tu instalacion.
"@
  }

  try {
    $nodeVersion = & node --version 2>&1 | ForEach-Object { $_.ToString().Trim() } | Select-Object -Last 1
    $npmVersion = & npm --version 2>&1 | ForEach-Object { $_.ToString().Trim() } | Select-Object -Last 1
  } catch {
    $nodeVersion = "desconocida"
    $npmVersion = "desconocida"
  }

  $frontendNodeModules = Join-Path $root "frontend\node_modules"
  if (-not (Test-Path $frontendNodeModules)) {
    Write-Host "No se encontraron dependencias del frontend (frontend/node_modules)."
    Write-Host "Ejecutando npm install en frontend/..."
    Push-Location (Join-Path $root "frontend")
    try {
      & npm install 2>&1 | Out-Host
      if ($LASTEXITCODE -ne 0) {
        throw "npm install fallo con exit code $LASTEXITCODE."
      }
    } finally {
      Pop-Location
    }
    Write-Host "Dependencias del frontend instaladas correctamente."
  }

  Write-Host "Frontend tooling: node $nodeVersion, npm $npmVersion"
}

function Read-YesNoPrompt {
  param(
    [Parameter(Mandatory)]
    [string]$Prompt
  )

  while ($true) {
    $answer = (Read-Host $Prompt).Trim().ToUpperInvariant()
    if ($answer -eq "S") {
      return $true
    }
    if ($answer -eq "N") {
      return $false
    }
    Write-Host "Respuesta no valida. Escribe S o N."
  }
}

function Test-VenvPythonRunnable {
  <#
    .SYNOPSIS
    Verifica que el Python del entorno virtual realmente ejecuta codigo.
    Test-Path no basta: el binario puede existir pero estar corrupto.
  #>
  if (-not (Test-Path $backendPython)) {
    return $false
  }

  try {
    $result = & $backendPython -c "import sys; print(sys.version_info[0])" 2>&1
    if ($LASTEXITCODE -ne 0) {
      return $false
    }
    $line = ($result | Select-Object -Last 1).ToString().Trim()
    return [int]::TryParse($line, [ref]$null)
  } catch {
    return $false
  }
}

function Ensure-VenvPythonRunnable {
  <#
    .SYNOPSIS
    Si el venv Python existe pero no funciona, ofrece reconstruirlo.
  #>
  if (Test-VenvPythonRunnable) {
    return
  }

  Write-Host ""
  Write-Host "ATENCION: El Python del entorno virtual esta presente pero no funciona." -ForegroundColor Yellow
  Write-Host "  $backendPython" -ForegroundColor Gray
  Write-Host ""
  Write-Host "Esto suele ocurrir cuando:"
  Write-Host "  - El entorno virtual quedo incompleto (pip install interrumpido)"
  Write-Host "  - Se movio o elimino el Python base que se uso para crearlo"
  Write-Host "  - El binario python.exe esta corrupto"
  Write-Host ""

  if (-not (Read-YesNoPrompt -Prompt "Quieres que VIRU elimine y regenere el entorno virtual? [S/N]")) {
    throw @"
No se puede continuar sin un Python funcional en el entorno virtual.
Recuperacion manual:
  rmdir /s "$backendDir\.venv"
  cd "$backendDir"
  py -3.14 -m venv .venv
  .\.venv\Scripts\python.exe -m pip install -e .[dev]
"@
  }

  Write-Host "Eliminando entorno virtual corrupto..."
  Remove-Item -LiteralPath (Join-Path $backendDir ".venv") -Recurse -Force -ErrorAction SilentlyContinue

  # Forzar recreacion: borrar cualquier marcador de que existe
  Ensure-BackendVirtualEnv

  Write-Host "Verificando que el nuevo entorno virtual funciona..."
  if (-not (Test-VenvPythonRunnable)) {
    throw @"
No se pudo recrear el entorno virtual automaticamente.
Prueba la recuperacion manual:
  rmdir /s "$backendDir\.venv"
  cd "$backendDir"
  py -3.14 -m venv .venv
  .\.venv\Scripts\python.exe -m pip install -e .[dev]
"@
  }

  Write-Host "Entorno virtual regenerado correctamente." -ForegroundColor Green
}

function Stop-ProcessTree {
  param(
    [Parameter(Mandatory)]
    [int]$ProcessId
  )

  $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $ProcessId" -ErrorAction SilentlyContinue
  foreach ($child in @($children)) {
    Stop-ProcessTree -ProcessId $child.ProcessId
  }

  try {
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
  } catch {}
}

function Wait-HttpOk {
  param(
    [Parameter(Mandatory)]
    [string]$Url,
    [int]$Attempts = 20,
    [int]$DelaySeconds = 1
  )

  for ($i = 0; $i -lt $Attempts; $i++) {
    try {
      $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
      if ($response.StatusCode -eq 200) {
        return $response
      }
    } catch {}
    Start-Sleep -Seconds $DelaySeconds
  }

  throw "Healthcheck fallido para $Url"
}

function Ensure-BackendVirtualEnv {
  if (Test-Path $backendPython) {
    return
  }

  $bootstrap = Resolve-BackendBootstrapPython
  if ($null -eq $bootstrap) {
    throw @"
No existe el entorno virtual del backend en: $backendPython
Y no se encontro un Python compatible (>=3.12) para crearlo automaticamente.
Opciones sugeridas:
  1. instala Python 3.14 o 3.12;
  2. o usa el runtime embebido del repo en $root\Python\pythoncore-3.14-64\python.exe;
  3. luego ejecuta manualmente:
     cd "$backendDir"
     py -3.14 -m venv .venv
     .\.venv\Scripts\python.exe -m pip install -e .[dev]
"@
  }

  Write-Host "No existe el entorno virtual del backend en: $backendPython"
  Write-Host "Se puede reparar automaticamente con: $($bootstrap.Candidate.DisplayName) ($($bootstrap.RawVersion))"
  Write-Host "Acciones:"
  Write-Host "  1. crear backend/.venv"
  Write-Host "  2. instalar dependencias del backend con -e .[dev]"

  if (-not (Read-YesNoPrompt -Prompt "Quieres que VIRU lo repare ahora? [S/N]")) {
    throw @"
Arranque cancelado por el usuario.
Recuperacion manual:
  cd "$backendDir"
  py -3.14 -m venv .venv
  .\.venv\Scripts\python.exe -m pip install -e .[dev]
"@
  }

  Write-Host "Creando backend/.venv con $($bootstrap.Candidate.DisplayName) ($($bootstrap.RawVersion))..."
  Invoke-PythonCommand -Candidate $bootstrap.Candidate -Arguments @("-m", "venv", ".venv") -WorkingDirectory $backendDir | Out-Null

  if (-not (Test-Path $backendPython)) {
    throw @"
La creacion del entorno virtual finalizo, pero no aparecio: $backendPython
Recuperacion manual sugerida:
  cd "$backendDir"
  py -3.14 -m venv .venv
"@
  }

  Write-Host "Instalando dependencias del backend en el entorno virtual..."
  $venvPython = [pscustomobject]@{
    DisplayName = "backend\\.venv\\Scripts\\python.exe"
    FilePath = $backendPython
    PrefixArgs = @()
  }
  Invoke-PythonCommand -Candidate $venvPython -Arguments @("-m", "pip", "install", "-e", ".[dev]") -WorkingDirectory $backendDir | Out-Null

  if (-not (Test-Path $backendPython)) {
    throw @"
Se completo el bootstrap, pero el Python del entorno virtual sigue sin estar disponible en:
$backendPython
Recuperacion manual sugerida:
  cd "$backendDir"
  .\.venv\Scripts\python.exe -m pip install -e .[dev]
"@
  }

  Write-Host "Entorno virtual del backend reparado correctamente."
}

function Install-BackendDependencies {
  Write-Host "Reparando dependencias del backend en el entorno virtual..."
  $venvPython = [pscustomobject]@{
    DisplayName = "backend\\.venv\\Scripts\\python.exe"
    FilePath = $backendPython
    PrefixArgs = @()
  }

  $repair = Invoke-PythonCommand -Candidate $venvPython `
    -Arguments @("-m", "pip", "install", "--upgrade", "--force-reinstall", "-e", ".[dev]") `
    -WorkingDirectory $backendDir `
    -CaptureOutput `
    -AllowFailure

  if ($repair.ExitCode -ne 0) {
    $repairOutput = ($repair.Output | ForEach-Object { $_.ToString() }) -join "`n"
    if ($repairOutput -notmatch "(?i)(uninstall-no-record-file|RECORD file)") {
      throw "No se pudieron reparar las dependencias del backend. Detalle: $repairOutput"
    }

    Write-Host "Pip no pudo desinstalar una dependencia corrupta; reinstalando por encima con --ignore-installed." -ForegroundColor Yellow
    Invoke-PythonCommand -Candidate $venvPython `
      -Arguments @("-m", "pip", "install", "--ignore-installed", "-e", ".[dev]") `
      -WorkingDirectory $backendDir | Out-Null
  }

  Write-Host "Dependencias del backend reparadas correctamente."
}

function Invoke-AlembicAudit {
  Push-Location $backendDir
  try {
    $output = @(& $backendPython -m app.infrastructure.db.alembic_audit --json 2>&1)
    $exitCode = $LASTEXITCODE
  } catch {
    $output = @($_.Exception.Message)
    $exitCode = 999
  } finally {
    Pop-Location
  }

  $lines = @($output | ForEach-Object { $_.ToString() })
  $jsonLine = $null
  foreach ($line in $lines) {
    $trimmed = $line.TrimStart()
    if ($trimmed.StartsWith("{")) {
      $jsonLine = $line
      break
    }
  }

  return [pscustomobject]@{
    Json = $jsonLine
    Output = ($lines -join "`n")
    ExitCode = $exitCode
  }
}

function Test-AlembicAuditNeedsDependencyRepair {
  param(
    [Parameter(Mandatory)]
    [pscustomobject]$Result
  )

  if ($Result.Output -match "(?i)(ImportError|ModuleNotFoundError|No module named|cannot import name|sqlalchemy_unavailable|Package\(s\) not found|invalid literal for int\(\) with base 10)") {
    return $true
  }

  if (-not [string]::IsNullOrWhiteSpace($Result.Json)) {
    try {
      $payload = $Result.Json | ConvertFrom-Json -ErrorAction Stop
      return ($payload.db_state.status -eq "db_error" -and $payload.db_state.error -match "(?i)(sqlalchemy|alembic|ImportError|ModuleNotFoundError|No module named|cannot import name)")
    } catch {
      return $false
    }
  }

  return $false
}

Ensure-BackendVirtualEnv
Ensure-VenvPythonRunnable

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
$env:DB_URL = $backendDbUrl
$env:PYTHONUNBUFFERED = "1"

Write-Host "Validando cadena de migraciones Alembic..."
$auditResult = Invoke-AlembicAudit

if (Test-AlembicAuditNeedsDependencyRepair -Result $auditResult) {
  Write-Host "La auditoria detecto dependencias Python incompletas o corruptas." -ForegroundColor Yellow
  Write-Host "VIRU intentara repararlas una vez y reintentar la auditoria."
  Install-BackendDependencies
  $auditResult = Invoke-AlembicAudit
}

$auditRaw = $auditResult.Json
$auditExitCode = $auditResult.ExitCode

if ([string]::IsNullOrWhiteSpace($auditRaw)) {
  throw @"
No se pudo ejecutar la auditoria de migraciones Alembic en:
  $backendPython -m app.infrastructure.db.alembic_audit --json

Salida capturada:
$($auditResult.Output)

Causas posibles:
  1. El entorno virtual de Python (.venv) esta incompleto o corrupto
  2. Faltan dependencias del backend (corre pip install -e .[dev])
  3. Hay un error de importacion en el modulo alembic_audit

Accion sugerida (desde la raiz del repo):
  cd "$backendDir"
  .\.venv\Scripts\python.exe -m pip install -e .[dev]

Si el problema persiste, regenera el .venv:
  rmdir /s "$backendDir\.venv"
  py -3.14 -m venv .venv
  .\.venv\Scripts\python.exe -m pip install -e .[dev]
"@
}

try {
  $audit = $auditRaw | ConvertFrom-Json -ErrorAction Stop
} catch {
  throw "No se pudo interpretar el diagnostico previo de Alembic. Detalle: $auditRaw"
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
  -WorkingDirectory $backendDir `
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
$backendErrLog = Join-Path $logsDir "backend-$ts.err.log"
$frontendLog = Join-Path $logsDir "frontend-$ts.log"
$frontendErrLog = Join-Path $logsDir "frontend-$ts.err.log"
$frontendBuildDir = Join-Path $root "frontend\.next"

# Mata procesos previos en 3000/8000 para evitar conflictos
$ports = @(3000, 8000)
foreach ($p in $ports) {
  $conns = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
  foreach ($c in $conns) {
    Stop-ProcessTree -ProcessId $c.OwningProcess
  }
}

# next dev maneja su propio cache incremental. Solo limpiamos si hay sennal de
# compilacion corrupta (entorno CI). En desarrollo local esto acelera el arranque.
if ($env:CI -or $env:NEXT_CLEAN_CACHE) {
  if (Test-Path $frontendBuildDir) {
    Remove-Item -LiteralPath $frontendBuildDir -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Cache de Next.js limpiado forzadamente (CI o NEXT_CLEAN_CACHE)."
  }
}

$uvicornWorkers = if ($env:UVICORN_WORKERS) { [int]$env:UVICORN_WORKERS } else { 1 }
if ($uvicornWorkers -le 0) { $uvicornWorkers = 1 }

Test-FrontendTooling

if ($runBackground) {
  $env:LOG_FILE = $backendLog
  $uvicornArgs = if ($uvicornWorkers -gt 1) {
    @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--workers", $uvicornWorkers)
  } else {
    @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload")
  }
  Start-Process -FilePath $backendPython `
    -ArgumentList $uvicornArgs `
    -WorkingDirectory $backendDir `
    -RedirectStandardOutput $backendLog `
    -RedirectStandardError $backendErrLog `
    -PassThru `
    -WindowStyle Hidden | Out-Null

  $env:NEXT_PUBLIC_API_URL = "/api/v1"
  Start-Process -FilePath "cmd.exe" `
    -ArgumentList @("/c", "npm run dev") `
    -WorkingDirectory (Join-Path $root "frontend") `
    -RedirectStandardOutput $frontendLog `
    -RedirectStandardError $frontendErrLog `
    -WindowStyle Hidden | Out-Null
} else {
  # Backend (modo foreground en nueva ventana)
  $uvicornReloadArg = if ($uvicornWorkers -gt 1) { "" } else { "--reload" }
  $uvicornWorkersArg = if ($uvicornWorkers -gt 1) { "--workers $uvicornWorkers" } else { "" }
  $backendCmd = "title Viru Backend && cd /d `"$root\backend`" && set LOG_FILE=$backendLog && set DB_URL=$backendDbUrl && `"$backendPython`" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 $uvicornReloadArg $uvicornWorkersArg"
  Start-Process -FilePath "cmd.exe" -ArgumentList "/k", $backendCmd | Out-Null

  # Frontend (modo foreground en nueva ventana)
  $frontendCmd = "title Viru Frontend && cd /d `"$root\frontend`" && set NEXT_PUBLIC_API_URL=/api/v1 && npm run dev"
  Start-Process -FilePath "cmd.exe" -ArgumentList "/k", $frontendCmd | Out-Null
}

try {
  Write-Host "Esperando a que el backend responda en :8000/health ..."
  $api = Wait-HttpOk -Url "http://127.0.0.1:8000/health" -Attempts 25 -DelaySeconds 1
  Write-Host "Backend listo (status $($api.StatusCode))."

  Write-Host "Esperando a que el frontend compile y responda en :3000 ..."
  Write-Host "(La primera compilacion de Next.js puede tardar hasta 60s)"
  $web = Wait-HttpOk -Url "http://127.0.0.1:3000" -Attempts 60 -DelaySeconds 1
  Write-Host "Frontend listo (status $($web.StatusCode))."

  Write-Host "Estabilizando backend tras arranque (3s)..."
  Start-Sleep -Seconds 3
  Write-Host "Backend estabilizado."
  Write-Host "DB_URL:" $backendDbUrl
  Write-Host "Backend log:" $backendLog
  Write-Host "Backend err log:" $backendErrLog
  Write-Host "Frontend log:" $frontendLog
  Write-Host "Frontend err log:" $frontendErrLog
  Write-Host "Abre: http://localhost:3000"
} catch {
  throw "Arranque incompleto. Revisa $backendLog, $backendErrLog, $frontendLog y $frontendErrLog. Detalle: $($_.Exception.Message)"
}
