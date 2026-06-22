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

function Test-DockerComposeAvailable {
  if (-not (Test-CommandAvailable -CommandName "docker")) {
    return $false
  }

  $null = & docker compose version 2>$null
  return ($LASTEXITCODE -eq 0)
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

  $output = & docker compose @Arguments 2>&1
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

  $stateOutput = (& docker inspect --format '{{.State.Status}}' $containerId 2>$null)
  if ($LASTEXITCODE -eq 0) {
    $stateText = ($stateOutput | Select-Object -First 1).ToString().Trim()
    $status.State = $stateText
    $status.Running = ($stateText -eq "running")
  }

  $portsOutput = (& docker inspect --format '{{json .NetworkSettings.Ports}}' $containerId 2>$null)
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
    $checks += [pscustomobject]@{ Name = "Docker Compose"; Status = "fail"; Message = "docker compose no esta disponible en PATH." }
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
