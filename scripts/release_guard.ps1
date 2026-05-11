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

function Matches-AnyPattern([string]$Path, [string[]]$Patterns) {
  foreach ($pattern in $Patterns) {
    if ($Path -like $pattern) {
      return $true
    }
  }
  return $false
}

function Test-ProbablyBinary([string]$AbsolutePath) {
  if (-not (Test-Path $AbsolutePath)) {
    return $false
  }

  try {
    $stream = [System.IO.File]::OpenRead($AbsolutePath)
    try {
      $length = [Math]::Min(4096, [int]$stream.Length)
      if ($length -le 0) {
        return $false
      }

      $buffer = New-Object byte[] $length
      [void]$stream.Read($buffer, 0, $length)
      foreach ($b in $buffer) {
        if ($b -eq 0) {
          return $true
        }
      }
      return $false
    }
    finally {
      $stream.Dispose()
    }
  }
  catch {
    return $false
  }
}

if (-not (Test-Path ".git")) {
  Fail "No se encontro .git en '$RepoRoot'. Ejecuta este guard dentro de la raiz del repo viru-tracker."
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

$staged = @(git diff --name-only --cached)
$tracked = @(git ls-files)
$pathsToInspect = @($tracked + $staged | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)

$blockedPatterns = @("*.tsbuildinfo", "*/=*", "=*")
$temporaryPrefixes = @("testsprite_tests/tmp/", "logs/", "logs_ia/", "coverage/", ".next/", "dist/", "build/")
$temporaryAllowedPrefixes = @("docs/qa/", "docs/archive/")

$violations = New-Object System.Collections.Generic.List[string]
foreach ($path in $pathsToInspect) {
  $normalized = $path.Replace("\", "/")
  $abs = Join-Path $RepoRoot $normalized
  if (-not (Test-Path $abs)) {
    continue
  }

  if (Matches-AnyPattern $normalized $blockedPatterns) {
    $violations.Add("$normalized (patron bloqueado)")
  }

  if ($normalized.StartsWith("frontend/")) {
    $ext = [System.IO.Path]::GetExtension($normalized)
    if ([string]::IsNullOrWhiteSpace($ext)) {
      if (Test-ProbablyBinary $abs) {
        $violations.Add("$normalized (binario en frontend sin extension permitida)")
      }
    }
  }

  if (Matches-AnyPattern $normalized ($temporaryPrefixes | ForEach-Object { "$_*" })) {
    $allowed = $false
    foreach ($allowedPrefix in $temporaryAllowedPrefixes) {
      if ($normalized.StartsWith($allowedPrefix)) {
        $allowed = $true
        break
      }
    }
    if (-not $allowed) {
      $violations.Add("$normalized (output temporal fuera de docs/qa o docs/archive)")
    }
  }
}

if ($violations.Count -gt 0) {
  $list = ($violations | Select-Object -Unique) -join ", "
  Fail "Artefactos bloqueados detectados: $list"
}
Pass "Validacion anti-basura sin hallazgos."

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
