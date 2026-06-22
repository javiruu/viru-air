. (Join-Path $PSScriptRoot "ops-common.ps1")

Write-Section "CADDY STOP"
$status = Get-CaddyRuntimeStatus

if (-not $status.DockerAvailable) {
  Write-Fail "docker compose no esta disponible."
  exit 1
}

if (-not $status.Exists) {
  Write-Info "Caddy aun no estaba creado."
  exit 0
}

if (-not $status.Running) {
  Write-Info ("Caddy ya estaba parado (estado $($status.State)).")
  exit 0
}

try {
  $result = Invoke-DockerCompose -Arguments ((Get-DockerComposeBaseArgs) + @("stop", "caddy"))
  foreach ($line in $result.Output) {
    Write-Info ($line.ToString())
  }
  Write-Ok "Caddy detenido."
  exit 0
} catch {
  Write-Fail $_.Exception.Message
  exit 1
}
