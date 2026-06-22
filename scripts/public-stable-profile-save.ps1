param(
  [string]$Label,
  [switch]$SetActive
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "ops-common.ps1")

Write-Section "GUARDAR PERFIL WEB ESTABLE"

$duck = Read-DotEnv -Path (Get-DuckDnsConfigPath) -AllowMissing
$infra = Read-DotEnv -Path (Get-InfraEnvPath) -AllowMissing
$domain = if ($infra.ContainsKey("DOMAIN") -and $infra["DOMAIN"]) { $infra["DOMAIN"] } elseif ($duck.ContainsKey("DUCKDNS_FQDN")) { $duck["DUCKDNS_FQDN"] } else { $null }

if (-not $domain) {
  Write-Fail "No hay dominio estable configurado todavia."
  Write-Info "Ejecuta DUCKDNS SETUP antes de guardar un perfil."
  exit 1
}

$current = Get-CurrentNetworkContext
$edge = Get-NetworkEdgeStatus
$defaultLabel = Get-DefaultStableNetworkProfileLabel -CurrentNetwork $current -EdgeStatus $edge
$resolvedLabel = if ($Label) { $Label } else { $defaultLabel }

Write-Info ("Dominio:       " + $domain)
Write-Info ("IP de este PC: " + $current.LocalIp)
Write-Info ("Router actual: " + $current.Gateway)
Write-Info ("Etiqueta:      " + $resolvedLabel)

try {
  $result = Save-PublicStableNetworkProfile -Domain $domain -CurrentNetwork $current -EdgeStatus $edge -Label $resolvedLabel -SetActive:$SetActive
  Write-Info ("Archivo local: " + $result.Path)
  Write-Ok ("Perfil guardado: " + $result.Profile.label)
  Write-Info ("ID del perfil: " + $result.Profile.id)
  if ($SetActive) {
    Write-Info "Este perfil ha quedado como activo."
  }
  exit 0
} catch {
  Write-Fail $_.Exception.Message
  Write-Info "Prueba con otra etiqueta para no reutilizar el mismo identificador."
  exit 1
}
