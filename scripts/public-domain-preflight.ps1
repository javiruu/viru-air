. (Join-Path $PSScriptRoot "ops-common.ps1")

Write-Section "PREFLIGHT: PUBLICACION ESTABLE"
$preflight = Get-PublicDomainPreflight
Write-ChecksReport -Checks $preflight.Checks

if ($preflight.Ready) {
  Write-Ok "Preflight OK: el entorno esta listo para publicar con DuckDNS + Caddy."
  exit 0
}

Write-Warn "Preflight incompleto: faltan piezas antes de dar por publicada la web."
exit 1
