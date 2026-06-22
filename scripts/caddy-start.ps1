. (Join-Path $PSScriptRoot "ops-common.ps1")

Write-Section "CADDY START"

$duck = Read-DotEnv -Path (Get-DuckDnsConfigPath) -AllowMissing
if ($duck.ContainsKey("DUCKDNS_FQDN")) {
  $envInfo = Ensure-InfraEnv -Domain $duck["DUCKDNS_FQDN"]
  Write-Info ("infra/.env sincronizado: " + $envInfo.Path)
}

if (-not (Ensure-DockerComposeReady)) {
  Write-Fail "No pude dejar Docker Compose operativo automaticamente en esta maquina."
  exit 1
}

$caddyStatus = Get-CaddyRuntimeStatus
if ($caddyStatus.Running) {
  Write-Ok "Caddy ya esta corriendo."
  if ($caddyStatus.PublishedPorts.Count -gt 0) {
    Write-Info ("Puertos publicados: $($caddyStatus.PublishedPorts -join ', ')")
  }
  exit 0
}

$preflight = Get-PublicDomainPreflight
Write-ChecksReport -Checks $preflight.Checks
if (-not $preflight.Ready) {
  Write-Fail "No arranco Caddy porque el preflight de publicacion estable no esta listo."
  exit 1
}

try {
  $result = Invoke-DockerCompose -Arguments ((Get-DockerComposeBaseArgs) + @("up", "-d", "caddy"))
  foreach ($line in $result.Output) {
    Write-Info ($line.ToString())
  }
} catch {
  Write-Fail $_.Exception.Message
  exit 1
}

$postStatus = Get-CaddyRuntimeStatus
if ($postStatus.Running) {
  Write-Ok "Caddy arrancado correctamente."
  if ($postStatus.PublishedPorts.Count -gt 0) {
    Write-Info ("Puertos publicados: $($postStatus.PublishedPorts -join ', ')")
  }
  exit 0
}

Write-Fail "Docker compose termino, pero Caddy no quedo corriendo."
exit 1
