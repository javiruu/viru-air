. (Join-Path $PSScriptRoot "ops-common.ps1")

$ErrorActionPreference = "Stop"

Write-Section "ESTADO CLOUDFLARE TUNNEL"

$status = Get-CloudflareTunnelStatus

if (-not $status.Installed) {
  Write-Fail $status.BlockingReason
  if ($status.NextStep) {
    Write-Info $status.NextStep
  }
  exit 1
}

Write-Ok "Cloudflare instalado."
if ($status.Version) {
  Write-Info ("Version: " + $status.Version)
}
Write-Info ("Modo configurado: " + $status.Mode)

if ($status.ConfigPath) {
  Write-Info ("Config local: " + $status.ConfigPath)
}
if ($status.Hostname) {
  Write-Info ("Hostname: " + $status.Hostname)
}
if ($status.CredentialsFile) {
  if ($status.CredentialsFileExists) {
    Write-Ok ("Credentials file: " + $status.CredentialsFile)
  } else {
    Write-Warn ("Credentials file no encontrado: " + $status.CredentialsFile)
  }
}
if ($status.AuthCertPath) {
  if ($status.AuthCertExists) {
    Write-Info ("Auth cert: " + $status.AuthCertPath)
  } else {
    Write-Warn ("Auth cert no encontrado: " + $status.AuthCertPath)
  }
}

if ($status.Running) {
  Write-Ok "Proceso activo."
} else {
  Write-Warn "Proceso no activo."
}

if ($status.PublicUrl) {
  Write-Ok ("URL publica: " + $status.PublicUrl)
}

if ($status.BlockingReason -and -not $status.Ready) {
  Write-Warn $status.BlockingReason
}
if ($status.NextStep) {
  Write-Info $status.NextStep
}

if ($status.Ready) {
  exit 0
}
exit 1
