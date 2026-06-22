. (Join-Path $PSScriptRoot "ops-common.ps1")

Write-Section "CADDY START"

$duck = Read-DotEnv -Path (Get-DuckDnsConfigPath) -AllowMissing
if ($duck.ContainsKey("DUCKDNS_FQDN")) {
  $envInfo = Ensure-InfraEnv -Domain $duck["DUCKDNS_FQDN"]
  Write-Info ("infra/.env sincronizado: " + $envInfo.Path)
}

$caddyCli = $null
try {
  $caddyCli = Ensure-CaddyInstalled
} catch {
  Write-Fail $_.Exception.Message
  exit 1
}

$caddyStatus = Get-CaddyRuntimeStatus
if ($caddyStatus.Healthy) {
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
  $paths = Get-CaddyManagedPaths
  if (Test-Path $paths.OutLog) { Remove-Item $paths.OutLog -Force -ErrorAction SilentlyContinue }
  if (Test-Path $paths.ErrLog) { Remove-Item $paths.ErrLog -Force -ErrorAction SilentlyContinue }
  if (Test-Path $paths.PidFile) { Remove-Item $paths.PidFile -Force -ErrorAction SilentlyContinue }
  Unblock-File -Path $caddyCli -ErrorAction SilentlyContinue

  $domain = (Read-DotEnv -Path (Get-InfraEnvPath))["DOMAIN"]
  $configPath = Join-Path (Get-InfraDir) "Caddyfile"
  $command = "`$env:DOMAIN='$domain'; & '$caddyCli' run --config '$configPath' --adapter caddyfile"
  $proc = Start-Process -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $command) `
    -RedirectStandardOutput $paths.OutLog `
    -RedirectStandardError $paths.ErrLog `
    -WindowStyle Hidden `
    -PassThru

  Set-Content -Path $paths.PidFile -Value $proc.Id -Encoding ASCII
  Start-Sleep -Seconds 4
} catch {
  Write-Fail $_.Exception.Message
  exit 1
}

$postStatus = Get-CaddyRuntimeStatus
if ($postStatus.Healthy) {
  Write-Ok "Caddy arrancado correctamente."
  if ($postStatus.PublishedPorts.Count -gt 0) {
    Write-Info ("Puertos publicados: $($postStatus.PublishedPorts -join ', ')")
  }
  exit 0
}

Write-Fail "Caddy no quedo corriendo correctamente. Revisa logs/caddy.err.log."
exit 1
