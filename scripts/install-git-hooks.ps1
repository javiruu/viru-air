$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

if (-not (Test-Path ".git")) {
  throw "No se encontro .git en '$repoRoot'. Ejecuta este script dentro de _publish_repo."
}

git config core.hooksPath .githooks
Write-Host "Git hooks path configurado a .githooks"
Write-Host "Hook activo: .githooks/pre-push"

