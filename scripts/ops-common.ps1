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

function Test-IsPrivateIPv4 {
  param([string]$IpAddress)

  if (-not $IpAddress) {
    return $false
  }

  return (
    $IpAddress -match '^10\.' -or
    $IpAddress -match '^192\.168\.' -or
    $IpAddress -match '^172\.(1[6-9]|2[0-9]|3[0-1])\.' -or
    $IpAddress -match '^100\.(6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])\.'
  )
}

function Get-PreferredLocalIPv4 {
  try {
    $defaultRoute = Get-NetRoute -DestinationPrefix "0.0.0.0/0" -ErrorAction Stop |
      Sort-Object RouteMetric, InterfaceMetric |
      Select-Object -First 1
    if ($defaultRoute) {
      $ip = Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex $defaultRoute.InterfaceIndex -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -and $_.IPAddress -notlike "169.254.*" } |
        Select-Object -First 1 -ExpandProperty IPAddress
      if ($ip) {
        return $ip
      }
    }
  } catch {}

  return Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -match '^\d+\.\d+\.\d+\.\d+$' -and $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } |
    Select-Object -First 1 -ExpandProperty IPAddress
}

function Get-PublicIpv4Address {
  $providers = @(
    "https://api.ipify.org",
    "https://ipv4.icanhazip.com"
  )

  foreach ($provider in $providers) {
    try {
      $response = Invoke-WebRequest -UseBasicParsing -Uri $provider -TimeoutSec 10
      $ip = ([string]$response.Content).Trim()
      if ($ip -match '^\d+\.\d+\.\d+\.\d+$') {
        return $ip
      }
    } catch {}
  }

  return $null
}

function Get-UpnpPortMappingCollection {
  try {
    $nat = New-Object -ComObject HNetCfg.NATUPnP
    return $nat.StaticPortMappingCollection
  } catch {
    return $null
  }
}

function Get-UpnpPortMappings {
  param([int[]]$Ports = @(80, 443))

  $collection = Get-UpnpPortMappingCollection
  if ($null -eq $collection) {
    return @()
  }

  $results = @()
  foreach ($item in $collection) {
    if ($Ports -notcontains [int]$item.ExternalPort) {
      continue
    }

    $results += [pscustomobject]@{
      Protocol = [string]$item.Protocol
      ExternalPort = [int]$item.ExternalPort
      InternalPort = [int]$item.InternalPort
      InternalClient = [string]$item.InternalClient
      ExternalIPAddress = [string]$item.ExternalIPAddress
      Enabled = [bool]$item.Enabled
      Description = [string]$item.Description
    }
  }

  return $results
}

function Ensure-UpnpPortMappings {
  param(
    [int[]]$Ports = @(80, 443),
    [string]$InternalClient = (Get-PreferredLocalIPv4)
  )

  $collection = Get-UpnpPortMappingCollection
  if ($null -eq $collection) {
    return [pscustomobject]@{
      Supported = $false
      LocalIp = $InternalClient
      ExternalIp = $null
      Changes = @()
    }
  }

  $changes = @()
  $externalIp = $null
  foreach ($port in $Ports) {
    $mapping = @(
      Get-UpnpPortMappings -Ports @($port) |
        Where-Object { $_.Protocol -eq "TCP" -and $_.ExternalPort -eq $port }
    ) | Select-Object -First 1

    if ($mapping) {
      $externalIp = [string]$mapping.ExternalIPAddress
      if ($mapping.InternalClient -eq $InternalClient -and [int]$mapping.InternalPort -eq $port -and $mapping.Enabled) {
        $changes += [pscustomobject]@{ Port = $port; Action = "ok"; Message = ("UPnP ya reenviaba TCP/{0} a {1}:{2}." -f $port, $InternalClient, $port) }
      } else {
        $changes += [pscustomobject]@{ Port = $port; Action = "conflict"; Message = ("UPnP ya usa TCP/{0} hacia {1}:{2}." -f $port, $mapping.InternalClient, $mapping.InternalPort) }
      }
      continue
    }

    try {
      $created = $collection.Add([int]$port, [string]"TCP", [int]$port, [string]$InternalClient, [bool]$true, [string]("ViruTracker TCP/{0}" -f $port))
      $externalIp = if ($created) { [string]$created.ExternalIPAddress } else { $externalIp }
      $changes += [pscustomobject]@{ Port = $port; Action = "added"; Message = ("UPnP ha creado TCP/{0} -> {1}:{2}." -f $port, $InternalClient, $port) }
    } catch {
      $changes += [pscustomobject]@{ Port = $port; Action = "error"; Message = ("No pude crear el reenvio UPnP para TCP/{0}: {1}" -f $port, $_.Exception.Message) }
    }
  }

  return [pscustomobject]@{
    Supported = $true
    LocalIp = $InternalClient
    ExternalIp = $externalIp
    Changes = $changes
  }
}

function Get-NetworkEdgeStatus {
  $localIp = Get-PreferredLocalIPv4
  $publicIp = Get-PublicIpv4Address
  $upnpMappings = @(Get-UpnpPortMappings -Ports @(80, 443) | Where-Object { $_.Protocol -eq "TCP" })
  $upnpExternalIp = $null
  if ($upnpMappings.Count -gt 0) {
    $upnpExternalIp = $upnpMappings[0].ExternalIPAddress
  }

  $doubleNat = $false
  if ($publicIp -and $upnpExternalIp -and $upnpExternalIp -ne $publicIp -and (Test-IsPrivateIPv4 -IpAddress $upnpExternalIp)) {
    $doubleNat = $true
  }

  return [pscustomobject]@{
    LocalIp = $localIp
    PublicIp = $publicIp
    UpnpMappings = $upnpMappings
    UpnpExternalIp = $upnpExternalIp
    UpnpSupported = ($null -ne (Get-UpnpPortMappingCollection))
    DoubleNatDetected = $doubleNat
  }
}

function Test-LocalTlsHandshake {
  param(
    [Parameter(Mandatory)][string]$ServerName,
    [string]$Address = "127.0.0.1",
    [int]$Port = 443
  )

  $tcp = $null
  $stream = $null
  $ssl = $null
  try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $async = $tcp.BeginConnect($Address, $Port, $null, $null)
    if (-not $async.AsyncWaitHandle.WaitOne(5000)) {
      throw "timeout"
    }
    $tcp.EndConnect($async)
    $stream = $tcp.GetStream()
    $ssl = New-Object System.Net.Security.SslStream($stream, $false, ({ $true }))
    $ssl.AuthenticateAsClient($ServerName)
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2 $ssl.RemoteCertificate
    return [pscustomobject]@{
      Success = $true
      Subject = $cert.Subject
      Issuer = $cert.Issuer
      NotAfter = $cert.NotAfter
    }
  } catch {
    return [pscustomobject]@{
      Success = $false
      Error = $_.Exception.Message
    }
  } finally {
    if ($ssl) { $ssl.Dispose() }
    if ($stream) { $stream.Dispose() }
    if ($tcp) { $tcp.Dispose() }
  }
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

  $needsWrite = $true
  if ($existedBefore) {
    $expectedLines = @(
      "# Auto-generated local production env for viru-tracker."
      "DOMAIN=$($values['DOMAIN'])"
      "NEXT_PUBLIC_API_URL=$($values['NEXT_PUBLIC_API_URL'])"
      "JWT_SECRET=$($values['JWT_SECRET'])"
      "APP_ENV=$($values['APP_ENV'])"
    )
    if ($values.ContainsKey("CORS_ALLOW_ORIGINS") -and $values["CORS_ALLOW_ORIGINS"]) {
      $expectedLines += "CORS_ALLOW_ORIGINS=$($values['CORS_ALLOW_ORIGINS'])"
    }
    if ($values.ContainsKey("CORS_ALLOW_ORIGIN_REGEX") -and $values["CORS_ALLOW_ORIGIN_REGEX"]) {
      $expectedLines += "CORS_ALLOW_ORIGIN_REGEX=$($values['CORS_ALLOW_ORIGIN_REGEX'])"
    }
    try {
      $currentContent = Get-Content -Path $envPath -ErrorAction Stop
      if ((@($currentContent) -join "`n") -eq ($expectedLines -join "`n")) {
        $needsWrite = $false
      }
    } catch {}
  }

  if ($needsWrite) {
    Write-DotEnvFile -Path $envPath -Values $values
  }
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
function Get-CaddyCliCandidates {
  $candidates = @()
  if (Test-CommandAvailable -CommandName "caddy") {
    $cmd = Get-Command caddy -ErrorAction SilentlyContinue
    if ($cmd) {
      $candidates += $cmd.Source
    }
  }

  $defaultPaths = @(
    "C:\Program Files\Caddy\caddy.exe",
    "C:\Program Files\caddy\caddy.exe",
    (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages\CaddyServer.Caddy_Microsoft.Winget.Source_8wekyb3d8bbwe\caddy.exe")
  )

  foreach ($path in $defaultPaths) {
    if ((Test-Path $path) -and $candidates -notcontains $path) {
      $candidates += $path
    }
  }

  return $candidates
}

function Get-PreferredCaddyCliPath {
  $candidates = @(Get-CaddyCliCandidates)
  foreach ($candidate in $candidates) {
    $path = [string]$candidate
    if ($path) {
      return $path
    }
  }
  return $null
}

function Ensure-CaddyInstalled {
  $caddyCli = Get-PreferredCaddyCliPath
  if ($caddyCli) {
    return $caddyCli
  }

  if (-not (Test-CommandAvailable -CommandName "winget")) {
    throw "caddy no esta instalado y winget no esta disponible para instalarlo automaticamente."
  }

  Write-Info "Instalando Caddy automaticamente con winget..."
  $result = Invoke-CommandWithTimeout -FilePath "winget.exe" -Arguments @(
    "install",
    "-e",
    "--id", "CaddyServer.Caddy",
    "--accept-package-agreements",
    "--accept-source-agreements",
    "--disable-interactivity"
  ) -TimeoutSeconds 300

  $caddyCli = Get-PreferredCaddyCliPath
  if ($caddyCli) {
    return $caddyCli
  }

  if ($result.TimedOut -or $result.ExitCode -ne 0) {
    $detail = if ($result.Output.Count -gt 0) { ($result.Output | Out-String).Trim() } else { "sin detalle" }
    throw "No pude instalar Caddy automaticamente: $detail"
  }

  $caddyCli = Get-PreferredCaddyCliPath
  if (-not $caddyCli) {
    throw "winget termino, pero no encuentro caddy.exe en esta maquina."
  }

  return $caddyCli
}

function Get-CaddyManagedPaths {
  $logsDir = Get-LogsDir
  return [pscustomobject]@{
    PidFile = Join-Path $logsDir "caddy.pid"
    OutLog = Join-Path $logsDir "caddy.out.log"
    ErrLog = Join-Path $logsDir "caddy.err.log"
  }
}

function Get-CaddyListeningProcesses {
  $portStates = @(Get-PortListeners -Ports @(80, 443) | Where-Object { $_.Listening })
  return @($portStates | Where-Object { $_.ProcessName -eq "caddy" })
}

function Get-CaddyRuntimeStatus {
  $status = [ordered]@{
    Installed = [bool](Get-PreferredCaddyCliPath)
    InfraEnvExists = (Test-Path (Get-InfraEnvPath))
    Domain = $null
    DomainMatchesDuckDns = $null
    Running = $false
    ProcessId = $null
    ProcessName = $null
    HasPidFile = $false
    PublishedPorts = @()
    TlsReady = $false
    TlsDetail = $null
    Healthy = $false
  }

  $infraEnv = Read-DotEnv -Path (Get-InfraEnvPath) -AllowMissing
  if ($infraEnv.ContainsKey("DOMAIN")) {
    $status.Domain = $infraEnv["DOMAIN"]
  }

  $duck = Read-DotEnv -Path (Get-DuckDnsConfigPath) -AllowMissing
  if ($duck.ContainsKey("DUCKDNS_FQDN") -and $status.Domain) {
    $status.DomainMatchesDuckDns = ($duck["DUCKDNS_FQDN"] -eq $status.Domain)
  }

  $paths = Get-CaddyManagedPaths
  $state = Get-ManagedProcessState -PidFile $paths.PidFile -Label "Caddy"
  $status.HasPidFile = $state.HasPidFile
  $status.Running = $state.IsRunning
  $status.ProcessId = $state.ProcessId
  $status.ProcessName = $state.ProcessName

  $portStates = @(Get-PortListeners -Ports @(80, 443) | Where-Object { $_.Listening })
  foreach ($portState in $portStates) {
    if ($status.ProcessId -and $portState.ProcessId -eq $status.ProcessId) {
      $status.PublishedPorts += $portState.Port
    }
  }

  if ($status.PublishedPorts.Count -eq 0) {
    $caddyListeners = @(Get-CaddyListeningProcesses)
    if ($caddyListeners.Count -gt 0) {
      $status.Running = $true
      $status.ProcessId = $caddyListeners[0].ProcessId
      $status.ProcessName = $caddyListeners[0].ProcessName
      $status.PublishedPorts = @($caddyListeners | Select-Object -ExpandProperty Port -Unique)
      if (-not $status.HasPidFile) {
        $status.HasPidFile = $true
      }
    }
  }

  if ($status.Domain -and $status.Running -and ($status.PublishedPorts -contains 443)) {
    $tls = Test-LocalTlsHandshake -ServerName $status.Domain
    $status.TlsReady = $tls.Success
    $status.TlsDetail = $tls
  }

  $status.Healthy = ($status.Running -and $status.PublishedPorts.Count -gt 0 -and $status.TlsReady)
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
  $edgeStatus = Get-NetworkEdgeStatus

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

  $frontendLocal = @(Get-PortListeners -Ports @(3000) | Where-Object { $_.Listening })
  $backendLocal = @(Get-PortListeners -Ports @(8000) | Where-Object { $_.Listening })
  if ($frontendLocal.Count -gt 0) {
    $checks += [pscustomobject]@{ Name = "Frontend local"; Status = "ok"; Message = "Frontend local activo en 3000." }
  } else {
    $ready = $false
    $checks += [pscustomobject]@{ Name = "Frontend local"; Status = "fail"; Message = "El frontend local no esta escuchando en 3000." }
  }

  if ($backendLocal.Count -gt 0) {
    $checks += [pscustomobject]@{ Name = "Backend local"; Status = "ok"; Message = "Backend local activo en 8000." }
  } else {
    $ready = $false
    $checks += [pscustomobject]@{ Name = "Backend local"; Status = "fail"; Message = "El backend local no esta escuchando en 8000." }
  }

  if (Get-PreferredCaddyCliPath) {
    $checks += [pscustomobject]@{ Name = "Caddy"; Status = "ok"; Message = "Caddy nativo esta instalado." }
  } elseif (Test-CommandAvailable -CommandName "winget") {
    $checks += [pscustomobject]@{ Name = "Caddy"; Status = "warn"; Message = "Caddy no esta instalado todavia, pero se puede instalar automaticamente con winget." }
  } else {
    $ready = $false
    $checks += [pscustomobject]@{ Name = "Caddy"; Status = "fail"; Message = "Caddy no esta instalado y winget no esta disponible." }
  }

  $portStates = Get-PortListeners -Ports @(80, 443)
  if ($caddyStatus.Healthy) {
    $checks += [pscustomobject]@{ Name = "Puertos 80/443"; Status = "ok"; Message = "Caddy ya esta corriendo y publica: $($caddyStatus.PublishedPorts -join ', ')." }
  } else {
    $busyPorts = @($portStates | Where-Object { $_.Listening })
    $busyByCaddy = @($busyPorts | Where-Object { $_.ProcessName -eq "caddy" })
    $busyByOthers = @($busyPorts | Where-Object { $_.ProcessName -ne "caddy" })
    if ($busyByOthers.Count -gt 0) {
      $ready = $false
      $busySummary = $busyByOthers | ForEach-Object { "puerto $($_.Port) por PID $($_.ProcessId) ($($_.ProcessName))" }
      $checks += [pscustomobject]@{ Name = "Puertos 80/443"; Status = "fail"; Message = "Hay conflictos en $($busySummary -join '; ')." }
    } elseif ($busyByCaddy.Count -gt 0) {
      $caddyPorts = @($busyByCaddy.Port | Sort-Object -Unique)
      $checks += [pscustomobject]@{ Name = "Puertos 80/443"; Status = "ok"; Message = "Caddy ya esta escuchando en: $($caddyPorts -join ', ')." }
    } else {
      $checks += [pscustomobject]@{ Name = "Puertos 80/443"; Status = "ok"; Message = "Puertos 80 y 443 libres para Caddy." }
    }
  }

  if ($edgeStatus.UpnpSupported) {
    if ($edgeStatus.UpnpMappings.Count -gt 0) {
      $mappingSummary = $edgeStatus.UpnpMappings |
        Where-Object { $_.Protocol -eq "TCP" } |
        Sort-Object ExternalPort |
        ForEach-Object { "TCP/$($_.ExternalPort) -> $($_.InternalClient):$($_.InternalPort)" }
      $checks += [pscustomobject]@{ Name = "UPnP"; Status = "ok"; Message = "UPnP visible en el router: $($mappingSummary -join '; ')." }
    } else {
      $checks += [pscustomobject]@{ Name = "UPnP"; Status = "warn"; Message = "El router expone UPnP, pero no hay reenvios activos para 80/443." }
    }
  } else {
    $checks += [pscustomobject]@{ Name = "UPnP"; Status = "warn"; Message = "No he podido consultar UPnP en este entorno." }
  }

  if ($edgeStatus.PublicIp) {
    $checks += [pscustomobject]@{ Name = "IP publica"; Status = "ok"; Message = "IP publica detectada: $($edgeStatus.PublicIp)." }
  } else {
    $checks += [pscustomobject]@{ Name = "IP publica"; Status = "warn"; Message = "No he podido confirmar la IP publica actual." }
  }

  if ($edgeStatus.DoubleNatDetected) {
    $ready = $false
    $checks += [pscustomobject]@{ Name = "Topologia de red"; Status = "fail"; Message = "Hay doble NAT: UPnP ve como externa $($edgeStatus.UpnpExternalIp), pero la IP publica real es $($edgeStatus.PublicIp)." }
  } elseif ($edgeStatus.UpnpExternalIp) {
    $checks += [pscustomobject]@{ Name = "Topologia de red"; Status = "ok"; Message = "La IP externa visible por UPnP coincide con la red esperada: $($edgeStatus.UpnpExternalIp)." }
  }

  if ($caddyStatus.Running -and -not $caddyStatus.TlsReady) {
    $ready = $false
    $tlsDetail = if ($caddyStatus.TlsDetail -and $caddyStatus.TlsDetail.Error) { $caddyStatus.TlsDetail.Error } else { "handshake TLS no disponible todavia" }
    $checks += [pscustomobject]@{ Name = "TLS"; Status = "fail"; Message = "Caddy esta escuchando, pero HTTPS aun no esta listo: $tlsDetail." }
  } elseif ($caddyStatus.TlsReady) {
    $checks += [pscustomobject]@{ Name = "TLS"; Status = "ok"; Message = "HTTPS local listo para $domain." }
  }

  return [pscustomobject]@{
    Ready = $ready
    Domain = $domain
    DuckDnsFqdn = $duckFqdn
    TaskInfo = $taskInfo
    DnsRecords = $dnsRecords
    LastDuckUpdate = $lastDuckUpdate
    CaddyStatus = $caddyStatus
    EdgeStatus = $edgeStatus
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
