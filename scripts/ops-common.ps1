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

function Get-InfraEnvPath {
  return (Join-Path (Get-InfraDir) ".env")
}

function Get-InfraEnvTemplatePath {
  return (Join-Path (Get-InfraDir) ".env.prod.example")
}

function Get-StableTunnelStatePath {
  return (Join-Path (Get-LogsDir) "stable-tunnel-state.json")
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

function Read-DotEnv {
  param(
    [Parameter(Mandatory)][string]$Path,
    [switch]$AllowMissing
  )

  $values = @{}
  if (-not (Test-Path $Path)) {
    if ($AllowMissing) {
      return $values
    }
    throw "No existe el archivo $Path"
  }

  foreach ($line in Get-Content -Path $Path -ErrorAction Stop) {
    $trimmed = $line.Trim()
    if (-not $trimmed -or $trimmed.StartsWith("#")) {
      continue
    }

    $parts = $trimmed -split "=", 2
    if ($parts.Count -ne 2) {
      continue
    }

    $values[$parts[0].Trim()] = $parts[1].Trim()
  }

  return $values
}

function Set-DotEnvValue {
  param(
    [Parameter(Mandatory)][string]$Path,
    [Parameter(Mandatory)][string]$Key,
    [Parameter(Mandatory)][string]$Value
  )

  $lines = @()
  if (Test-Path $Path) {
    $lines = @(Get-Content -Path $Path -ErrorAction Stop)
  }

  $updated = $false
  for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match "^\s*$([regex]::Escape($Key))=") {
      $lines[$i] = "$Key=$Value"
      $updated = $true
      break
    }
  }

  if (-not $updated) {
    $lines += "$Key=$Value"
  }

  Set-Content -Path $Path -Value $lines -Encoding ASCII
}

function Ensure-StableTunnelEnv {
  param([string]$Domain)

  $envPath = Get-InfraEnvPath
  if (-not (Test-Path $envPath)) {
    $templatePath = Get-InfraEnvTemplatePath
    if (-not (Test-Path $templatePath)) {
      throw "Falta la plantilla infra/.env.prod.example para preparar infra/.env."
    }
    Copy-Item -Path $templatePath -Destination $envPath -Force
  }

  if ($Domain) {
    Set-DotEnvValue -Path $envPath -Key "DOMAIN" -Value $Domain
  }

  return $envPath
}

function Get-ManagedProcessState {
  param(
    [Parameter(Mandatory)][string]$PidFile,
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

  $raw = Get-Content -Path $PidFile -Raw -ErrorAction SilentlyContinue
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

  $pidValue = 0
  $hasValidPid = [int]::TryParse($raw.Trim(), [ref]$pidValue)
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
  param([Parameter(Mandatory)][string]$PidFile)

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

function Get-CommandVersionText {
  param(
    [Parameter(Mandatory)][string]$FilePath,
    [string[]]$Arguments = @("--version"),
    [int]$TimeoutSeconds = 10
  )

  try {
    $direct = & $FilePath @Arguments 2>&1
    if ($direct) {
      $directText = (($direct | Select-Object -First 1) -join " ").Trim()
      if ($directText) {
        return $directText
      }
    }
  } catch {}

  $result = Invoke-CommandWithTimeout -FilePath $FilePath -Arguments $Arguments -TimeoutSeconds $TimeoutSeconds
  if ($result.TimedOut -or $result.ExitCode -ne 0 -or $result.Output.Count -eq 0) {
    return $null
  }

  return (($result.Output -join " ").Trim())
}

function Test-WingetAvailable {
  return (Test-CommandAvailable -CommandName "winget")
}

function Install-WingetPackageIfMissing {
  param(
    [Parameter(Mandatory)][string]$DisplayName,
    [Parameter(Mandatory)][string]$PackageId,
    [Parameter(Mandatory)][scriptblock]$DetectScript
  )

  if (& $DetectScript) {
    return [pscustomobject]@{
      Installed = $true
      Changed = $false
      Message = "$DisplayName ya estaba instalado."
      Output = @()
      ExitCode = 0
      TimedOut = $false
    }
  }

  if (-not (Test-WingetAvailable)) {
    return [pscustomobject]@{
      Installed = $false
      Changed = $false
      Message = "winget no esta disponible para instalar $DisplayName automaticamente."
      Output = @()
      ExitCode = 127
      TimedOut = $false
    }
  }

  $winget = (Get-Command winget -ErrorAction SilentlyContinue).Source
  $result = Invoke-CommandWithTimeout -FilePath $winget -Arguments @("install", "--id", $PackageId, "--accept-package-agreements", "--accept-source-agreements", "--silent") -TimeoutSeconds 240

  $installedNow = (& $DetectScript)
  return [pscustomobject]@{
    Installed = [bool]$installedNow
    Changed = [bool]$installedNow
    Message = if ($installedNow) { "$DisplayName instalado automaticamente." } else { "No pude instalar $DisplayName automaticamente." }
    Output = $result.Output
    ExitCode = $result.ExitCode
    TimedOut = $result.TimedOut
  }
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

function Get-LocalAppStatus {
  $ports = @(Get-PortListeners -Ports @(3000, 8000))
  $frontend = @($ports | Where-Object { $_.Port -eq 3000 -and $_.Listening })
  $backend = @($ports | Where-Object { $_.Port -eq 8000 -and $_.Listening })

  return [pscustomobject]@{
    FrontendListeners = $frontend
    BackendListeners = $backend
    FrontendReady = ($frontend.Count -gt 0)
    BackendReady = ($backend.Count -gt 0)
    Ready = ($frontend.Count -gt 0 -and $backend.Count -gt 0)
    TunnelTargetUrl = "http://127.0.0.1:3000"
  }
}

function Read-StableTunnelState {
  $path = Get-StableTunnelStatePath
  if (-not (Test-Path $path)) {
    return $null
  }

  try {
    return (Get-Content -Path $path -Raw -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop)
  } catch {
    return $null
  }
}

function Write-StableTunnelState {
  param([Parameter(Mandatory)]$State)
  $path = Get-StableTunnelStatePath
  $json = $State | ConvertTo-Json -Depth 8
  Set-Content -Path $path -Value $json -Encoding ASCII
  return $path
}

function Clear-StableTunnelState {
  $path = Get-StableTunnelStatePath
  if (Test-Path $path) {
    Remove-Item $path -Force -ErrorAction SilentlyContinue
  }
}

function Find-UrlsInText {
  param([string]$Text)

  if (-not $Text) {
    return @()
  }

  return @([regex]::Matches($Text, 'https://[^\s"''<>]+') | ForEach-Object { $_.Value } | Select-Object -Unique)
}

function Find-UrlsInObject {
  param($Value)

  if ($null -eq $Value) {
    return @()
  }

  if ($Value -is [string]) {
    return @(Find-UrlsInText -Text $Value)
  }

  $urls = @()
  if ($Value -is [System.Collections.IEnumerable] -and -not ($Value -is [string])) {
    foreach ($item in $Value) {
      $urls += Find-UrlsInObject -Value $item
    }
    return @($urls | Select-Object -Unique)
  }

  foreach ($property in $Value.PSObject.Properties) {
    $urls += Find-UrlsInObject -Value $property.Value
  }

  return @($urls | Select-Object -Unique)
}

function Get-CloudflaredCliPath {
  $candidates = @()
  if (Test-CommandAvailable -CommandName "cloudflared") {
    $cmd = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($cmd) {
      $candidates += $cmd.Source
    }
  }

  $defaultPaths = @(
    "C:\Program Files\cloudflared\cloudflared.exe",
    (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe")
  )

  foreach ($path in $defaultPaths) {
    if ((Test-Path $path) -and $candidates -notcontains $path) {
      $candidates += $path
    }
  }

  return ($candidates | Select-Object -First 1)
}

function Ensure-CloudflaredInstalled {
  $install = Install-WingetPackageIfMissing -DisplayName "cloudflared" -PackageId "Cloudflare.cloudflared" -DetectScript { [bool](Get-CloudflaredCliPath) }
  $cliPath = Get-CloudflaredCliPath

  return [pscustomobject]@{
    Installed = [bool]$cliPath
    Changed = $install.Changed
    CliPath = $cliPath
    Message = if ($cliPath) { $install.Message } else { "Cloudflare Tunnel no esta instalado en este equipo." }
    Output = $install.Output
  }
}

function Get-CloudflareTunnelPaths {
  $logsDir = Get-LogsDir
  return [pscustomobject]@{
    PidFile = Join-Path $logsDir "cloudflare-tunnel.pid"
    OutLog = Join-Path $logsDir "cloudflare-tunnel.out.log"
    ErrLog = Join-Path $logsDir "cloudflare-tunnel.err.log"
    LogFile = Join-Path $logsDir "cloudflare-tunnel.out.log"
  }
}

function Get-CloudflareTunnelConfigCandidates {
  return @(
    (Join-Path (Get-InfraDir) "cloudflare-tunnel.local.yml"),
    (Join-Path (Get-InfraDir) "cloudflare-tunnel.local.yaml"),
    (Join-Path (Get-InfraDir) "cloudflare-tunnel.yml")
  )
}

function Get-CloudflareTunnelConfigPath {
  foreach ($path in (Get-CloudflareTunnelConfigCandidates)) {
    if (Test-Path $path) {
      return $path
    }
  }
  return $null
}

function Get-CloudflareTunnelAuthCertPath {
  return (Join-Path $env:USERPROFILE ".cloudflared\cert.pem")
}

function Get-CloudflareTunnelCredentialsFileFromConfig {
  param([string]$ConfigPath)

  if (-not $ConfigPath -or -not (Test-Path $ConfigPath)) {
    return $null
  }

  foreach ($line in Get-Content -Path $ConfigPath -ErrorAction SilentlyContinue) {
    if ($line -match '^\s*credentials-file:\s*("?)([^"#]+)\1') {
      return $Matches[2].Trim()
    }
  }

  return $null
}

function Get-CloudflareTunnelConfigInfo {
  $configPath = Get-CloudflareTunnelConfigPath
  if (-not $configPath) {
    return [pscustomobject]@{
      ConfigPath = $null
      TunnelIdOrName = $null
      Hostname = $null
      CredentialsFile = $null
    }
  }

  $tunnelId = $null
  $hostname = $null
  $credentialsFile = $null
  foreach ($line in Get-Content -Path $configPath -ErrorAction SilentlyContinue) {
    if (-not $tunnelId -and $line -match '^\s*tunnel:\s*("?)([^"#]+)\1') {
      $tunnelId = $Matches[2].Trim()
    }
    if (-not $hostname -and $line -match '^\s*hostname:\s*("?)([^"#]+)\1') {
      $hostname = $Matches[2].Trim()
    }
    if (-not $credentialsFile -and $line -match '^\s*credentials-file:\s*("?)([^"#]+)\1') {
      $credentialsFile = $Matches[2].Trim()
    }
  }

  return [pscustomobject]@{
    ConfigPath = $configPath
    TunnelIdOrName = $tunnelId
    Hostname = $hostname
    CredentialsFile = $credentialsFile
  }
}

function Write-CloudflareTunnelConfig {
  param(
    [Parameter(Mandatory)][string]$TunnelIdOrName,
    [Parameter(Mandatory)][string]$Hostname,
    [Parameter(Mandatory)][string]$CredentialsFile,
    [string]$ServiceUrl = "http://127.0.0.1:3000"
  )

  $configPath = Join-Path (Get-InfraDir) "cloudflare-tunnel.local.yml"
  $lines = @(
    "tunnel: $TunnelIdOrName",
    "credentials-file: $CredentialsFile",
    "",
    "ingress:",
    "  - hostname: $Hostname",
    "    service: $ServiceUrl",
    "  - service: http_status:404"
  )
  Set-Content -Path $configPath -Value $lines -Encoding ASCII
  return $configPath
}

function Get-CloudflareQuickTunnelUrl {
  $paths = Get-CloudflareTunnelPaths
  $lines = @()
  if (Test-Path $paths.OutLog) {
    $lines += Get-Content -Path $paths.OutLog -ErrorAction SilentlyContinue
  }
  if (Test-Path $paths.ErrLog) {
    $lines += Get-Content -Path $paths.ErrLog -ErrorAction SilentlyContinue
  }

  $urls = @()
  foreach ($line in $lines) {
    $urls += Find-UrlsInText -Text $line
  }

  $quickUrl = @($urls | Where-Object { $_ -like "https://*.trycloudflare.com*" } | Select-Object -Last 1)
  if ($quickUrl.Count -gt 0) {
    return $quickUrl[0]
  }

  $genericUrl = @($urls | Select-Object -Last 1)
  if ($genericUrl.Count -gt 0) {
    return $genericUrl[0]
  }

  return $null
}

function Get-CloudflareTunnelStatus {
  $cliPath = Get-CloudflaredCliPath
  $paths = Get-CloudflareTunnelPaths
  $state = Get-ManagedProcessState -PidFile $paths.PidFile -Label "Cloudflare Tunnel"
  $config = Get-CloudflareTunnelConfigInfo
  $mode = if ($config.ConfigPath) { "named" } else { "quick" }
  $publicUrl = if ($mode -eq "named" -and $config.Hostname) { "https://$($config.Hostname)" } else { Get-CloudflareQuickTunnelUrl }
  $authCertPath = Get-CloudflareTunnelAuthCertPath
  $credentialsFileExists = [bool]($config.CredentialsFile -and (Test-Path $config.CredentialsFile))
  $namedConfigReady = [bool]($config.ConfigPath -and $config.TunnelIdOrName -and $config.Hostname -and $credentialsFileExists)
  $version = if ($cliPath) { Get-CommandVersionText -FilePath $cliPath -Arguments @("--version") } else { $null }

  $blockingReason = $null
  $nextStep = $null
  if (-not $cliPath) {
    $blockingReason = "Cloudflare Tunnel no esta instalado en este equipo."
    $nextStep = "Instala cloudflared para publicar con Cloudflare Tunnel."
  } elseif ($mode -eq "named" -and -not (Test-Path $authCertPath) -and -not $credentialsFileExists) {
    $blockingReason = "Cloudflare Tunnel no esta autorizado todavia para usar el tunel configurado."
    $nextStep = "Falta autenticar cloudflared. Ejecuta 'cloudflared tunnel login' y vuelve a intentarlo."
  } elseif ($mode -eq "named" -and -not $config.TunnelIdOrName) {
    $blockingReason = "La configuracion local de Cloudflare existe, pero falta el identificador del tunel."
    $nextStep = "Anade 'tunnel:' a infra/cloudflare-tunnel.local.yml."
  } elseif ($mode -eq "named" -and -not $config.Hostname) {
    $blockingReason = "La configuracion local de Cloudflare existe, pero falta asociar el hostname del tunel."
    $nextStep = "La configuracion local existe, pero falta 'hostname:' en el ingress del tunnel."
  } elseif ($mode -eq "named" -and -not $credentialsFileExists) {
    $blockingReason = "La configuracion local de Cloudflare existe, pero falta el credentials-file del tunel."
    $nextStep = "Descarga el credentials-file del tunel y apunta a el desde infra/cloudflare-tunnel.local.yml."
  } elseif ($mode -eq "quick" -and -not $state.IsRunning) {
    $nextStep = "Si quieres dominio propio, crea infra/cloudflare-tunnel.local.yml. Si no, puedes arrancar un quick tunnel desde el panel."
  }

  return [pscustomobject]@{
    Provider = "cloudflare"
    DisplayName = "Cloudflare Tunnel"
    Installed = [bool]$cliPath
    CliPath = $cliPath
    Version = $version
    Mode = $mode
    Running = $state.IsRunning
    HasPidFile = $state.HasPidFile
    ProcessId = $state.ProcessId
    ProcessName = $state.ProcessName
    ConfigPath = $config.ConfigPath
    TunnelIdOrName = $config.TunnelIdOrName
    Hostname = $config.Hostname
    CredentialsFile = $config.CredentialsFile
    CredentialsFileExists = $credentialsFileExists
    AuthCertPath = $authCertPath
    AuthCertExists = (Test-Path $authCertPath)
    PublicUrl = $publicUrl
    Ready = [bool]($state.IsRunning -and $publicUrl)
    BlockingReason = $blockingReason
    NextStep = $nextStep
    Paths = $paths
    NamedConfigReady = $namedConfigReady
  }
}

function Start-CloudflareTunnel {
  $status = Get-CloudflareTunnelStatus
  if (-not $status.Installed) {
    return $status
  }

  if ($status.Mode -eq "named" -and -not $status.NamedConfigReady) {
    return $status
  }

  if ($status.Running -and $status.Ready) {
    return $status
  }

  $paths = $status.Paths
  if (Test-Path $paths.OutLog) { Remove-Item $paths.OutLog -Force -ErrorAction SilentlyContinue }
  if (Test-Path $paths.ErrLog) { Remove-Item $paths.ErrLog -Force -ErrorAction SilentlyContinue }
  if (Test-Path $paths.PidFile) { Remove-Item $paths.PidFile -Force -ErrorAction SilentlyContinue }

  $args = @("tunnel", "--no-autoupdate")
  if ($status.Mode -eq "named") {
    $args += @("--config", $status.ConfigPath, "run")
  } else {
    $args += @("--url", "http://127.0.0.1:3000")
  }

  $proc = Start-Process -FilePath $status.CliPath `
    -ArgumentList $args `
    -RedirectStandardOutput $paths.OutLog `
    -RedirectStandardError $paths.ErrLog `
    -WindowStyle Hidden `
    -PassThru

  Set-Content -Path $paths.PidFile -Value $proc.Id -Encoding ASCII

  for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 500
    $current = Get-CloudflareTunnelStatus
    if ($current.Ready) {
      Write-StableTunnelState -State ([pscustomobject]@{
        Provider = "cloudflare"
        StartedAt = (Get-Date).ToString("s")
        Mode = $current.Mode
        PublicUrl = $current.PublicUrl
      }) | Out-Null
      return $current
    }

    if (-not $current.Running) {
      break
    }
  }

  return (Get-CloudflareTunnelStatus)
}

function Stop-CloudflareTunnel {
  $status = Get-CloudflareTunnelStatus
  $paths = $status.Paths

  $stoppedState = Stop-ManagedProcess -PidFile $paths.PidFile
  if (Test-Path $paths.PidFile) {
    Remove-Item $paths.PidFile -Force -ErrorAction SilentlyContinue
  }

  return [pscustomobject]@{
    Provider = "cloudflare"
    HadPidFile = $stoppedState.HasPidFile
    WasRunning = $stoppedState.IsRunning
    Stopped = ($stoppedState.HasPidFile -or $stoppedState.IsRunning)
  }
}

function Get-TailscaleCliPath {
  $candidates = @()
  if (Test-CommandAvailable -CommandName "tailscale") {
    $cmd = Get-Command tailscale -ErrorAction SilentlyContinue
    if ($cmd) {
      $candidates += $cmd.Source
    }
  }

  $defaultPaths = @(
    "C:\Program Files\Tailscale\tailscale.exe"
  )

  foreach ($path in $defaultPaths) {
    if ((Test-Path $path) -and $candidates -notcontains $path) {
      $candidates += $path
    }
  }

  return ($candidates | Select-Object -First 1)
}

function Ensure-TailscaleInstalled {
  $install = Install-WingetPackageIfMissing -DisplayName "Tailscale" -PackageId "Tailscale.Tailscale" -DetectScript { [bool](Get-TailscaleCliPath) }
  $cliPath = Get-TailscaleCliPath

  return [pscustomobject]@{
    Installed = [bool]$cliPath
    Changed = $install.Changed
    CliPath = $cliPath
    Message = if ($cliPath) { $install.Message } else { "Tailscale no esta instalado en este equipo." }
    Output = $install.Output
  }
}

function Get-TailscaleFunnelPaths {
  $logsDir = Get-LogsDir
  return [pscustomobject]@{
    OutLog = Join-Path $logsDir "tailscale-funnel.out.log"
    ErrLog = Join-Path $logsDir "tailscale-funnel.err.log"
    LogFile = Join-Path $logsDir "tailscale-funnel.out.log"
  }
}

function Invoke-TailscaleJsonCommand {
  param([Parameter(Mandatory)][string[]]$Arguments)

  $cliPath = Get-TailscaleCliPath
  if (-not $cliPath) {
    return [pscustomobject]@{
      Available = $false
      Success = $false
      ExitCode = 127
      Output = @()
      Json = $null
    }
  }

  try {
    $output = & $cliPath @Arguments 2>&1
    $exitCode = $LASTEXITCODE
  } catch {
    $output = @($_.Exception.Message)
    $exitCode = 1
  }

  $result = [pscustomobject]@{
    TimedOut = $false
    ExitCode = $exitCode
    Output = @($output)
  }

  $json = $null
  if (-not $result.TimedOut -and $result.ExitCode -eq 0) {
    try {
      $json = (($result.Output -join "`n") | ConvertFrom-Json -ErrorAction Stop)
    } catch {}
  }

  return [pscustomobject]@{
    Available = $true
    Success = (-not $result.TimedOut -and $result.ExitCode -eq 0)
    ExitCode = $result.ExitCode
    Output = $result.Output
    Json = $json
  }
}

function Get-TailscaleFunnelStatus {
  $cliPath = Get-TailscaleCliPath
  $paths = Get-TailscaleFunnelPaths
  $version = if ($cliPath) { Get-CommandVersionText -FilePath $cliPath -Arguments @("version") } else { $null }
  $statusResult = Invoke-TailscaleJsonCommand -Arguments @("status", "--json")
  $backendState = $null
  $dnsName = $null
  if ($statusResult.Json) {
    $backendState = $statusResult.Json.BackendState
    if ($statusResult.Json.Self -and $statusResult.Json.Self.DNSName) {
      $dnsName = ([string]$statusResult.Json.Self.DNSName).TrimEnd(".")
    }
  }

  $funnelResult = Invoke-TailscaleJsonCommand -Arguments @("funnel", "status", "--json")
  $urls = @()
  if ($funnelResult.Json) {
    $urls += Find-UrlsInObject -Value $funnelResult.Json
  }

  $blockingReason = $null
  $nextStep = $null
  if (-not $cliPath) {
    $blockingReason = "Tailscale no esta instalado en este equipo."
    $nextStep = "Instala Tailscale para usar Funnel."
  } elseif (-not $statusResult.Success) {
    $blockingReason = "Tailscale no esta listo todavia."
    $nextStep = "Tailscale no esta listo todavia. Ejecuta 'tailscale up' y asegurate de iniciar sesion."
  } elseif ($backendState -and $backendState -ne "Running") {
    $blockingReason = "Tailscale existe, pero no esta conectado."
    $nextStep = "Tailscale existe, pero no esta conectado. Ejecuta 'tailscale up'."
  } elseif (-not $funnelResult.Success) {
    $blockingReason = "Tailscale esta conectado, pero Funnel aun no esta listo."
    $nextStep = "Tailscale esta conectado, pero Funnel aun no esta listo. Revisa permisos y vuelve a ejecutar el start."
  } elseif ($urls.Count -eq 0) {
    $blockingReason = "Tailscale esta conectado, pero Funnel publico aun no esta activado."
    $nextStep = "Vuelve a lanzar Tailscale Funnel o revisa si tu tailnet permite Funnel publico."
  }

  return [pscustomobject]@{
    Provider = "tailscale"
    DisplayName = "Tailscale Funnel"
    Installed = [bool]$cliPath
    CliPath = $cliPath
    Version = $version
    Running = [bool]($funnelResult.Success -and $urls.Count -gt 0)
    HasPidFile = $false
    ProcessId = $null
    ProcessName = "tailscaled"
    BackendState = $backendState
    DnsName = $dnsName
    PublicUrl = if ($urls.Count -gt 0) { $urls[0] } else { $null }
    Ready = [bool]($funnelResult.Success -and $urls.Count -gt 0)
    BlockingReason = $blockingReason
    NextStep = $nextStep
    RawStatusOutput = $statusResult.Output
    RawFunnelOutput = $funnelResult.Output
    Paths = $paths
  }
}

function Start-TailscaleFunnel {
  $status = Get-TailscaleFunnelStatus
  if (-not $status.Installed) {
    return $status
  }

  if ($status.BackendState -and $status.BackendState -ne "Running") {
    return $status
  }

  $paths = $status.Paths
  if (Test-Path $paths.OutLog) { Remove-Item $paths.OutLog -Force -ErrorAction SilentlyContinue }
  if (Test-Path $paths.ErrLog) { Remove-Item $paths.ErrLog -Force -ErrorAction SilentlyContinue }

  $result = Invoke-CommandWithTimeout -FilePath $status.CliPath -Arguments @("funnel", "--bg", "3000") -TimeoutSeconds 30
  Set-Content -Path $paths.OutLog -Value $result.Output -Encoding ASCII

  $current = Get-TailscaleFunnelStatus
  if ($current.Ready) {
    Write-StableTunnelState -State ([pscustomobject]@{
      Provider = "tailscale"
      StartedAt = (Get-Date).ToString("s")
      Mode = "funnel"
      PublicUrl = $current.PublicUrl
    }) | Out-Null
  }

  return $current
}

function Stop-TailscaleFunnel {
  $status = Get-TailscaleFunnelStatus
  if (-not $status.Installed) {
    return [pscustomobject]@{
      Provider = "tailscale"
      WasRunning = $false
    }
  }

  $result = Invoke-CommandWithTimeout -FilePath $status.CliPath -Arguments @("funnel", "reset") -TimeoutSeconds 20
  if (Test-Path $status.Paths.OutLog) {
    Remove-Item $status.Paths.OutLog -Force -ErrorAction SilentlyContinue
  }
  if (Test-Path $status.Paths.ErrLog) {
    Remove-Item $status.Paths.ErrLog -Force -ErrorAction SilentlyContinue
  }

  return [pscustomobject]@{
    Provider = "tailscale"
    WasRunning = $status.Running
    ExitCode = $result.ExitCode
    Stopped = $true
  }
}

function Get-StableTunnelStatus {
  $localApp = Get-LocalAppStatus
  $cloudflare = Get-CloudflareTunnelStatus
  $tailscale = Get-TailscaleFunnelStatus
  $state = Read-StableTunnelState

  $activeProvider = $null
  $active = $null
  if ($cloudflare.Ready) {
    $activeProvider = "cloudflare"
    $active = $cloudflare
  } elseif ($tailscale.Ready) {
    $activeProvider = "tailscale"
    $active = $tailscale
  } elseif ($state -and $state.Provider -eq "cloudflare") {
    $activeProvider = "cloudflare"
    $active = $cloudflare
  } elseif ($state -and $state.Provider -eq "tailscale") {
    $activeProvider = "tailscale"
    $active = $tailscale
  }

  $summary = $null
  $nextStep = $null
  if (-not $localApp.FrontendReady) {
    $summary = "El frontend local no esta levantado."
    $nextStep = "Inicia VIRU localmente antes de abrir un tunel."
  } elseif (-not $localApp.BackendReady) {
    $summary = "El backend local no esta levantado."
    $nextStep = "Inicia VIRU localmente antes de abrir un tunel."
  } elseif ($cloudflare.Ready) {
    $summary = "Cloudflare Tunnel esta activo."
    if ($cloudflare.Mode -eq "quick") {
      $nextStep = "Si quieres dominio propio, prepara infra/cloudflare-tunnel.local.yml y vuelve a publicar."
    }
  } elseif ($tailscale.Ready) {
    $summary = "Tailscale Funnel esta activo."
    $nextStep = "Puedes dejarlo asi o volver a Cloudflare Tunnel cuando quieras dominio gestionado por Cloudflare."
  } elseif ($cloudflare.Installed) {
    $summary = "Cloudflare Tunnel es la via estable recomendada y aun no esta activo."
    $nextStep = if ($cloudflare.NextStep) { $cloudflare.NextStep } else { "Arranca PUBLICAR WEB ESTABLE para abrir el tunel." }
  } elseif ($tailscale.Installed) {
    $summary = "Cloudflare no esta disponible en esta maquina y Tailscale queda como alternativa."
    $nextStep = if ($tailscale.NextStep) { $tailscale.NextStep } else { "Arranca Tailscale Funnel desde el panel." }
  } else {
    $summary = "No hay ningun proveedor de tunel listo en esta maquina."
    $nextStep = "Instala cloudflared o Tailscale para poder publicar la web."
  }

  return [pscustomobject]@{
    LocalApp = $localApp
    Cloudflare = $cloudflare
    Tailscale = $tailscale
    ActiveProvider = $activeProvider
    Active = $active
    Ready = [bool]($active -and $active.Ready)
    PublicUrl = if ($active) { $active.PublicUrl } else { $null }
    Summary = $summary
    NextStep = $nextStep
  }
}

function Stop-StableTunnel {
  $cloudflare = Stop-CloudflareTunnel
  $tailscale = Stop-TailscaleFunnel
  Clear-StableTunnelState

  return [pscustomobject]@{
    Cloudflare = $cloudflare
    Tailscale = $tailscale
    StoppedProvider = if ($cloudflare.WasRunning -or $cloudflare.HadPidFile) { "cloudflare" } elseif ($tailscale.WasRunning) { "tailscale" } else { $null }
  }
}
