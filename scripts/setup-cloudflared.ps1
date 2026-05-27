<# 
.SYNOPSIS
  Instala cloudflared y configura un Cloudflare Tunnel para viru-tracker.

.DESCRIPTION
  Este script:
  1. Detecta o instala cloudflared (vÃ­a winget o descarga directa).
  2. Autentica con Cloudflare (abre navegador).
  3. Crea el tÃºnel "viru-tracker" si no existe.
  4. Configura el DNS (CNAME -> tunnel) en Cloudflare para viruair.dpdns.org.
  5.  Escribe el archivo de config infra/cloudflared-config.local.yml con los IDs reales.

.PARAMETER Domain
  Dominio a exponer. Por defecto: viruair.dpdns.org

.EXAMPLE
  .\scripts\setup-cloudflared.ps1
  .\scripts\setup-cloudflared.ps1 -Domain viruair.dpdns.org
#>

param(
  [string]$Domain = "viruair.dpdns.org",
  [string]$ConfigPath = "$PSScriptRoot\..\infra\cloudflared-config.local.yml"
)

$ErrorActionPreference = "Stop"
$TunnelName = "viru-tracker"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Cloudflare Tunnel Setup - viru-tracker" -ForegroundColor Cyan
Write-Host "  Domain: $Domain"                        -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# â”€â”€ 1. Check / install cloudflared â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Write-Host "[1/5] Checking cloudflared..." -ForegroundColor Yellow

$cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue

if (-not $cloudflared) {
  Write-Host "  cloudflared not found. Installing via winget..." -ForegroundColor Gray
  
  $winget = Get-Command winget -ErrorAction SilentlyContinue
  if ($winget) {
    winget install --id Cloudflare.cloudflared --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) {
      throw "winget install failed. Try manual install: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
    }
  } else {
    Write-Host "  winget not available. Downloading cloudflared directly..." -ForegroundColor Gray
    $url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    $dest = "$env:LOCALAPPDATA\cloudflared\cloudflared.exe"
    $destDir = Split-Path $dest -Parent
    if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
    Invoke-WebRequest -Uri $url -OutFile $dest
    # Add to user PATH
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($userPath -notlike "*$destDir*") {
      [Environment]::SetEnvironmentVariable("Path", "$userPath;$destDir", "User")
      $env:Path = "$env:Path;$destDir"
    }
  }
  
  # Refresh PATH and verify
  $env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" + [Environment]::GetEnvironmentVariable("Path", "Machine")
  $cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
  if (-not $cloudflared) {
    throw "cloudflared still not found after install. Please restart your terminal and re-run this script."
  }
}

Write-Host "  cloudflared found at: $($cloudflared.Source)" -ForegroundColor Green

# â”€â”€ 2. Authenticate with Cloudflare â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Write-Host ""
Write-Host "[2/5] Authenticating with Cloudflare..." -ForegroundColor Yellow
Write-Host "  A browser window will open. Log in to your Cloudflare account." -ForegroundColor Gray

# Check if already authenticated (cert.pem exists)
$certPath = "$env:USERPROFILE\.cloudflared\cert.pem"
$alreadyAuthed = Test-Path $certPath

if ($alreadyAuthed) {
  Write-Host "  Already authenticated (cert.pem found)." -ForegroundColor Green
  Write-Host "  To re-authenticate, delete $certPath and re-run this script." -ForegroundColor Gray
} else {
  cloudflared tunnel login
  if ($LASTEXITCODE -ne 0) {
    throw "cloudflared login failed."
  }
  Write-Host "  Authentication successful." -ForegroundColor Green
}

# â”€â”€ 3. Create tunnel â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Write-Host ""
Write-Host "[3/5] Creating tunnel '$TunnelName'..." -ForegroundColor Yellow

$tunnelList = cloudflared tunnel list --output json 2>$null | ConvertFrom-Json -ErrorAction SilentlyContinue
$existingTunnel = $tunnelList | Where-Object { $_.name -eq $TunnelName } | Select-Object -First 1

if ($existingTunnel) {
  $TunnelId = $existingTunnel.id
  Write-Host "  Tunnel already exists: $TunnelId" -ForegroundColor Green
} else {
  $createOutput = cloudflared tunnel create $TunnelName 2>&1
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to create tunnel: $createOutput"
  }
  # Extract tunnel ID from output (format: "Created tunnel viru-tracker with id xxxx-xxxx-xxxx-xxxx")
  $TunnelId = ($createOutput | Select-String -Pattern 'with id ([a-f0-9-]+)').Matches.Groups[1].Value
  if (-not $TunnelId) {
    # Fallback: list tunnels and find it
    $tunnelList = cloudflared tunnel list --output json 2>$null | ConvertFrom-Json
    $TunnelId = ($tunnelList | Where-Object { $_.name -eq $TunnelName }).id
  }
  Write-Host "  Tunnel created: $TunnelId" -ForegroundColor Green
}

# â”€â”€ 4. Configure DNS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Write-Host ""
Write-Host "[4/5] Configuring DNS for $Domain..." -ForegroundColor Yellow

$cnameTarget = "$TunnelId.cfargotunnel.com"

Write-Host "  Creating CNAME: $Domain -> $cnameTarget" -ForegroundColor Gray
# cloudflared tunnel route dns is idempotent â€” succeeds silently if route exists
$routeOutput = cloudflared tunnel route dns $TunnelName $Domain 2>&1
if ($LASTEXITCODE -ne 0) {
  # Check if it failed because the route already exists (expected)
  if ($routeOutput -match "already exists|duplicate|conflict") {
    Write-Host "  DNS record already exists: $Domain -> $cnameTarget" -ForegroundColor Green
  } else {
    Write-Host "  WARNING: DNS route may have failed. Output:" -ForegroundColor Yellow
    Write-Host "  $routeOutput" -ForegroundColor DarkYellow
    Write-Host "  If the domain doesn't resolve, manually add in Cloudflare Dashboard:" -ForegroundColor Yellow
    Write-Host "    Type: CNAME, Name: @, Target: $cnameTarget" -ForegroundColor Yellow
    Write-Host "    Ensure the orange cloud (proxy) is ENABLED" -ForegroundColor Yellow
  }
} else {
  Write-Host "  DNS configured: $Domain -> $cnameTarget" -ForegroundColor Green
}

# â”€â”€ 5. Write config file â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Write-Host ""
Write-Host "[5/5] Writing tunnel config to $ConfigPath..." -ForegroundColor Yellow

$credentialsFile = "$env:USERPROFILE\.cloudflared\$TunnelId.json"

$configContent = @"
# Cloudflare Tunnel configuration for viru-tracker
# Domain: $Domain
# Tunnel ID: $TunnelId
#
# Start:  cloudflared tunnel run $TunnelName
#         (or use VIRU_PANEL.bat option A)
#
# Cloudflare handles HTTPS automatically â€” no Caddy needed.

tunnel: $TunnelId
credentials-file: $credentialsFile

ingress:
  # API routes -> backend
  - hostname: $Domain
    path: /api/*
    service: http://localhost:8000

  # All other traffic -> frontend (Next.js)
  - hostname: $Domain
    service: http://localhost:3000

  # Reject unmatched requests
  - service: http_status:404
"@

$configDir = Split-Path $ConfigPath -Parent
if (-not (Test-Path $configDir)) { New-Item -ItemType Directory -Path $configDir -Force | Out-Null }
Set-Content -Path $ConfigPath -Value $configContent -Encoding UTF8

Write-Host "  Config written to: $ConfigPath" -ForegroundColor Green
Write-Host "  (This file is git-ignored - it contains real tunnel IDs.)" -ForegroundColor Gray

# -- Done ------------------------------------------------------------------
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SETUP COMPLETE"                        -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Domain:   https://$Domain" -ForegroundColor White
Write-Host "  Tunnel:   $TunnelName ($TunnelId)" -ForegroundColor White
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor Yellow
Write-Host "  1. Start VIRU locally (VIRU_PANEL.bat option 1)" -ForegroundColor Gray
Write-Host "  2. Start tunnel:  cloudflared tunnel run $TunnelName" -ForegroundColor Gray
Write-Host "     Or use:         VIRU_PANEL.bat option A" -ForegroundColor Gray
Write-Host "  3. Open:          https://$Domain" -ForegroundColor Gray
Write-Host ""
Write-Host "  NOTE: DNS propagation can take a few minutes after first setup." -ForegroundColor DarkYellow
