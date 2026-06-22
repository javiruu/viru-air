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

function Get-PublicStableNetworkProfilesPath {
  return (Join-Path (Get-InfraDir) "public-stable-network-profiles.json")
}

function Get-LegacyPublicStableNetworkStatePath {
  return (Join-Path (Get-InfraDir) "public-stable-network-state.json")
}

function Get-PublicStableNetworkStatePath {
  return (Get-PublicStableNetworkProfilesPath)
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

function Get-CurrentNetworkContext {
  $route = $null
  try {
    $route = Get-NetRoute -DestinationPrefix "0.0.0.0/0" -ErrorAction Stop |
      Sort-Object RouteMetric, InterfaceMetric |
      Select-Object -First 1
  } catch {}

  $localIp = Get-PreferredLocalIPv4
  $ipRow = $null
  if ($route) {
    $ipRow = Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex $route.InterfaceIndex -ErrorAction SilentlyContinue |
      Where-Object { $_.IPAddress -eq $localIp } |
      Select-Object -First 1
  }
  if (-not $ipRow -and $localIp) {
    $ipRow = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
      Where-Object { $_.IPAddress -eq $localIp } |
      Select-Object -First 1
  }

  $subnetHint = $null
  if ($localIp -match '^(\d+\.\d+\.\d+)\.\d+$') {
    $subnetHint = "$($Matches[1]).x"
  }

  return [pscustomobject]@{
    LocalIp = $localIp
    Gateway = if ($route) { $route.NextHop } else { $null }
    InterfaceAlias = if ($route) { $route.InterfaceAlias } elseif ($ipRow) { $ipRow.InterfaceAlias } else { $null }
    InterfaceIndex = if ($route) { $route.InterfaceIndex } elseif ($ipRow) { $ipRow.InterfaceIndex } else { $null }
    PrefixLength = if ($ipRow) { $ipRow.PrefixLength } else { $null }
    SubnetHint = $subnetHint
  }
}

function Test-SameIpv4SubnetHint {
  param(
    [string]$LeftIp,
    [string]$RightIp
  )

  if (-not $LeftIp -or -not $RightIp) {
    return $false
  }

  if ($LeftIp -match '^(\d+\.\d+\.\d+)\.\d+$' -and $RightIp -match '^(\d+\.\d+\.\d+)\.\d+$') {
    return ($Matches[1] -eq ([regex]::Match($RightIp, '^(\d+\.\d+\.\d+)\.\d+$').Groups[1].Value))
  }

  return $false
}

function Get-ObjectPropertyValue {
  param(
    $Object,
    [Parameter(Mandatory)][string]$Name,
    $Default = $null
  )

  if ($null -eq $Object) {
    return $Default
  }

  $property = $Object.PSObject.Properties[$Name]
  if ($property) {
    return $property.Value
  }

  return $Default
}

function New-EmptyPublicStableNetworkProfilesState {
  return [pscustomobject]@{
    schemaVersion = 3
    activeProfileId = "auto"
    profiles = @()
  }
}

function Normalize-StableNetworkProfile {
  param([Parameter(Mandatory)]$Profile)

  $profileIdValue = Get-ObjectPropertyValue -Object $Profile -Name "id"
  $legacyProfileIdValue = Get-ObjectPropertyValue -Object $Profile -Name "profileId"
  $expectedPcIpValue = Get-ObjectPropertyValue -Object $Profile -Name "expectedPcIp"
  $expectedLocalIpValue = Get-ObjectPropertyValue -Object $Profile -Name "expectedLocalIp"
  $expectedGatewayValue = Get-ObjectPropertyValue -Object $Profile -Name "expectedGateway"
  $expectedSubnetHintValue = Get-ObjectPropertyValue -Object $Profile -Name "expectedSubnetHint"
  $intermediateRouterIpValue = Get-ObjectPropertyValue -Object $Profile -Name "intermediateRouterIp"
  $expectedUpnpExternalIpValue = Get-ObjectPropertyValue -Object $Profile -Name "expectedUpnpExternalIp"

  $id = if ($profileIdValue) { [string]$profileIdValue } elseif ($legacyProfileIdValue) { [string]$legacyProfileIdValue } else { $null }
  if (-not $id) {
    $id = [guid]::NewGuid().ToString("N")
  }

  $expectedPcIp = if ($expectedPcIpValue) { [string]$expectedPcIpValue } elseif ($expectedLocalIpValue) { [string]$expectedLocalIpValue } else { $null }
  $expectedGateway = if ($expectedGatewayValue) { [string]$expectedGatewayValue } else { $null }
  $expectedSubnetHint = if ($expectedSubnetHintValue) { [string]$expectedSubnetHintValue } else {
    if ($expectedPcIp -match '^(\d+\.\d+\.\d+)\.\d+$') { "$($Matches[1]).x" } else { $null }
  }
  $intermediateRouterIp = if ($intermediateRouterIpValue) { [string]$intermediateRouterIpValue } elseif ($expectedUpnpExternalIpValue) { [string]$expectedUpnpExternalIpValue } else { $null }

  return [pscustomobject]@{
    id = $id
    label = if (Get-ObjectPropertyValue -Object $Profile -Name "label") { [string](Get-ObjectPropertyValue -Object $Profile -Name "label") } else { $id }
    domain = if (Get-ObjectPropertyValue -Object $Profile -Name "domain") { [string](Get-ObjectPropertyValue -Object $Profile -Name "domain") } else { $null }
    expectedPcIp = $expectedPcIp
    expectedGateway = $expectedGateway
    expectedInterfaceAlias = if (Get-ObjectPropertyValue -Object $Profile -Name "expectedInterfaceAlias") { [string](Get-ObjectPropertyValue -Object $Profile -Name "expectedInterfaceAlias") } else { $null }
    expectedSubnetHint = $expectedSubnetHint
    upstreamRouterIp = if (Get-ObjectPropertyValue -Object $Profile -Name "upstreamRouterIp") { [string](Get-ObjectPropertyValue -Object $Profile -Name "upstreamRouterIp") } else { $null }
    intermediateRouterIp = $intermediateRouterIp
    expectedPublicIp = if (Get-ObjectPropertyValue -Object $Profile -Name "expectedPublicIp") { [string](Get-ObjectPropertyValue -Object $Profile -Name "expectedPublicIp") } else { $null }
    expectedUpnpMappings = @((Get-ObjectPropertyValue -Object $Profile -Name "expectedUpnpMappings" -Default @()))
    mode = if (Get-ObjectPropertyValue -Object $Profile -Name "mode") { [string](Get-ObjectPropertyValue -Object $Profile -Name "mode") } else { "unknown" }
    notes = if (Get-ObjectPropertyValue -Object $Profile -Name "notes") { [string](Get-ObjectPropertyValue -Object $Profile -Name "notes") } else { $null }
    createdAt = if (Get-ObjectPropertyValue -Object $Profile -Name "createdAt") { [string](Get-ObjectPropertyValue -Object $Profile -Name "createdAt") } elseif (Get-ObjectPropertyValue -Object $Profile -Name "savedAt") { [string](Get-ObjectPropertyValue -Object $Profile -Name "savedAt") } else { $null }
    lastSeenAt = if (Get-ObjectPropertyValue -Object $Profile -Name "lastSeenAt") { [string](Get-ObjectPropertyValue -Object $Profile -Name "lastSeenAt") } elseif (Get-ObjectPropertyValue -Object $Profile -Name "savedAt") { [string](Get-ObjectPropertyValue -Object $Profile -Name "savedAt") } else { $null }
    lastSeenPublicIp = if (Get-ObjectPropertyValue -Object $Profile -Name "lastSeenPublicIp") { [string](Get-ObjectPropertyValue -Object $Profile -Name "lastSeenPublicIp") } elseif (Get-ObjectPropertyValue -Object $Profile -Name "expectedPublicIp") { [string](Get-ObjectPropertyValue -Object $Profile -Name "expectedPublicIp") } else { $null }
    lastSeenUpnpExternalIp = if (Get-ObjectPropertyValue -Object $Profile -Name "lastSeenUpnpExternalIp") { [string](Get-ObjectPropertyValue -Object $Profile -Name "lastSeenUpnpExternalIp") } elseif ($expectedUpnpExternalIpValue) { [string]$expectedUpnpExternalIpValue } else { $null }
    lastSeenInterfaceAlias = if (Get-ObjectPropertyValue -Object $Profile -Name "lastSeenInterfaceAlias") { [string](Get-ObjectPropertyValue -Object $Profile -Name "lastSeenInterfaceAlias") } elseif (Get-ObjectPropertyValue -Object $Profile -Name "expectedInterfaceAlias") { [string](Get-ObjectPropertyValue -Object $Profile -Name "expectedInterfaceAlias") } else { $null }
    lastSeenSubnetHint = if (Get-ObjectPropertyValue -Object $Profile -Name "lastSeenSubnetHint") { [string](Get-ObjectPropertyValue -Object $Profile -Name "lastSeenSubnetHint") } else { $expectedSubnetHint }
  }
}

function Convert-LegacyStableNetworkStateToProfilesState {
  param([Parameter(Mandatory)]$LegacyState)

  $profile = Normalize-StableNetworkProfile -Profile ([pscustomobject]@{
    id = if (Get-ObjectPropertyValue -Object $LegacyState -Name "profileId") { Get-ObjectPropertyValue -Object $LegacyState -Name "profileId" } else { "legacy-default" }
    label = if (Get-ObjectPropertyValue -Object $LegacyState -Name "domain") { "legacy-$(Get-ObjectPropertyValue -Object $LegacyState -Name 'domain')" } else { "legacy-default" }
    domain = Get-ObjectPropertyValue -Object $LegacyState -Name "domain"
    expectedPcIp = Get-ObjectPropertyValue -Object $LegacyState -Name "expectedLocalIp"
    expectedGateway = Get-ObjectPropertyValue -Object $LegacyState -Name "expectedGateway"
    expectedInterfaceAlias = Get-ObjectPropertyValue -Object $LegacyState -Name "expectedInterfaceAlias"
    expectedSubnetHint = Get-ObjectPropertyValue -Object $LegacyState -Name "expectedSubnetHint"
    expectedPublicIp = Get-ObjectPropertyValue -Object $LegacyState -Name "expectedPublicIp"
    intermediateRouterIp = Get-ObjectPropertyValue -Object $LegacyState -Name "expectedUpnpExternalIp"
    expectedUpnpMappings = Get-ObjectPropertyValue -Object $LegacyState -Name "expectedUpnpMappings" -Default @()
    createdAt = Get-ObjectPropertyValue -Object $LegacyState -Name "savedAt"
    lastSeenAt = Get-ObjectPropertyValue -Object $LegacyState -Name "savedAt"
    mode = if (Get-ObjectPropertyValue -Object $LegacyState -Name "expectedUpnpExternalIp") { "double_nat" } else { "unknown" }
    notes = "Importado automaticamente desde el formato antiguo."
  })

  return [pscustomobject]@{
    schemaVersion = 3
    activeProfileId = "auto"
    profiles = @($profile)
  }
}

function Read-RawStableNetworkProfilesFile {
  param([switch]$AllowMissing)

  $profilesPath = Get-PublicStableNetworkProfilesPath
  $legacyPath = Get-LegacyPublicStableNetworkStatePath
  $sourcePath = $null

  if (Test-Path $profilesPath) {
    $sourcePath = $profilesPath
  } elseif (Test-Path $legacyPath) {
    $sourcePath = $legacyPath
  }

  if (-not $sourcePath) {
    if ($AllowMissing) {
      return $null
    }
    throw "No existe la configuracion de perfiles de red estable."
  }

  try {
    $raw = Get-Content -Path $sourcePath -Raw -ErrorAction Stop
    if (-not $raw.Trim()) {
      return $null
    }
    return ($raw | ConvertFrom-Json -ErrorAction Stop)
  } catch {
    return $null
  }
}

function Read-PublicStableNetworkProfiles {
  param([switch]$AllowMissing)

  $parsed = Read-RawStableNetworkProfilesFile -AllowMissing:$AllowMissing
  if (-not $parsed) {
    return $null
  }

  if ($parsed.PSObject.Properties.Name -contains "profiles") {
    $profiles = @()
    foreach ($profile in @($parsed.profiles)) {
      $profiles += (Normalize-StableNetworkProfile -Profile $profile)
    }

    return [pscustomobject]@{
      schemaVersion = if ($parsed.schemaVersion) { [int]$parsed.schemaVersion } else { 3 }
      activeProfileId = if ($parsed.activeProfileId) { [string]$parsed.activeProfileId } else { "auto" }
      profiles = $profiles
    }
  }

  return (Convert-LegacyStableNetworkStateToProfilesState -LegacyState $parsed)
}

function Write-PublicStableNetworkProfiles {
  param([Parameter(Mandatory)]$State)

  $normalizedProfiles = @()
  foreach ($profile in @($State.profiles)) {
    $normalizedProfiles += (Normalize-StableNetworkProfile -Profile $profile)
  }

  $normalizedState = [pscustomobject]@{
    schemaVersion = 3
    activeProfileId = if ($State.activeProfileId) { [string]$State.activeProfileId } else { "auto" }
    profiles = $normalizedProfiles
  }

  $path = Get-PublicStableNetworkProfilesPath
  $json = $normalizedState | ConvertTo-Json -Depth 8
  Set-Content -Path $path -Value $json -Encoding ASCII
  return $path
}

function Read-PublicStableNetworkState {
  param([switch]$AllowMissing)
  return (Read-PublicStableNetworkProfiles -AllowMissing:$AllowMissing)
}

function Write-PublicStableNetworkState {
  param([Parameter(Mandatory)]$State)
  return (Write-PublicStableNetworkProfiles -State $State)
}

function Get-StableNetworkMode {
  param(
    [Parameter(Mandatory)]$CurrentNetwork,
    [Parameter(Mandatory)]$EdgeStatus
  )

  if ($EdgeStatus.UpnpExternalIp -and (Test-IsPrivateIPv4 -IpAddress $EdgeStatus.UpnpExternalIp) -and $CurrentNetwork.LocalIp -and -not (Test-SameIpv4SubnetHint -LeftIp $CurrentNetwork.LocalIp -RightIp $EdgeStatus.UpnpExternalIp)) {
    return "double_nat"
  }

  if ($CurrentNetwork.LocalIp -and $CurrentNetwork.Gateway -and (Test-SameIpv4SubnetHint -LeftIp $CurrentNetwork.LocalIp -RightIp $CurrentNetwork.Gateway)) {
    return "direct_router"
  }

  return "unknown"
}

function New-StableNetworkProfileId {
  param(
    [Parameter(Mandatory)]$CurrentNetwork,
    [Parameter(Mandatory)]$EdgeStatus,
    [string]$Label
  )

  $base = if ($Label) { $Label } elseif ($CurrentNetwork.SubnetHint) { $CurrentNetwork.SubnetHint } elseif ($CurrentNetwork.LocalIp) { $CurrentNetwork.LocalIp } else { "red" }
  $gateway = if ($CurrentNetwork.Gateway) { $CurrentNetwork.Gateway } else { "sin-gateway" }
  $mode = Get-StableNetworkMode -CurrentNetwork $CurrentNetwork -EdgeStatus $EdgeStatus
  return ((($base + "-" + $gateway + "-" + $mode).ToLowerInvariant()) -replace '[^a-z0-9\.\-]', '-')
}

function Get-DefaultStableNetworkProfileLabel {
  param(
    [Parameter(Mandatory)]$CurrentNetwork,
    [Parameter(Mandatory)]$EdgeStatus
  )

  $mode = Get-StableNetworkMode -CurrentNetwork $CurrentNetwork -EdgeStatus $EdgeStatus
  switch ($mode) {
    "direct_router" {
      if ($CurrentNetwork.SubnetHint) {
        return "Red $($CurrentNetwork.SubnetHint) directa"
      }
      return "Red directa"
    }
    "double_nat" {
      if ($CurrentNetwork.SubnetHint) {
        return "Red $($CurrentNetwork.SubnetHint) con router intermedio"
      }
      return "Red con router intermedio"
    }
    default {
      if ($CurrentNetwork.SubnetHint) {
        return "Red $($CurrentNetwork.SubnetHint)"
      }
      return "Red nueva"
    }
  }
}

function New-StableNetworkProfileFromCurrentNetwork {
  param(
    [Parameter(Mandatory)][string]$Domain,
    [Parameter(Mandatory)]$CurrentNetwork,
    [Parameter(Mandatory)]$EdgeStatus,
    [string]$Label,
    [string]$ProfileId,
    [string]$Notes
  )

  $timestamp = (Get-Date).ToString("s")
  $mode = Get-StableNetworkMode -CurrentNetwork $CurrentNetwork -EdgeStatus $EdgeStatus
  $tcpMappings = @($EdgeStatus.UpnpMappings | Where-Object { $_.Protocol -eq "TCP" -and $_.ExternalPort -in @(80, 443) })
  $resolvedLabel = if ($Label) { $Label } else { Get-DefaultStableNetworkProfileLabel -CurrentNetwork $CurrentNetwork -EdgeStatus $EdgeStatus }
  $resolvedId = if ($ProfileId) { $ProfileId } else { New-StableNetworkProfileId -CurrentNetwork $CurrentNetwork -EdgeStatus $EdgeStatus -Label $resolvedLabel }

  return [pscustomobject]@{
    id = $resolvedId
    label = $resolvedLabel
    domain = $Domain
    expectedPcIp = $CurrentNetwork.LocalIp
    expectedGateway = $CurrentNetwork.Gateway
    expectedInterfaceAlias = $CurrentNetwork.InterfaceAlias
    expectedSubnetHint = $CurrentNetwork.SubnetHint
    upstreamRouterIp = $null
    intermediateRouterIp = if ($mode -eq "double_nat") { $EdgeStatus.UpnpExternalIp } else { $null }
    expectedPublicIp = $EdgeStatus.PublicIp
    expectedUpnpMappings = @($tcpMappings | ForEach-Object {
      [pscustomobject]@{
        protocol = (Get-ObjectPropertyValue -Object $_ -Name "Protocol")
        externalPort = (Get-ObjectPropertyValue -Object $_ -Name "ExternalPort")
        internalPort = (Get-ObjectPropertyValue -Object $_ -Name "InternalPort")
        internalClient = (Get-ObjectPropertyValue -Object $_ -Name "InternalClient")
        externalIPAddress = (Get-ObjectPropertyValue -Object $_ -Name "ExternalIPAddress")
        description = (Get-ObjectPropertyValue -Object $_ -Name "Description")
      }
    })
    mode = $mode
    notes = $Notes
    createdAt = $timestamp
    lastSeenAt = $timestamp
    lastSeenPublicIp = $EdgeStatus.PublicIp
    lastSeenUpnpExternalIp = $EdgeStatus.UpnpExternalIp
    lastSeenInterfaceAlias = $CurrentNetwork.InterfaceAlias
    lastSeenSubnetHint = $CurrentNetwork.SubnetHint
  }
}

function Get-StableNetworkProfileById {
  param(
    $ProfilesState,
    [string]$ProfileId
  )

  if (-not $ProfilesState -or -not $ProfileId) {
    return $null
  }

  foreach ($profile in @($ProfilesState.profiles)) {
    $normalized = Normalize-StableNetworkProfile -Profile $profile
    if ($normalized.id -eq $ProfileId) {
      return $normalized
    }
  }

  return $null
}

function Test-StableNetworkProfileMatch {
  param(
    [Parameter(Mandatory)]$Profile,
    [Parameter(Mandatory)]$CurrentNetwork,
    [Parameter(Mandatory)]$EdgeStatus,
    [string]$Domain
  )

  $currentMode = Get-StableNetworkMode -CurrentNetwork $CurrentNetwork -EdgeStatus $EdgeStatus
  $score = 0
  $hasIdentity = $false

  if ($Profile.domain) {
    if ($Domain -and $Profile.domain -eq $Domain) {
      $score += 2
    } elseif ($Domain) {
      return [pscustomobject]@{ IsMatch = $false; Score = 0; CurrentMode = $currentMode }
    }
  }

  if ($Profile.expectedPcIp) {
    $hasIdentity = $true
    if ($CurrentNetwork.LocalIp -and $Profile.expectedPcIp -eq $CurrentNetwork.LocalIp) {
      $score += 6
    } else {
      return [pscustomobject]@{ IsMatch = $false; Score = 0; CurrentMode = $currentMode }
    }
  }

  if ($Profile.expectedGateway) {
    $hasIdentity = $true
    if ($CurrentNetwork.Gateway -and $Profile.expectedGateway -eq $CurrentNetwork.Gateway) {
      $score += 5
    } else {
      return [pscustomobject]@{ IsMatch = $false; Score = 0; CurrentMode = $currentMode }
    }
  }

  if ($Profile.expectedSubnetHint) {
    $hasIdentity = $true
    if ($CurrentNetwork.SubnetHint -and $Profile.expectedSubnetHint -eq $CurrentNetwork.SubnetHint) {
      $score += 3
    } elseif ($Profile.expectedPcIp -and $CurrentNetwork.LocalIp -and (Test-SameIpv4SubnetHint -LeftIp $Profile.expectedPcIp -RightIp $CurrentNetwork.LocalIp)) {
      $score += 2
    } else {
      return [pscustomobject]@{ IsMatch = $false; Score = 0; CurrentMode = $currentMode }
    }
  }

  if ($Profile.intermediateRouterIp) {
    $hasIdentity = $true
    if ($EdgeStatus.UpnpExternalIp -and $Profile.intermediateRouterIp -eq $EdgeStatus.UpnpExternalIp) {
      $score += 4
    }
  }

  if ($Profile.mode -and $Profile.mode -ne "unknown" -and $Profile.mode -eq $currentMode) {
    $score += 2
  }

  if ($Profile.expectedPublicIp -and $EdgeStatus.PublicIp -and $Profile.expectedPublicIp -eq $EdgeStatus.PublicIp) {
    $score += 1
  }

  return [pscustomobject]@{
    IsMatch = ($hasIdentity -and $score -gt 0)
    Score = $score
    CurrentMode = $currentMode
  }
}

function Select-BestStableNetworkProfile {
  param(
    $ProfilesState,
    [Parameter(Mandatory)]$CurrentNetwork,
    [Parameter(Mandatory)]$EdgeStatus,
    [string]$Domain
  )

  if (-not $ProfilesState -or -not $ProfilesState.profiles) {
    return $null
  }

  $best = $null
  foreach ($profile in @($ProfilesState.profiles)) {
    $normalizedProfile = Normalize-StableNetworkProfile -Profile $profile
    $result = Test-StableNetworkProfileMatch -Profile $normalizedProfile -CurrentNetwork $CurrentNetwork -EdgeStatus $EdgeStatus -Domain $Domain
    if (-not $result.IsMatch) {
      continue
    }

    $candidate = [pscustomobject]@{
      Profile = $normalizedProfile
      Score = $result.Score
      CurrentMode = $result.CurrentMode
    }

    if (-not $best -or $candidate.Score -gt $best.Score) {
      $best = $candidate
    }
  }

  return $best
}

function Set-ActivePublicStableNetworkProfile {
  param([Parameter(Mandatory)][string]$ProfileId)

  $state = Read-PublicStableNetworkProfiles -AllowMissing
  if (-not $state) {
    $state = New-EmptyPublicStableNetworkProfilesState
  }

  if ($ProfileId -ne "auto" -and -not (Get-StableNetworkProfileById -ProfilesState $state -ProfileId $ProfileId)) {
    throw "No existe el perfil $ProfileId."
  }

  $state.activeProfileId = $ProfileId
  return (Write-PublicStableNetworkProfiles -State $state)
}

function Save-PublicStableNetworkProfile {
  param(
    [Parameter(Mandatory)][string]$Domain,
    [Parameter(Mandatory)]$CurrentNetwork,
    [Parameter(Mandatory)]$EdgeStatus,
    [string]$Label,
    [string]$ProfileId,
    [string]$Notes,
    [switch]$SetActive,
    [switch]$UpdateExisting
  )

  $state = Read-PublicStableNetworkProfiles -AllowMissing
  if (-not $state) {
    $state = New-EmptyPublicStableNetworkProfilesState
  }

  $newProfile = New-StableNetworkProfileFromCurrentNetwork -Domain $Domain -CurrentNetwork $CurrentNetwork -EdgeStatus $EdgeStatus -Label $Label -ProfileId $ProfileId -Notes $Notes
  $existing = Get-StableNetworkProfileById -ProfilesState $state -ProfileId $newProfile.id
  if ($existing -and -not $UpdateExisting) {
    throw "Ya existe un perfil con id $($newProfile.id). Usa otro nombre o activa la actualizacion explicita."
  }

  $profiles = New-Object System.Collections.ArrayList
  foreach ($profile in @($state.profiles)) {
    if ($profile.id -ne $newProfile.id) {
      [void]$profiles.Add($profile)
    }
  }
  [void]$profiles.Add($newProfile)
  $state.profiles = @($profiles)
  if ($SetActive) {
    $state.activeProfileId = $newProfile.id
  }

  $path = Write-PublicStableNetworkProfiles -State $state
  return [pscustomobject]@{
    Path = $path
    Profile = $newProfile
    ReplacedExisting = [bool]$existing
  }
}

function Save-PublicStableNetworkState {
  param(
    [Parameter(Mandatory)][string]$Domain,
    [Parameter(Mandatory)]$CurrentNetwork,
    [Parameter(Mandatory)]$EdgeStatus
  )

  $result = Save-PublicStableNetworkProfile -Domain $Domain -CurrentNetwork $CurrentNetwork -EdgeStatus $EdgeStatus -SetActive -UpdateExisting
  return $result.Path
}

function Get-CaddyAcmeFailureDiagnostic {
  $paths = Get-CaddyManagedPaths
  if (-not (Test-Path $paths.ErrLog)) {
    return $null
  }

  $lines = @(Get-Content -Path $paths.ErrLog -Tail 200 -ErrorAction SilentlyContinue)
  if ($lines.Count -eq 0) {
    return $null
  }

  $joined = $lines -join "`n"
  $hasTimeout = ($joined -match "Timeout during connect")
  $hasHttp01 = ($joined -match "http-01")
  $hasTlsAlpn = ($joined -match "tls-alpn-01")

  return [pscustomobject]@{
    HasTimeout = $hasTimeout
    HasHttp01Failure = $hasHttp01
    HasTlsAlpnFailure = $hasTlsAlpn
    Summary = if ($hasTimeout) { "Let's Encrypt no puede entrar desde Internet a 80/443." } else { $null }
  }
}

function Test-LocalStableHttpReachability {
  param([string]$Domain)

  if (-not $Domain) {
    return [pscustomobject]@{
      Success = $false
      StatusCode = $null
      Server = $null
      Location = $null
      Error = "No hay dominio para probar HTTP local."
    }
  }

  try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1/" -Headers @{ Host = $Domain } -MaximumRedirection 0 -TimeoutSec 10
    return [pscustomobject]@{
      Success = $true
      StatusCode = [int]$response.StatusCode
      Server = [string]$response.Headers["Server"]
      Location = [string]$response.Headers["Location"]
      Error = $null
    }
  } catch {
    $httpResponse = $_.Exception.Response
    if ($httpResponse) {
      return [pscustomobject]@{
        Success = $true
        StatusCode = [int]$httpResponse.StatusCode.value__
        Server = [string]$httpResponse.Headers["Server"]
        Location = [string]$httpResponse.Headers["Location"]
        Error = $_.Exception.Message
      }
    }

    return [pscustomobject]@{
      Success = $false
      StatusCode = $null
      Server = $null
      Location = $null
      Error = $_.Exception.Message
    }
  }
}

function Get-LocalFirewallHttpEvidence {
  $rules = @()
  try {
    $rules = @(Get-NetFirewallRule -Enabled True -Direction Inbound -Action Allow -ErrorAction Stop |
      Where-Object { $_.DisplayName -match 'caddy|80|443|http|https|viru' })
  } catch {
    $rules = @()
  }

  return [pscustomobject]@{
    AllowRules = $rules
    HasAllowEvidence = ($rules.Count -gt 0)
  }
}

function Get-StablePublishNetworkDiagnosis {
  param(
    [Parameter(Mandatory)]$EdgeStatus,
    [Parameter(Mandatory)]$CaddyStatus,
    [string]$Domain,
    $CurrentNetworkOverride,
    $ProfilesStateOverride,
    $AcmeOverride
  )

  $current = if ($PSBoundParameters.ContainsKey("CurrentNetworkOverride") -and $null -ne $CurrentNetworkOverride) { $CurrentNetworkOverride } else { Get-CurrentNetworkContext }
  $profilesState = if ($PSBoundParameters.ContainsKey("ProfilesStateOverride")) { $ProfilesStateOverride } else { Read-PublicStableNetworkProfiles -AllowMissing }
  $acme = if ($PSBoundParameters.ContainsKey("AcmeOverride")) { $AcmeOverride } else { Get-CaddyAcmeFailureDiagnostic }
  $localHttp = Test-LocalStableHttpReachability -Domain $Domain
  $localFirewall = Get-LocalFirewallHttpEvidence
  $currentMode = Get-StableNetworkMode -CurrentNetwork $current -EdgeStatus $EdgeStatus
  $detectedMatch = Select-BestStableNetworkProfile -ProfilesState $profilesState -CurrentNetwork $current -EdgeStatus $EdgeStatus -Domain $Domain
  $detectedProfile = if ($detectedMatch) { $detectedMatch.Profile } else { $null }
  $activeProfileId = if ($profilesState -and $profilesState.activeProfileId) { [string]$profilesState.activeProfileId } else { "auto" }
  $activeProfile = if ($activeProfileId -and $activeProfileId -ne "auto") { Get-StableNetworkProfileById -ProfilesState $profilesState -ProfileId $activeProfileId } else { $null }
  $activeProfileMatch = $null
  if ($activeProfile) {
    $activeProfileMatch = Test-StableNetworkProfileMatch -Profile $activeProfile -CurrentNetwork $current -EdgeStatus $EdgeStatus -Domain $Domain
  }

  $tcpMappings = @($EdgeStatus.UpnpMappings | Where-Object { $_.Protocol -eq "TCP" -and $_.ExternalPort -in @(80, 443) })
  $mappedTargetIp = $null
  $uniqueTargets = @($tcpMappings | Select-Object -ExpandProperty InternalClient -Unique)
  if ($uniqueTargets.Count -eq 1) {
    $mappedTargetIp = $uniqueTargets[0]
  }

  $publicRouteHitsCurrentPc = [bool]($current.LocalIp -and $mappedTargetIp -and $mappedTargetIp -eq $current.LocalIp)
  $publicRouteEvidence = ($publicRouteHitsCurrentPc -or $CaddyStatus.TlsReady -or ($acme -and $acme.HasTimeout))
  $manualProfileMismatch = [bool]($activeProfileId -ne "auto" -and $activeProfile -and (-not $activeProfileMatch -or -not $activeProfileMatch.IsMatch))
  $isNewNetwork = (-not $detectedProfile)
  $caseCode = $null
  $summary = $null
  $nextStep = $null
  $details = @()

  if ($current.LocalIp) {
    $details += "IP de este PC: $($current.LocalIp)"
  }
  if ($current.Gateway) {
    $details += "Router actual: $($current.Gateway)"
  }
  if ($detectedProfile) {
    $details += "Perfil de red detectado: $($detectedProfile.label)"
  }
  if ($activeProfile) {
    $details += "Perfil activo configurado: $($activeProfile.label)"
  }
  if ($currentMode -eq "double_nat") {
    $details += "Modo detectado: red con router intermedio"
  } elseif ($currentMode -eq "direct_router") {
    $details += "Modo detectado: router directo"
  } else {
    $details += "Modo detectado: red sin clasificar todavia"
  }
  if ($mappedTargetIp) {
    $details += "Los reenvios visibles apuntan a: $mappedTargetIp"
  }
  if ($localHttp.Success -and $localHttp.StatusCode) {
    $details += "HTTP local responde en 127.0.0.1:$($localHttp.StatusCode)"
  }
  if ($localFirewall.HasAllowEvidence) {
    $details += "Firewall local con reglas de entrada para HTTP/HTTPS"
  }

  if ($manualProfileMismatch) {
    $caseCode = "MANUAL_PROFILE_MISMATCH"
    $summary = "El perfil activo manual no coincide con la red actual."
    if ($detectedProfile) {
      $nextStep = "Ahora mismo encaja mejor el perfil '$($detectedProfile.label)'. Cambia el perfil activo a ese o vuelve a modo auto."
    } else {
      $nextStep = "Cambia a modo auto, activa otro perfil o guarda esta red actual como perfil nuevo."
    }
  } elseif ($detectedProfile) {
    $caseCode = "PROFILE_DETECTED"
    $summary = "Perfil de red detectado: $($detectedProfile.label)."
    if ($acme -and $acme.HasTimeout) {
      if ($localHttp.Success -and $localFirewall.HasAllowEvidence) {
        $nextStep = "Caddy ya responde en local y el firewall parece abierto. El bloqueo casi seguro esta en el router o en el operador: revisa que TCP 80 y 443 apunten a $($current.LocalIp) y que tu conexion acepte entrada por esos puertos."
      } elseif ($detectedProfile.mode -eq "direct_router") {
        $nextStep = "Revisa que el router actual tenga TCP 80 y 443 apuntando a $($current.LocalIp) y que el firewall de Windows permita esos puertos."
      } elseif ($detectedProfile.mode -eq "double_nat") {
        $nextStep = "Revisa la cadena completa: router principal 80/443 hacia el router intermedio y router intermedio 80/443 hacia $($current.LocalIp)."
      } else {
        $nextStep = "La app esta bien, pero Internet todavia no entra por 80/443 hasta este PC. Revisa el Port Forwarding hacia $($current.LocalIp)."
      }
    } elseif ($publicRouteHitsCurrentPc -and -not $CaddyStatus.TlsReady) {
      $nextStep = "Los reenvios visibles ya apuntan a esta IP. Si HTTPS aun falla, revisa el firewall local o espera a que termine de emitirse el certificado."
    }
  } elseif ($isNewNetwork) {
    $caseCode = "NEW_NETWORK"
    $summary = "Red nueva detectada. Esta red aun no esta guardada como perfil web estable."
    if ($current.LocalIp -and -not $publicRouteEvidence) {
      $nextStep = "Puedes usar esta red, pero primero configura el Port Forwarding hacia $($current.LocalIp) y luego guarda esta red como perfil."
    } elseif ($publicRouteHitsCurrentPc) {
      $nextStep = "Esta red parece viable y los reenvios visibles ya apuntan a esta IP. Guardala como perfil para no repetir este aviso."
    } else {
      $nextStep = "Si quieres usar esta red como publicacion estable, guarda un perfil nuevo y revisa que 80/443 lleguen hasta esta IP."
    }
  } elseif ($EdgeStatus.DoubleNatDetected -and $CaddyStatus.Running -and -not $CaddyStatus.TlsReady) {
    $caseCode = "UPSTREAM_ROUTE_BLOCKED"
    $summary = "La app esta bien, pero Internet todavia no llega a este PC por 80/443."
    $nextStep = if ($EdgeStatus.UpnpExternalIp) {
      "Revisa el router aguas arriba para que reenvie 80/443 hacia $($EdgeStatus.UpnpExternalIp) y desde ahi hasta la IP actual del PC."
    } else {
      "Revisa la cadena de Port Forwarding completa hasta la IP actual del PC."
    }
  } elseif ($EdgeStatus.UpnpExternalIp -and (Test-IsPrivateIPv4 -IpAddress $EdgeStatus.UpnpExternalIp) -and $acme -and $acme.HasTimeout) {
    $caseCode = "CGNAT_OR_PRIVATE_NAT"
    $summary = "La ruta publica sigue sin llegar a este PC y puede haber CG-NAT o una NAT privada aguas arriba."
    $nextStep = "Confirma con tu operador si la IP publica es realmente enrutable o si estas bajo CG-NAT."
  } elseif ($acme -and $acme.HasTimeout -and $localHttp.Success -and $localFirewall.HasAllowEvidence) {
    $caseCode = "UPSTREAM_ROUTE_BLOCKED"
    $summary = "Caddy responde localmente y el firewall de Windows parece abierto, pero Let''s Encrypt no consigue entrar desde Internet."
    $nextStep = "El bloqueo casi seguro esta en el router o en el operador. Revisa que TCP 80 y 443 apunten a $($current.LocalIp) y que tu conexion no este filtrando puertos entrantes."
  }

  return [pscustomobject]@{
    Current = $current
    ProfilesState = $profilesState
    ProfilesCount = if ($profilesState -and $profilesState.profiles) { @($profilesState.profiles).Count } else { 0 }
    ActiveProfileId = $activeProfileId
    ActiveProfile = $activeProfile
    DetectedProfile = $detectedProfile
    CurrentMode = $currentMode
    IsNewNetwork = $isNewNetwork
    ManualProfileMismatch = $manualProfileMismatch
    PublicRouteHitsCurrentPc = $publicRouteHitsCurrentPc
    PublicRouteEvidence = $publicRouteEvidence
    MappedTargetIp = $mappedTargetIp
    TcpMappings = $tcpMappings
    Acme = $acme
    LocalHttp = $localHttp
    LocalFirewall = $localFirewall
    CaseCode = $caseCode
    Summary = $summary
    NextStep = $nextStep
    Details = $details
  }
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
  $networkDiagnosis = Get-StablePublishNetworkDiagnosis -EdgeStatus $edgeStatus -CaddyStatus $caddyStatus -Domain $domain

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
    $checks += [pscustomobject]@{ Name = "Topologia de red"; Status = "warn"; Message = "Hay un router intermedio: UPnP ve como externa $($edgeStatus.UpnpExternalIp), mientras la IP publica real es $($edgeStatus.PublicIp)." }
  } elseif ($edgeStatus.UpnpExternalIp) {
    $checks += [pscustomobject]@{ Name = "Topologia de red"; Status = "ok"; Message = "La red expone UPnP con salida por $($edgeStatus.UpnpExternalIp)." }
  }

  if ($caddyStatus.Running -and -not $caddyStatus.TlsReady) {
    $ready = $false
    $tlsDetail = if ($caddyStatus.TlsDetail -and $caddyStatus.TlsDetail.Error) { $caddyStatus.TlsDetail.Error } else { "handshake TLS no disponible todavia" }
    $checks += [pscustomobject]@{ Name = "TLS"; Status = "fail"; Message = "Caddy esta escuchando, pero HTTPS aun no esta listo: $tlsDetail." }
  } elseif ($caddyStatus.TlsReady) {
    $checks += [pscustomobject]@{ Name = "TLS"; Status = "ok"; Message = "HTTPS local listo para $domain." }
  }

  if ($networkDiagnosis.Current.LocalIp) {
    $checks += [pscustomobject]@{ Name = "Red actual"; Status = "ok"; Message = "Este PC esta ahora en $($networkDiagnosis.Current.LocalIp) por $($networkDiagnosis.Current.InterfaceAlias)." }
  }

  if ($networkDiagnosis.Current.Gateway) {
    $checks += [pscustomobject]@{ Name = "Gateway actual"; Status = "ok"; Message = "Gateway actual: $($networkDiagnosis.Current.Gateway)." }
  }

  if ($networkDiagnosis.DetectedProfile) {
    $checks += [pscustomobject]@{ Name = "Perfil de red"; Status = "ok"; Message = "Perfil de red detectado: $($networkDiagnosis.DetectedProfile.label)." }
  } elseif ($networkDiagnosis.IsNewNetwork) {
    $checks += [pscustomobject]@{ Name = "Perfil de red"; Status = "warn"; Message = "Red nueva detectada. Esta red aun no esta guardada como perfil web estable." }
  }

  if ($networkDiagnosis.ManualProfileMismatch) {
    $ready = $false
    $checks += [pscustomobject]@{ Name = "Perfil activo"; Status = "fail"; Message = $networkDiagnosis.Summary }
  }

  if ($networkDiagnosis.CaseCode -eq "UPSTREAM_ROUTE_BLOCKED") {
    $ready = $false
    $checks += [pscustomobject]@{ Name = "Llegada publica"; Status = "fail"; Message = $networkDiagnosis.Summary }
  } elseif ($networkDiagnosis.CaseCode -eq "CGNAT_OR_PRIVATE_NAT") {
    $ready = $false
    $checks += [pscustomobject]@{ Name = "Llegada publica"; Status = "fail"; Message = $networkDiagnosis.Summary }
  } elseif ($networkDiagnosis.CaseCode -eq "PROFILE_DETECTED" -or $networkDiagnosis.CaseCode -eq "NEW_NETWORK") {
    $checks += [pscustomobject]@{ Name = "Llegada publica"; Status = "warn"; Message = if ($networkDiagnosis.NextStep) { $networkDiagnosis.NextStep } else { "Todavia no hay confirmacion completa de la llegada publica por 80/443." } }
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
    NetworkDiagnosis = $networkDiagnosis
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
