$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "..\ops-common.ps1")

function Get-CloudflaredCliPath {
  return "cloudflared.exe"
}

function Get-CloudflareTunnelPaths {
  return [pscustomobject]@{
    PidFile = "unused.pid"
    OutLog = "unused.out.log"
    ErrLog = "unused.err.log"
  }
}

function Get-ManagedProcessState {
  return [pscustomobject]@{
    IsRunning = $true
    HasPidFile = $true
    ProcessId = 42
    ProcessName = "cloudflared"
  }
}

function Get-CloudflareTunnelConfigInfo {
  return [pscustomobject]@{
    ConfigPath = $null
    TunnelIdOrName = $null
    Hostname = $null
    CredentialsFile = $null
  }
}

function Get-CloudflareQuickTunnelUrl {
  return "https://expired-quick-tunnel.example"
}

function Get-CloudflareTunnelAuthCertPath {
  return "missing-cert.pem"
}

function Get-CommandVersionText {
  return "cloudflared version test"
}

function Invoke-WebRequest {
  throw [System.Net.WebException]::new("Name resolution failed")
}

$status = Get-CloudflareTunnelStatus

if ($status.Ready) {
  throw "Expected an unreachable public URL to make the Cloudflare tunnel not ready."
}

if ($status.BlockingReason -ne "El proceso de Cloudflare sigue activo, pero su URL publica ya no responde.") {
  throw "Expected the stale quick-tunnel state to explain why publication is not ready."
}

function Invoke-WebRequest {
  return [pscustomobject]@{ StatusCode = 200 }
}

$status = Get-CloudflareTunnelStatus

if (-not $status.Ready) {
  throw "Expected a running tunnel with a reachable public URL to be ready."
}

Write-Host "PASS: Cloudflare readiness follows the public URL response."
