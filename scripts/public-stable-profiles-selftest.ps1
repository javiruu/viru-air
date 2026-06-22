$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "ops-common.ps1")

function Assert-Equal {
  param(
    [Parameter(Mandatory)]$Actual,
    [Parameter(Mandatory)]$Expected,
    [Parameter(Mandatory)][string]$Message
  )

  if ($Actual -ne $Expected) {
    throw "$Message. Esperado: $Expected. Actual: $Actual."
  }
}

function Assert-True {
  param(
    [Parameter(Mandatory)][bool]$Condition,
    [Parameter(Mandatory)][string]$Message
  )

  if (-not $Condition) {
    throw $Message
  }
}

$profilesState = [pscustomobject]@{
  schemaVersion = 3
  activeProfileId = "auto"
  profiles = @(
    [pscustomobject]@{
      id = "tp-link-mesh"
      label = "TP-Link Mesh"
      domain = "virutracker.duckdns.org"
      expectedPcIp = "192.168.68.114"
      expectedGateway = "192.168.68.1"
      intermediateRouterIp = "192.168.1.128"
      mode = "double_nat"
      notes = "DIGI -> TP-Link Mesh -> Laptop"
    },
    [pscustomobject]@{
      id = "digi-direct"
      label = "DIGI directo"
      domain = "virutracker.duckdns.org"
      expectedPcIp = "192.168.1.130"
      expectedGateway = "192.168.1.1"
      mode = "direct_router"
      notes = "DIGI -> Laptop"
    }
  )
}

$caddyStatus = [pscustomobject]@{
  Running = $true
  TlsReady = $false
}

$cleanAcme = [pscustomobject]@{
  HasTimeout = $false
}

$timeoutAcme = [pscustomobject]@{
  HasTimeout = $true
}

$meshEdge = [pscustomobject]@{
  PublicIp = "79.116.219.59"
  UpnpExternalIp = "192.168.1.128"
  UpnpMappings = @(
    [pscustomobject]@{ Protocol = "TCP"; ExternalPort = 80; InternalPort = 80; InternalClient = "192.168.68.114" },
    [pscustomobject]@{ Protocol = "TCP"; ExternalPort = 443; InternalPort = 443; InternalClient = "192.168.68.114" }
  )
  DoubleNatDetected = $true
}

$meshCurrent = [pscustomobject]@{
  LocalIp = "192.168.68.114"
  Gateway = "192.168.68.1"
  InterfaceAlias = "Wi-Fi"
  SubnetHint = "192.168.68.x"
}

$meshDiagnosis = Get-StablePublishNetworkDiagnosis -EdgeStatus $meshEdge -CaddyStatus $caddyStatus -Domain "virutracker.duckdns.org" -CurrentNetworkOverride $meshCurrent -ProfilesStateOverride $profilesState -AcmeOverride $cleanAcme
Assert-Equal -Actual $meshDiagnosis.DetectedProfile.id -Expected "tp-link-mesh" -Message "El perfil TP-Link Mesh no se detecto bien"

$directEdge = [pscustomobject]@{
  PublicIp = "79.116.219.59"
  UpnpExternalIp = $null
  UpnpMappings = @(
    [pscustomobject]@{ Protocol = "TCP"; ExternalPort = 80; InternalPort = 80; InternalClient = "192.168.1.130" },
    [pscustomobject]@{ Protocol = "TCP"; ExternalPort = 443; InternalPort = 443; InternalClient = "192.168.1.130" }
  )
  DoubleNatDetected = $false
}

$directCurrent = [pscustomobject]@{
  LocalIp = "192.168.1.130"
  Gateway = "192.168.1.1"
  InterfaceAlias = "Wi-Fi"
  SubnetHint = "192.168.1.x"
}

$directDiagnosis = Get-StablePublishNetworkDiagnosis -EdgeStatus $directEdge -CaddyStatus $caddyStatus -Domain "virutracker.duckdns.org" -CurrentNetworkOverride $directCurrent -ProfilesStateOverride $profilesState -AcmeOverride $timeoutAcme
Assert-Equal -Actual $directDiagnosis.DetectedProfile.id -Expected "digi-direct" -Message "El perfil DIGI directo no se detecto bien"
Assert-True -Condition ($directDiagnosis.NextStep -like "*192.168.1.130*") -Message "El mensaje de DIGI directo debe apuntar a la IP actual del PC"
Assert-True -Condition (-not ($directDiagnosis.NextStep -like "*TP-Link*")) -Message "No debe recomendar volver al TP-Link cuando detecta DIGI directo"

$newCurrent = [pscustomobject]@{
  LocalIp = "192.168.50.22"
  Gateway = "192.168.50.1"
  InterfaceAlias = "Wi-Fi"
  SubnetHint = "192.168.50.x"
}

$newEdge = [pscustomobject]@{
  PublicIp = "79.116.219.59"
  UpnpExternalIp = $null
  UpnpMappings = @()
  DoubleNatDetected = $false
}

$newDiagnosis = Get-StablePublishNetworkDiagnosis -EdgeStatus $newEdge -CaddyStatus $caddyStatus -Domain "virutracker.duckdns.org" -CurrentNetworkOverride $newCurrent -ProfilesStateOverride $profilesState -AcmeOverride $cleanAcme
Assert-True -Condition $newDiagnosis.IsNewNetwork -Message "La red nueva debe detectarse como red nueva"
Assert-Equal -Actual $newDiagnosis.CaseCode -Expected "NEW_NETWORK" -Message "La red nueva no debe bloquearse como topologia antigua"

$tempPath = Join-Path ([System.IO.Path]::GetTempPath()) ("viru-stable-profiles-" + [guid]::NewGuid().ToString("N") + ".json")
$stateForSave = [pscustomobject]@{
  schemaVersion = 3
  activeProfileId = "auto"
  profiles = @(
    [pscustomobject]@{ id = "tp-link-mesh"; label = "TP-Link Mesh"; domain = "virutracker.duckdns.org"; expectedPcIp = "192.168.68.114"; expectedGateway = "192.168.68.1"; mode = "double_nat" }
  )
}
Set-Content -Path $tempPath -Value ($stateForSave | ConvertTo-Json -Depth 8) -Encoding ASCII

$originalProfilesPath = Get-PublicStableNetworkProfilesPath
$originalLegacyPath = Get-LegacyPublicStableNetworkStatePath

function global:Get-PublicStableNetworkProfilesPath { return $tempPath }
function global:Get-LegacyPublicStableNetworkStatePath { return "Z:\no-legacy-file.json" }

try {
  $saveResult = Save-PublicStableNetworkProfile -Domain "virutracker.duckdns.org" -CurrentNetwork $directCurrent -EdgeStatus $directEdge -Label "DIGI directo"
  $savedState = Read-PublicStableNetworkProfiles
  Assert-Equal -Actual @($savedState.profiles).Count -Expected 2 -Message "Guardar un perfil nuevo no debe machacar los anteriores"
  Assert-Equal -Actual $saveResult.Profile.label -Expected "DIGI directo" -Message "El perfil guardado debe conservar su etiqueta"
} finally {
  Remove-Item -Path Function:\Get-PublicStableNetworkProfilesPath -Force
  Remove-Item -Path Function:\Get-LegacyPublicStableNetworkStatePath -Force
  Remove-Item -Path $tempPath -Force -ErrorAction SilentlyContinue
}

Write-Output "SELFTEST_OK public-stable-profiles"
