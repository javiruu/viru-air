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

if ($status.BlockingReason -ne "El proceso de Cloudflare sigue activo, pero no he podido verificar su URL desde este equipo tras probar HEAD y GET.") {
  throw "Expected the stale quick-tunnel state to explain why publication is not ready."
}

function Invoke-WebRequest {
  return [pscustomobject]@{ StatusCode = 200 }
}

$status = Get-CloudflareTunnelStatus

if (-not $status.Ready) {
  throw "Expected a running tunnel with a reachable public URL to be ready."
}

function Invoke-WebRequest {
  param([string]$Method)
  if ($Method -eq "Head") {
    throw [System.Net.WebException]::new("HEAD blocked")
  }
  return [pscustomobject]@{ StatusCode = 204 }
}

$check = Get-PublicUrlReadiness -Url "https://head-blocked.example"
if (-not $check.Ready -or $check.Method -ne "Get") {
  throw "Expected GET to verify the URL when HEAD is blocked."
}

function Get-TailscaleCliPath {
  return "tailscale.exe"
}

function Invoke-TailscaleJsonCommand {
  return [pscustomobject]@{
    Available = $true
    Success = $false
    ExitCode = 1
    Output = @("open \\.\pipe\ProtectedPrefix\Administrators\Tailscale\tailscaled: Acceso denegado.")
    Json = $null
    AccessDenied = $true
  }
}

$tailscaleStatus = Get-TailscaleFunnelStatus
if ($tailscaleStatus.BlockingReason -ne "Tailscale esta activo, pero el panel no tiene permiso para consultar su servicio local.") {
  throw "Expected Tailscale permission errors to be reported distinctly."
}

Write-Host "PASS: tunnel readiness handles GET fallback and Tailscale permission errors."
