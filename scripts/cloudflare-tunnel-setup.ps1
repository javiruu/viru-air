param(
  [string]$Domain,
  [string]$TunnelId,
  [string]$Hostname,
  [string]$CredentialsFile,
  [switch]$InstallIfMissing
)

. (Join-Path $PSScriptRoot "ops-common.ps1")

$ErrorActionPreference = "Stop"

Write-Section "SETUP CLOUDFLARE TUNNEL"

if ($InstallIfMissing) {
  $install = Ensure-CloudflaredInstalled
  if ($install.Changed) {
    Write-Ok $install.Message
  } elseif (-not $install.Installed) {
    Write-Fail $install.Message
    exit 1
  } else {
    Write-Info $install.Message
  }
}

$status = Get-CloudflareTunnelStatus
if (-not $status.Installed) {
  Write-Fail "Cloudflare Tunnel no esta instalado en este equipo."
  Write-Info "Siguiente paso: vuelve a ejecutar este script con -InstallIfMissing o instala cloudflared manualmente."
  exit 1
}

if (-not $Hostname -and $Domain) {
  $Hostname = $Domain
}

if (-not $Hostname) {
  $infraEnv = Read-DotEnv -Path (Get-InfraEnvPath) -AllowMissing
  if ($infraEnv.ContainsKey("DOMAIN") -and $infraEnv["DOMAIN"]) {
    $Hostname = $infraEnv["DOMAIN"]
  }
}

if ($Domain) {
  $envPath = Ensure-StableTunnelEnv -Domain $Domain
  Write-Info ("infra/.env sincronizado en: " + $envPath)
}

if ($TunnelId -and $Hostname -and $CredentialsFile) {
  $configPath = Write-CloudflareTunnelConfig -TunnelIdOrName $TunnelId -Hostname $Hostname -CredentialsFile $CredentialsFile
  Write-Ok ("Config local escrita en: " + $configPath)
}

$current = Get-CloudflareTunnelStatus
$versionText = if ($current.Version) { $current.Version } else { "desconocida" }

Write-Info ("Version: " + $versionText)
Write-Info ("Modo actual: " + $current.Mode)

if ($current.ConfigPath) {
  Write-Info ("Config local: " + $current.ConfigPath)
}

if ($current.Mode -eq "named") {
  if ($current.TunnelIdOrName) {
    Write-Ok ("Tunnel ID o nombre: " + $current.TunnelIdOrName)
  } else {
    Write-Warn "Falta el tunnel ID o nombre en la configuracion local."
  }

  if ($current.Hostname) {
    Write-Ok ("Hostname publico: " + $current.Hostname)
  } else {
    Write-Warn "Falta el hostname publico del tunel."
  }

  if ($current.CredentialsFileExists) {
    Write-Ok ("Credentials file detectado: " + $current.CredentialsFile)
  } else {
    Write-Warn "No encuentro el credentials-file del tunel."
  }

  if ($current.AuthCertExists) {
    Write-Ok ("Auth cert detectado: " + $current.AuthCertPath)
  } else {
    Write-Warn "No encuentro cert.pem de cloudflared en este usuario."
  }
} else {
  Write-Info "No hay config named local. Se usara quick tunnel hasta que prepares infra/cloudflare-tunnel.local.yml."
}

if ($current.BlockingReason) {
  Write-Warn $current.BlockingReason
}
if ($current.NextStep) {
  Write-Info $current.NextStep
}

if ($current.Mode -eq "named" -and $current.NamedConfigReady) {
  Write-Ok "Cloudflare Tunnel named ya esta amueblado para arrancar."
  exit 0
}

Write-Warn "Cloudflare Tunnel aun necesita un ultimo paso humano antes de quedar completo."
exit 1
