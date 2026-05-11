param(
  [ValidateSet("repo", "docs", "live-docs")]
  [string]$Mode = "repo",
  [string]$OutputPath
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$excludeNames = @(
  ".git",
  "_publish_repo",
  "node_modules",
  "npm-cache",
  ".venv",
  "venv",
  ".next",
  ".pytest_cache",
  "__pycache__",
  "logs",
  "test-results",
  "tmp",
  "%TEMP%",
  "_bench_before",
  "_bench_after",
  "caches",
  "builds"
)

$excludePrefixWildcards = @(
  ".next_broken_"
)

$excludeFilePatterns = @(
  ".env",
  ".env.*",
  "token.txt",
  "viru.db",
  "*.sqlite",
  "*.sqlite3",
  "tree_filtrado.txt"
)

function Get-ModeRoot {
  param([string]$SelectedMode)
  switch ($SelectedMode) {
    "repo" { return $repoRoot }
    "docs" { return (Join-Path $repoRoot "docs") }
    "live-docs" { return (Join-Path $repoRoot "docs") }
    default { throw "Modo no soportado: $SelectedMode" }
  }
}

function Should-ExcludeSegment {
  param([string]$Segment)
  if ($excludeNames -contains $Segment) {
    return $true
  }
  foreach ($prefix in $excludePrefixWildcards) {
    if ($Segment.StartsWith($prefix)) {
      return $true
    }
  }
  return $false
}

function Should-ExcludeRelativePath {
  param(
    [string]$RelativePath,
    [string]$SelectedMode
  )
  if ([string]::IsNullOrWhiteSpace($RelativePath)) {
    return $false
  }

  $normalized = $RelativePath.Replace("\", "/")
  $segments = $normalized.Split("/", [System.StringSplitOptions]::RemoveEmptyEntries)
  $leaf = if ($segments.Count -gt 0) { $segments[$segments.Count - 1] } else { "" }

  foreach ($pattern in $excludeFilePatterns) {
    if ($leaf -like $pattern) {
      return $true
    }
  }

  foreach ($segment in $segments) {
    if (Should-ExcludeSegment -Segment $segment) {
      return $true
    }
  }

  if ($SelectedMode -eq "live-docs" -and ($normalized -eq "archive" -or $normalized.StartsWith("archive/"))) {
    return $true
  }

  return $false
}

function Get-TreeLines {
  param(
    [string]$BasePath,
    [string]$SelectedMode
  )

  $all = Get-ChildItem -Path $BasePath -Recurse -Force -ErrorAction SilentlyContinue |
    Sort-Object FullName

  $lines = New-Object System.Collections.Generic.List[string]
  foreach ($item in $all) {
    $baseUri = New-Object System.Uri(($BasePath.TrimEnd("\") + "\"))
    $itemUri = New-Object System.Uri($item.FullName)
    $relative = [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($itemUri).ToString()).Replace("/", "\")
    if (Should-ExcludeRelativePath -RelativePath $relative -SelectedMode $SelectedMode) {
      continue
    }

    $segments = $relative.Split([System.IO.Path]::DirectorySeparatorChar)
    $depth = [Math]::Max(0, $segments.Count - 1)
    $indent = ("  " * $depth)
    $name = $item.Name
    if ($item.PSIsContainer) {
      $name = "$name/"
    }
    $lines.Add("$indent$name")
  }

  return $lines
}

$targetRoot = Get-ModeRoot -SelectedMode $Mode
if (-not (Test-Path $targetRoot)) {
  throw "Ruta base no encontrada para modo '$Mode': $targetRoot"
}

$header = @(
  "# tree-clean",
  "mode: $Mode",
  "base: $targetRoot",
  ""
)

$lines = Get-TreeLines -BasePath $targetRoot -SelectedMode $Mode
$output = @($header + $lines) -join [Environment]::NewLine

if ($OutputPath) {
  $absoluteOutput = if ([System.IO.Path]::IsPathRooted($OutputPath)) {
    $OutputPath
  } else {
    Join-Path $repoRoot $OutputPath
  }
  $output | Set-Content -Path $absoluteOutput -Encoding UTF8
  Write-Output "Escrito: $absoluteOutput"
} else {
  Write-Output $output
}
