Set-StrictMode -Version Latest

function Get-RepoRoot {
  return (Split-Path -Parent $PSScriptRoot)
}

function Get-InfraDir {
  return (Join-Path (Get-RepoRoot) "infra")
}

function Get-LogsDir {
  $path = Join-Path (Get-RepoRoot) "logs"
  if (-not (Test-Path $path)) {
    New-Item -ItemType Directory -Path $path -Force | Out-Null
  }
  return $path
}

function Get-DuckDnsConfigPath {
  return (Join-Path (Get-InfraDir) "duckdns.local.env")
}

function Get-InfraEnvPath {
  return (Join-Path (Get-InfraDir) ".env")
}

function New-UrlSafeSecret {
  param([int]$Bytes = 48)

  $buffer = New-Object byte[] $Bytes
  $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  try {
    $rng.GetBytes($buffer)
  } finally {
    $rng.Dispose()
  }

  return [Convert]::ToBase64String($buffer).TrimEnd("=").Replace("+", "-").Replace("/", "_")
}

function Read-DotEnv {
  param(
    [Parameter(Mandatory)]
    [string]$Path,
    [switch]$AllowMissing
  )

  $values = @{}
  if (-not (Test-Path $Path)) {
    if ($AllowMissing) {
      return $values
    }
    throw "Archivo .env no encontrado: $Path"
  }

  foreach ($line in Get-Content -Path $Path) {
    $trimmed = $line.Trim()
    if (-not $trimmed -or $trimmed.StartsWith("#")) {
      continue
    }

    $parts = $trimmed -split "=", 2
    if ($parts.Count -ne 2) {
      continue
    }

    $key = $parts[0].Trim()
    $value = $parts[1].Trim().Trim("'`"")
    if ($key) {
      $values[$key] = $value
    }
  }

  return $values
}

function Write-DotEnvFile {
  param(
    [Parameter(Mandatory)][string]$Path,
    [Parameter(Mandatory)][hashtable]$Values
  )

  $lines = @(
    "# Auto-generated local production env for viru-tracker."
    "DOMAIN=$($Values['DOMAIN'])"
    "NEXT_PUBLIC_API_URL=$($Values['NEXT_PUBLIC_API_URL'])"
    "JWT_SECRET=$($Values['JWT_SECRET'])"
    "APP_ENV=$($Values['APP_ENV'])"
  )

  if ($Values.ContainsKey("CORS_ALLOW_ORIGINS") -and $Values["CORS_ALLOW_ORIGINS"]) {
    $lines += "CORS_ALLOW_ORIGINS=$($Values['CORS_ALLOW_ORIGINS'])"
  }

  if ($Values.ContainsKey("CORS_ALLOW_ORIGIN_REGEX") -and $Values["CORS_ALLOW_ORIGIN_REGEX"]) {
    $lines += "CORS_ALLOW_ORIGIN_REGEX=$($Values['CORS_ALLOW_ORIGIN_REGEX'])"
  }

  Set-Content -Path $Path -Value $lines -Encoding ASCII
}

function Ensure-InfraEnv {
  param([Parameter(Mandatory)][string]$Domain)

  $envPath = Get-InfraEnvPath
  $existedBefore = Test-Path $envPath
  $existing = Read-DotEnv -Path $envPath -AllowMissing

  $values = @{
    DOMAIN = $Domain
    NEXT_PUBLIC_API_URL = if ($existing.ContainsKey("NEXT_PUBLIC_API_URL") -and $existing["NEXT_PUBLIC_API_URL"]) { $existing["NEXT_PUBLIC_API_URL"] } else { "/api/v1" }
    JWT_SECRET = if ($existing.ContainsKey("JWT_SECRET") -and $existing["JWT_SECRET"] -and $existing["JWT_SECRET"] -ne "change-me-to-a-strong-random-value" -and $existing["JWT_SECRET"] -ne "change-me") { $existing["JWT_SECRET"] } else { New-UrlSafeSecret }
    APP_ENV = if ($existing.ContainsKey("APP_ENV") -and $existing["APP_ENV"]) { $existing["APP_ENV"] } else { "production" }
  }

  if ($existing.ContainsKey("CORS_ALLOW_ORIGINS")) {
    $values["CORS_ALLOW_ORIGINS"] = $existing["CORS_ALLOW_ORIGINS"]
  }
  if ($existing.ContainsKey("CORS_ALLOW_ORIGIN_REGEX")) {
    $values["CORS_ALLOW_ORIGIN_REGEX"] = $existing["CORS_ALLOW_ORIGIN_REGEX"]
  }

  Write-DotEnvFile -Path $envPath -Values $values
  return [pscustomobject]@{
    Path = $envPath
    Domain = $values["DOMAIN"]
    JwtGenerated = (-not $existing.ContainsKey("JWT_SECRET") -or -not $existing["JWT_SECRET"] -or $existing["JWT_SECRET"] -eq "change-me-to-a-strong-random-value" -or $existing["JWT_SECRET"] -eq "change-me")
    WasCreated = (-not $existedBefore)
  }
}

function Write-Section {
  param([string]$Text)
  Write-Host ""
  Write-Host $Text -ForegroundColor Cyan
}

function Write-Info {
  param([string]$Text)
  Write-Host $Text -ForegroundColor Gray
}

function Write-Ok {
  param([string]$Text)
  Write-Host $Text -ForegroundColor Green
}

function Write-Warn {
  param([string]$Text)
  Write-Host $Text -ForegroundColor Yellow
}

function Write-Fail {
  param([string]$Text)
  Write-Host $Text -ForegroundColor Red
}

function Get-ManagedProcessState {
  param(
    [Parameter(Mandatory)]
    [string]$PidFile,
    [string]$Label = "Proceso"
  )

  if (-not (Test-Path $PidFile)) {
    return [pscustomobject]@{
      Label = $Label
      HasPidFile = $false
      HasValidPid = $false
      IsRunning = $false
      ProcessId = $null
      ProcessName = $null
      Message = "$Label no esta activo."
    }
  }

  $raw = (Get-Content -Path $PidFile -Raw -ErrorAction SilentlyContinue)
  if ($null -eq $raw) {
    return [pscustomobject]@{
      Label = $Label
      HasPidFile = $true
      HasValidPid = $false
      IsRunning = $false
      ProcessId = $null
      ProcessName = $null
      Message = "$Label tiene un PID invalido."
    }
  }

  $trimmed = $raw.Trim()
  $pidValue = 0
  $hasValidPid = [int]::TryParse($trimmed, [ref]$pidValue)
  if (-not $hasValidPid -or $pidValue -le 0) {
    return [pscustomobject]@{
      Label = $Label
      HasPidFile = $true
      HasValidPid = $false
      IsRunning = $false
      ProcessId = $null
      ProcessName = $null
      Message = "$Label tiene un PID invalido."
    }
  }

  $proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
  return [pscustomobject]@{
    Label = $Label
    HasPidFile = $true
    HasValidPid = $true
    IsRunning = [bool]$proc
    ProcessId = $pidValue
    ProcessName = if ($proc) { $proc.ProcessName } else { $null }
    Message = if ($proc) { "$Label activo (PID $pidValue)." } else { "$Label tiene un PID guardado pero el proceso ya no existe." }
  }
}

function Stop-ManagedProcess {
  param(
    [Parameter(Mandatory)]
    [string]$PidFile
  )

  $state = Get-ManagedProcessState -PidFile $PidFile
  if ($state.IsRunning) {
    Stop-Process -Id $state.ProcessId -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 300
  }

  if (Test-Path $PidFile) {
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
  }

  return $state
}

function Test-CommandAvailable {
  param([Parameter(Mandatory)][string]$CommandName)
  return [bool](Get-Command $CommandName -ErrorAction SilentlyContinue)
}

function Get-PortListeners {
  param([Parameter(Mandatory)][int[]]$Ports)

  $results = @()
  foreach ($port in $Ports) {
    $listeners = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
    if ($listeners.Count -eq 0) {
      $results += [pscustomobject]@{
        Port = $port
        Listening = $false
        ProcessId = $null
        ProcessName = $null
        LocalAddress = $null
      }
      continue
    }

    foreach ($listener in ($listeners | Sort-Object OwningProcess -Unique)) {
      $proc = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
      $results += [pscustomobject]@{
        Port = $port
        Listening = $true
        ProcessId = $listener.OwningProcess
        ProcessName = if ($proc) { $proc.ProcessName } else { "desconocido" }
        LocalAddress = $listener.LocalAddress
      }
    }
  }

  return $results
}

function Format-PortLine {
  param([Parameter(Mandatory)]$PortState)

  if (-not $PortState.Listening) {
    return "Puerto $($PortState.Port): libre"
  }

  return "Puerto $($PortState.Port): ocupado por PID $($PortState.ProcessId) ($($PortState.ProcessName))"
}

function Get-ScheduledTaskInfo {
  param([Parameter(Mandatory)][string]$TaskName)

  if (Get-Command Get-ScheduledTask -ErrorAction SilentlyContinue) {
    try {
      $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
      return [pscustomobject]@{
        Present = $true
        Enabled = [bool]$task.Settings.Enabled
        State = [string]$task.State
        TaskName = $TaskName
      }
    } catch {
      return [pscustomobject]@{
        Present = $false
        Enabled = $false
        State = "Missing"
        TaskName = $TaskName
      }
    }
  }

  schtasks /Query /TN $TaskName 2>$null | Out-Null
  $present = ($LASTEXITCODE -eq 0)
  return [pscustomobject]@{
    Present = $present
    Enabled = $present
    State = if ($present) { "Unknown" } else { "Missing" }
    TaskName = $TaskName
  }
}

function Set-ScheduledTaskEnabledState {
  param(
    [Parameter(Mandatory)][string]$TaskName,
    [Parameter(Mandatory)][bool]$Enabled
  )

  if (-not (Get-Command Get-ScheduledTask -ErrorAction SilentlyContinue)) {
    throw "Enable/Disable de tareas requiere el modulo ScheduledTasks de PowerShell."
  }

  $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
  if ($Enabled) {
    Enable-ScheduledTask -InputObject $task | Out-Null
  } else {
    Disable-ScheduledTask -InputObject $task | Out-Null
  }

  return (Get-ScheduledTaskInfo -TaskName $TaskName)
}

function Get-DnsARecords {
  param([string]$Name)

  if (-not $Name) {
    return @()
  }

  try {
    return @(
      Resolve-DnsName -Name $Name -Type A -ErrorAction Stop |
        Where-Object { $_.IPAddress } |
        Select-Object -ExpandProperty IPAddress
    )
  } catch {
    return @()
  }
}

function Get-LastTabLogEntry {
  param([Parameter(Mandatory)][string]$Path)

  if (-not (Test-Path $Path)) {
    return $null
  }

  $line = Get-Content -Path $Path -Tail 1 -ErrorAction SilentlyContinue
  if (-not $line) {
    return $null
  }

  $parts = $line -split "`t"
  return [pscustomobject]@{
    Raw = $line
    Timestamp = if ($parts.Count -gt 0) { $parts[0] } else { $null }
    Result = if ($parts.Count -gt 1) { $parts[1] } else { $null }
    Detail = if ($parts.Count -gt 2) { $parts[2] } else { $null }
  }
}

function Invoke-CommandWithTimeout {
  param(
    [Parameter(Mandatory)][string]$FilePath,
    [Parameter(Mandatory)][string[]]$Arguments,
    [int]$TimeoutSeconds = 10
  )

  $tempBase = Join-Path (Get-LogsDir) ("cmd-" + [guid]::NewGuid().ToString("N"))
  $stdoutPath = "$tempBase.out.log"
  $stderrPath = "$tempBase.err.log"

  try {
    $proc = Start-Process -FilePath $FilePath `
      -ArgumentList $Arguments `
      -RedirectStandardOutput $stdoutPath `
      -RedirectStandardError $stderrPath `
      -PassThru `
      -WindowStyle Hidden

    if (-not $proc.WaitForExit($TimeoutSeconds * 1000)) {
      Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
      return [pscustomobject]@{
        TimedOut = $true
        ExitCode = 124
        Output = @()
      }
    }

    $output = @()
    if (Test-Path $stdoutPath) { $output += Get-Content -Path $stdoutPath -ErrorAction SilentlyContinue }
    if (Test-Path $stderrPath) { $output += Get-Content -Path $stderrPath -ErrorAction SilentlyContinue }

    return [pscustomobject]@{
      TimedOut = $false
      ExitCode = $proc.ExitCode
      Output = $output
    }
  } finally {
    Remove-Item $stdoutPath -Force -ErrorAction SilentlyContinue
    Remove-Item $stderrPath -Force -ErrorAction SilentlyContinue
  }
}

function Get-DockerCliCandidates {
  $candidates = @()
  if (Test-CommandAvailable -CommandName "docker") {
    $cmd = Get-Command docker -ErrorAction SilentlyContinue
    if ($cmd) {
      $candidates += $cmd.Source
    }
  }

  $defaultPaths = @(
    "C:\Program Files\Docker\Docker\resources\bin\docker.exe",
    "C:\Program Files\Docker\Docker\resources\docker-cli.exe"
  )

  foreach ($path in $defaultPaths) {
    if ((Test-Path $path) -and $candidates -notcontains $path) {
      $candidates += $path
    }
  }

  return $candidates
}

function Get-PreferredDockerCliPath {
  $candidates = @(Get-DockerCliCandidates)
  foreach ($candidate in $candidates) {
    $path = [string]$candidate
    if ($path) {
      return $path
    }
  }
  return $null
}

function Get-DockerDesktopExecutable {
  $paths = @(
    "C:\Program Files\Docker\Docker\Docker Desktop.exe",
    "C:\Program Files\Docker\Docker Desktop.exe"
  )

  foreach ($path in $paths) {
    if (Test-Path $path) {
      return $path
    }
  }

  return $null
}

function Test-DockerDesktopWelcomeOpen {
  $windows = @(Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "Welcome*" })
  return ($windows.Count -gt 0)
}

function Test-DockerCliAvailable {
  $candidates = Get-DockerCliCandidates
  foreach ($candidate in $candidates) {
    $candidatePath = [string]$candidate
    if (-not $candidatePath) {
      continue
    }
    $result = Invoke-CommandWithTimeout -FilePath $candidatePath -Arguments @("compose", "version") -TimeoutSeconds 10
    if (-not $result.TimedOut -and $result.ExitCode -eq 0) {
      if (-not ($env:PATH -split ";" | Where-Object { $_ -eq (Split-Path -Parent $candidatePath) })) {
        $env:PATH = (Split-Path -Parent $candidatePath) + ";" + $env:PATH
      }
      Set-Alias -Name docker -Value $candidatePath -Scope Script
      return $true
    }
  }
  return $false
}

function Test-DockerDaemonAvailable {
  $dockerCli = Get-PreferredDockerCliPath
  if (-not $dockerCli) {
    return $false
  }

  $result = Invoke-CommandWithTimeout -FilePath $dockerCli -Arguments @("info") -TimeoutSeconds 10
  if ($result.TimedOut) {
    return $false
  }
  return ($result.ExitCode -eq 0)
}

function Test-DockerComposeAvailable {
  return ((Test-DockerCliAvailable) -and (Test-DockerDaemonAvailable))
}

function Wait-ForDockerDaemon {
  param([int]$TimeoutSeconds = 180)

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  do {
    if (Test-DockerComposeAvailable) {
      return $true
    }
    if (Test-DockerDesktopWelcomeOpen) {
      return $false
    }
    Start-Sleep -Seconds 3
  } while ((Get-Date) -lt $deadline)

  return $false
}

function Start-DockerDesktopIfInstalled {
  $dockerDesktop = Get-DockerDesktopExecutable
  if (-not $dockerDesktop) {
    return $false
  }

  if (Test-DockerDesktopWelcomeOpen) {
    return $false
  }

  $running = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
  if (-not $running) {
    Start-Process -FilePath $dockerDesktop -WindowStyle Hidden | Out-Null
  }

  return (Wait-ForDockerDaemon -TimeoutSeconds 180)
}

function Install-DockerDesktopIfMissing {
  if (Test-DockerComposeAvailable) {
    return $true
  }

  if (Start-DockerDesktopIfInstalled) {
    return $true
  }

  if (-not (Test-CommandAvailable -CommandName "winget")) {
    return $false
  }

  $logPath = Join-Path (Get-LogsDir) "docker-desktop-install.log"
  $stderrPath = Join-Path (Get-LogsDir) "docker-desktop-install.err.log"
  if (Test-Path $logPath) {
    Remove-Item $logPath -Force -ErrorAction SilentlyContinue
  }
  if (Test-Path $stderrPath) {
    Remove-Item $stderrPath -Force -ErrorAction SilentlyContinue
  }

  $proc = Start-Process -FilePath "winget.exe" `
    -ArgumentList @(
      "install",
      "-e",
      "--id", "Docker.DockerDesktop",
      "--accept-package-agreements",
      "--accept-source-agreements",
      "--disable-interactivity"
    ) `
    -RedirectStandardOutput $logPath `
    -RedirectStandardError $stderrPath `
    -PassThru

  if (-not $proc.WaitForExit(300000)) {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    Write-Warn "La instalacion automatica de Docker Desktop no termino en 5 minutos. Puede requerir permisos de administrador o una confirmacion de Windows."
    return $false
  }

  if ($proc.ExitCode -ne 0) {
    $installOutput = @()
    if (Test-Path $logPath) { $installOutput += Get-Content -Path $logPath -Tail 80 }
    if (Test-Path $stderrPath) { $installOutput += Get-Content -Path $stderrPath -Tail 80 }
    $installOutput = if ($installOutput.Count -gt 0) { ($installOutput | Out-String).Trim() } else { "sin log" }
    Write-Warn ("No pude instalar Docker Desktop automaticamente con winget: " + $installOutput)
    return $false
  }

  return (Start-DockerDesktopIfInstalled)
}

function Ensure-DockerComposeReady {
  if (Test-DockerComposeAvailable) {
    return $true
  }

  if (Test-DockerDesktopWelcomeOpen) {
    Write-Warn "Docker Desktop esta instalado pero sigue en la pantalla inicial 'Welcome'. Hasta completar ese onboarding, el daemon no arranca."
    return $false
  }

  if (Start-DockerDesktopIfInstalled) {
    return $true
  }

  $installed = Install-DockerDesktopIfMissing
  if ($installed) {
    return $true
  }

  if (Test-DockerDesktopWelcomeOpen) {
    Write-Warn "Docker Desktop esta instalado pero sigue en la pantalla inicial 'Welcome'. Hasta completar ese onboarding, el daemon no arranca."
  }

  return $false
}

function Get-DockerComposeBaseArgs {
  $infraDir = Get-InfraDir
  $envPath = Get-InfraEnvPath
  $args = @()
  if (Test-Path $envPath) {
    $args += @("--env-file", $envPath)
  }
  $args += @(
    "-f", (Join-Path $infraDir "docker-compose.yml"),
    "-f", (Join-Path $infraDir "docker-compose.prod.yml")
  )
  return $args
}

function Invoke-DockerCompose {
  param(
    [Parameter(Mandatory)][string[]]$Arguments,
    [switch]$AllowFailure
  )

  $dockerCli = Get-PreferredDockerCliPath
  if (-not $dockerCli) {
    throw "No encuentro el binario docker en esta maquina."
  }

  $output = & $dockerCli compose @Arguments 2>&1
  $exitCode = $LASTEXITCODE
  if (-not $AllowFailure -and $exitCode -ne 0) {
    throw "docker compose fallo (exit $exitCode): $($output -join [Environment]::NewLine)"
  }

  return [pscustomobject]@{
    Output = @($output)
    ExitCode = $exitCode
  }
}

function Get-ComposeServices {
  if (-not (Test-DockerComposeAvailable)) {
    return @()
  }

  $result = Invoke-DockerCompose -Arguments ((Get-DockerComposeBaseArgs) + @("config", "--services")) -AllowFailure
  if ($result.ExitCode -ne 0) {
    return @()
  }

  return @($result.Output | ForEach-Object { $_.ToString().Trim() } | Where-Object { $_ })
}

function Get-CaddyRuntimeStatus {
  $status = [ordered]@{
    DockerAvailable = (Test-DockerComposeAvailable)
    InfraEnvExists = (Test-Path (Get-InfraEnvPath))
    Domain = $null
    ServiceDefined = $false
    ContainerId = $null
    Exists = $false
    Running = $false
    State = "unknown"
    PublishedPorts = @()
    DomainMatchesDuckDns = $null
  }

  $infraEnv = Read-DotEnv -Path (Get-InfraEnvPath) -AllowMissing
  if ($infraEnv.ContainsKey("DOMAIN")) {
    $status.Domain = $infraEnv["DOMAIN"]
  }

  $duck = Read-DotEnv -Path (Get-DuckDnsConfigPath) -AllowMissing
  if ($duck.ContainsKey("DUCKDNS_FQDN") -and $status.Domain) {
    $status.DomainMatchesDuckDns = ($duck["DUCKDNS_FQDN"] -eq $status.Domain)
  }

  if (-not $status.DockerAvailable) {
    return [pscustomobject]$status
  }

  $services = Get-ComposeServices
  $status.ServiceDefined = ($services -contains "caddy")
  if (-not $status.ServiceDefined) {
    $status.State = "service_missing"
    return [pscustomobject]$status
  }

  $idResult = Invoke-DockerCompose -Arguments ((Get-DockerComposeBaseArgs) + @("ps", "-a", "-q", "caddy")) -AllowFailure
  $containerId = ($idResult.Output | ForEach-Object { $_.ToString().Trim() } | Where-Object { $_ } | Select-Object -First 1)
  if (-not $containerId) {
    $status.State = "not_created"
    return [pscustomobject]$status
  }

  $status.ContainerId = $containerId
  $status.Exists = $true

  $dockerCli = Get-PreferredDockerCliPath
  $stateOutput = (& $dockerCli inspect --format '{{.State.Status}}' $containerId 2>$null)
  if ($LASTEXITCODE -eq 0) {
    $stateText = ($stateOutput | Select-Object -First 1).ToString().Trim()
    $status.State = $stateText
    $status.Running = ($stateText -eq "running")
  }

  $portsOutput = (& $dockerCli inspect --format '{{json .NetworkSettings.Ports}}' $containerId 2>$null)
  if ($LASTEXITCODE -eq 0 -and $portsOutput) {
    try {
      $portsJson = ($portsOutput | Select-Object -First 1).ToString()
      $portsMap = $portsJson | ConvertFrom-Json
      foreach ($prop in $portsMap.PSObject.Properties) {
        if ($null -ne $prop.Value) {
          $status.PublishedPorts += $prop.Name
        }
      }
    } catch {}
  }

  return [pscustomobject]$status
}

function Get-PublicDomainPreflight {
  $checks = @()
  $ready = $true
  $duckConfig = Read-DotEnv -Path (Get-DuckDnsConfigPath) -AllowMissing
  $infraEnv = Read-DotEnv -Path (Get-InfraEnvPath) -AllowMissing
  $domain = if ($infraEnv.ContainsKey("DOMAIN")) { $infraEnv["DOMAIN"] } else { $null }
  $duckFqdn = if ($duckConfig.ContainsKey("DUCKDNS_FQDN")) { $duckConfig["DUCKDNS_FQDN"] } else { $null }
  $duckLog = if ($duckConfig.ContainsKey("DUCKDNS_LOG_PATH")) { Join-Path (Get-RepoRoot) $duckConfig["DUCKDNS_LOG_PATH"] } else { Join-Path (Get-LogsDir) "duckdns-update.log" }
  $lastDuckUpdate = Get-LastTabLogEntry -Path $duckLog
  $taskName = if ($duckConfig.ContainsKey("DUCKDNS_TASK_NAME")) { $duckConfig["DUCKDNS_TASK_NAME"] } else { "ViruTracker-DuckDNS" }
  $taskInfo = Get-ScheduledTaskInfo -TaskName $taskName
  $caddyStatus = Get-CaddyRuntimeStatus

  if (-not (Test-Path (Get-InfraEnvPath))) {
    $ready = $false
    $checks += [pscustomobject]@{ Name = "infra/.env"; Status = "fail"; Message = "Falta infra/.env. Copia infra/.env.prod.example y define DOMAIN/JWT_SECRET." }
  } elseif (-not $domain) {
    $ready = $false
    $checks += [pscustomobject]@{ Name = "DOMAIN"; Status = "fail"; Message = "infra/.env existe, pero DOMAIN no esta definido." }
  } elseif ($domain -eq "localhost") {
    $ready = $false
    $checks += [pscustomobject]@{ Name = "DOMAIN"; Status = "fail"; Message = "DOMAIN sigue siendo localhost; no sirve para publicacion estable." }
  } else {
    $checks += [pscustomobject]@{ Name = "DOMAIN"; Status = "ok"; Message = "DOMAIN configurado: $domain" }
  }

  if ($duckFqdn) {
    if ($domain -and $domain -ne $duckFqdn) {
      $ready = $false
      $checks += [pscustomobject]@{ Name = "DuckDNS"; Status = "fail"; Message = "infra/.env usa $domain, pero DuckDNS esta configurado para $duckFqdn." }
    } else {
      $checks += [pscustomobject]@{ Name = "DuckDNS"; Status = "ok"; Message = "DuckDNS configurado para $duckFqdn." }
    }
  } else {
    $ready = $false
    $checks += [pscustomobject]@{ Name = "DuckDNS"; Status = "fail"; Message = "Falta infra/duckdns.local.env o esta incompleto." }
  }

  if ($taskInfo.Present) {
    if ($taskInfo.Enabled) {
      $checks += [pscustomobject]@{ Name = "Tarea DuckDNS"; Status = "ok"; Message = "Tarea $taskName activa ($($taskInfo.State))." }
    } else {
      $ready = $false
      $checks += [pscustomobject]@{ Name = "Tarea DuckDNS"; Status = "fail"; Message = "Tarea $taskName existe, pero esta desactivada." }
    }
  } else {
    $ready = $false
    $checks += [pscustomobject]@{ Name = "Tarea DuckDNS"; Status = "fail"; Message = "No existe la tarea programada $taskName." }
  }

  if ($lastDuckUpdate -and $lastDuckUpdate.Result -eq "OK") {
    $checks += [pscustomobject]@{ Name = "Ultimo update DuckDNS"; Status = "ok"; Message = "Ultimo update: OK ($($lastDuckUpdate.Timestamp))." }
  } elseif ($lastDuckUpdate) {
    $ready = $false
    $checks += [pscustomobject]@{ Name = "Ultimo update DuckDNS"; Status = "fail"; Message = "Ultimo update: $($lastDuckUpdate.Result) ($($lastDuckUpdate.Timestamp))." }
  } else {
    $ready = $false
    $checks += [pscustomobject]@{ Name = "Ultimo update DuckDNS"; Status = "fail"; Message = "No hay evidencia de updates en $duckLog." }
  }

  $dnsTarget = if ($domain) { $domain } elseif ($duckFqdn) { $duckFqdn } else { $null }
  $dnsRecords = @(Get-DnsARecords -Name $dnsTarget)
  if ($dnsTarget -and $dnsRecords.Count -gt 0) {
    $checks += [pscustomobject]@{ Name = "DNS"; Status = "ok"; Message = "Resolucion A activa para ${dnsTarget}: $($dnsRecords -join ', ')." }
  } elseif ($dnsTarget) {
    $ready = $false
    $checks += [pscustomobject]@{ Name = "DNS"; Status = "fail"; Message = "El dominio $dnsTarget aun no resuelve; parece que sigue propagando." }
  } else {
    $ready = $false
    $checks += [pscustomobject]@{ Name = "DNS"; Status = "fail"; Message = "No hay dominio efectivo para comprobar DNS." }
  }

  if (-not (Test-DockerComposeAvailable)) {
    $ready = $false
    if ((Get-PreferredDockerCliPath) -or (Test-DockerDesktopWelcomeOpen)) {
      if (Test-DockerDesktopWelcomeOpen) {
        $checks += [pscustomobject]@{ Name = "Docker Compose"; Status = "fail"; Message = "Docker Desktop esta en la pantalla inicial 'Welcome' y el daemon aun no arranco." }
      } else {
        $checks += [pscustomobject]@{ Name = "Docker Compose"; Status = "fail"; Message = "docker compose existe, pero el daemon de Docker Desktop aun no responde." }
      }
    } else {
      $checks += [pscustomobject]@{ Name = "Docker Compose"; Status = "fail"; Message = "docker compose no esta disponible en PATH." }
    }
  } else {
    $checks += [pscustomobject]@{ Name = "Docker Compose"; Status = "ok"; Message = "docker compose esta disponible." }
    $services = Get-ComposeServices
    $required = @("caddy", "backend", "frontend")
    $missing = @($required | Where-Object { $services -notcontains $_ })
    if ($missing.Count -gt 0) {
      $ready = $false
      $checks += [pscustomobject]@{ Name = "Compose"; Status = "fail"; Message = "Faltan servicios en compose: $($missing -join ', ')." }
    } else {
      $checks += [pscustomobject]@{ Name = "Compose"; Status = "ok"; Message = "Servicios esperados presentes: $($required -join ', ')." }
    }
  }

  $portStates = Get-PortListeners -Ports @(80, 443)
  if ($caddyStatus.Running) {
    $checks += [pscustomobject]@{ Name = "Puertos 80/443"; Status = "ok"; Message = "Caddy ya esta corriendo y publica: $($caddyStatus.PublishedPorts -join ', ')." }
  } else {
    $busyPorts = @($portStates | Where-Object { $_.Listening })
    if ($busyPorts.Count -gt 0) {
      $ready = $false
      $busySummary = $busyPorts | ForEach-Object { "puerto $($_.Port) por PID $($_.ProcessId) ($($_.ProcessName))" }
      $checks += [pscustomobject]@{ Name = "Puertos 80/443"; Status = "fail"; Message = "Hay conflictos en $($busySummary -join '; ')." }
    } else {
      $checks += [pscustomobject]@{ Name = "Puertos 80/443"; Status = "ok"; Message = "Puertos 80 y 443 libres para Caddy." }
    }
  }

  return [pscustomobject]@{
    Ready = $ready
    Domain = $domain
    DuckDnsFqdn = $duckFqdn
    TaskInfo = $taskInfo
    DnsRecords = $dnsRecords
    LastDuckUpdate = $lastDuckUpdate
    CaddyStatus = $caddyStatus
    Checks = $checks
  }
}

function Write-ChecksReport {
  param([Parameter(Mandatory)]$Checks)

  foreach ($check in $Checks) {
    switch ($check.Status) {
      "ok" { Write-Ok ("[OK] " + $check.Message) }
      "warn" { Write-Warn ("[WARN] " + $check.Message) }
      default { Write-Fail ("[FAIL] " + $check.Message) }
    }
  }
}

function Get-PublicTunnelPaths {
  $logsDir = Get-LogsDir
  return [pscustomobject]@{
    PidFile = Join-Path $logsDir "public_temp_tunnel.pid"
    OutLog = Join-Path $logsDir "public_temp_tunnel.out.log"
    ErrLog = Join-Path $logsDir "public_temp_tunnel.err.log"
  }
}

function Get-PublicTunnelUrl {
  $paths = Get-PublicTunnelPaths
  $lines = @()
  if (Test-Path $paths.OutLog) {
    $lines += Get-Content -Path $paths.OutLog -ErrorAction SilentlyContinue
  }
  if (Test-Path $paths.ErrLog) {
    $lines += Get-Content -Path $paths.ErrLog -ErrorAction SilentlyContinue
  }

  $line = $lines | Where-Object { $_ -match "https://[^ ]+" } | Select-Object -Last 1
  if (-not $line) {
    return $null
  }

  $match = [regex]::Match($line, "https://[^ ]+")
  if ($match.Success) {
    return $match.Value
  }
  return $null
}
