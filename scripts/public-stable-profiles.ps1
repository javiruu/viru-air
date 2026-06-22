param(
  [string]$SetActiveProfileId,
  [switch]$UseAuto
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "ops-common.ps1")

Write-Section "PERFILES WEB ESTABLE"

if ($UseAuto -and $SetActiveProfileId) {
  Write-Fail "Usa solo una accion: -UseAuto o -SetActiveProfileId."
  exit 1
}

if ($UseAuto) {
  $path = Set-ActivePublicStableNetworkProfile -ProfileId "auto"
  Write-Ok "Perfil activo cambiado a auto."
  Write-Info ("Archivo local: " + $path)
}

if ($SetActiveProfileId) {
  try {
    $path = Set-ActivePublicStableNetworkProfile -ProfileId $SetActiveProfileId
    Write-Ok ("Perfil activo cambiado a: " + $SetActiveProfileId)
    Write-Info ("Archivo local: " + $path)
  } catch {
    Write-Fail $_.Exception.Message
    exit 1
  }
}

$state = Read-PublicStableNetworkProfiles -AllowMissing
if (-not $state -or @($state.profiles).Count -eq 0) {
  Write-Warn "No hay perfiles guardados todavia."
  Write-Info "Usa la opcion GUARDAR ESTA RED COMO PERFIL WEB ESTABLE para crear el primero."
  exit 0
}

Write-Info ("Perfil activo: " + $state.activeProfileId)
foreach ($profile in @($state.profiles)) {
  $activeMark = if ($state.activeProfileId -eq $profile.id) { "*" } else { "-" }
  Write-Info "$activeMark $($profile.label) [$($profile.id)]"
  if ($profile.expectedPcIp) {
    Write-Info ("  IP esperada: " + $profile.expectedPcIp)
  }
  if ($profile.expectedGateway) {
    Write-Info ("  Router:      " + $profile.expectedGateway)
  }
  if ($profile.mode) {
    Write-Info ("  Modo:        " + $profile.mode)
  }
  if ($profile.notes) {
    Write-Info ("  Notas:       " + $profile.notes)
  }
}
