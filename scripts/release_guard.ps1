param(
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string[]]$ExpectedPaths = @(),
  [switch]$AllowDirtyWorktree,
  [switch]$PrePush
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

function Fail([string]$Message) {
  Write-Host "RELEASE_GUARD_FAIL: $Message" -ForegroundColor Red
  exit 1
}

function Pass([string]$Message) {
  Write-Host "RELEASE_GUARD_OK: $Message" -ForegroundColor Green
}

if (-not (Test-Path ".git")) {
  Fail "No se encontro .git en '$RepoRoot'. Ejecuta este guard dentro de _publish_repo."
}

$branch = (git rev-parse --abbrev-ref HEAD).Trim()
if ($branch -ne "main") {
  Fail "Rama actual '$branch'. La publicacion por defecto requiere 'main'."
}
Pass "Rama main confirmada."

if (-not $AllowDirtyWorktree) {
  $status = git status --porcelain
  if ($status) {
    Fail "Working tree no limpio. Revisa git status antes de publicar."
  }
  Pass "Working tree limpio."
}

if ($ExpectedPaths.Count -gt 0) {
  $expected = $ExpectedPaths | ForEach-Object { $_.Replace("\", "/") }

  $changed = git diff --name-only --cached
  if (-not $changed) {
    Fail "No hay cambios staged. Usa git add con los archivos esperados."
  }

  $unexpected = @()
  foreach ($path in $changed) {
    $normalized = $path.Replace("\", "/")
    if ($expected -notcontains $normalized) {
      $unexpected += $path
    }
  }

  if ($unexpected.Count -gt 0) {
    Fail ("Hay archivos staged fuera del alcance: " + ($unexpected -join ", "))
  }
  Pass "Staging acotado a archivos esperados."
}

$remote = git remote get-url origin 2>$null
if (-not $remote) {
  Fail "No se encontro remote 'origin'."
}
Pass "Remote origin disponible: $remote"

if ($PrePush) {
  Pass "Validacion pre-push completada."
}

Pass "Release guard completado."
exit 0

