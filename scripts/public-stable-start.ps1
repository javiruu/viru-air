param(
  [switch]$AutoMode
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "ops-common.ps1")

function Convert-ToFriendlyCheck {
  param([Parameter(Mandatory)]$Check)

  $message = [string]$Check.Message

  switch ($Check.Name) {
    "infra/.env" {
      $message = "Falta la configuracion local de produccion en infra/.env."
    }
    "DOMAIN" {
      $message = $message.Replace("DOMAIN configurado:", "Dominio web configurado:")
      $message = $message.Replace("infra/.env existe, pero DOMAIN no esta definido.", "infra/.env existe, pero el dominio web aun no esta definido.")
      $message = $message.Replace("DOMAIN sigue siendo localhost; no sirve para publicacion estable.", "El dominio web sigue siendo localhost y no sirve para abrir la web desde fuera.")
    }
    "DuckDNS" {
      $message = $message.Replace("DuckDNS configurado", "Dominio DuckDNS configurado")
      $message = $message.Replace("Falta infra/duckdns.local.env o esta incompleto.", "Falta la configuracion local de DuckDNS.")
    }
    "Tarea DuckDNS" {
      if ($message -match "^Tarea\s+([^\s]+)\s+activa") {
        $message = $message -replace "^Tarea\s+([^\s]+)\s+activa", "Actualizacion automatica del dominio activa"
      } elseif ($message -match "^Tarea\s+([^\s]+)\s+existe,\s+pero\s+esta\s+desactivada\.$") {
        $message = "La actualizacion automatica del dominio esta pausada."
      } elseif ($message -match "^No existe la tarea programada\s+([^\s]+)\.$") {
        $message = "No existe la tarea automatica que mantiene actualizado el dominio."
      }
    }
    "Ultimo update DuckDNS" {
      $message = $message.Replace("Ultimo update:", "Ultima actualizacion del dominio:")
      $message = $message.Replace("No hay evidencia de updates", "Todavia no hay evidencia de actualizaciones")
    }
    "DNS" {
      $message = $message.Replace("Resolucion A activa para", "Resolucion DNS activa para")
      $message = $message.Replace("aun no resuelve; parece que sigue propagando.", "aun no resuelve; parece que sigue propagando.")
    }
    "Caddy" {
      if ($Check.Status -eq "ok") {
        $message = "El servicio web estable ya esta instalado."
      } elseif ($Check.Status -eq "warn") {
        $message = "El servicio web estable no esta instalado todavia, pero puedo instalarlo automaticamente."
      } else {
        $message = "Falta el servicio web estable y no puedo instalarlo automaticamente en este equipo."
      }
    }
    "Puertos 80/443" {
      if ($Check.Status -eq "ok") {
        if ($message -like "Caddy ya esta corriendo*") {
          $message = "La web estable ya esta usando los puertos 80 y 443."
        } else {
          $message = "Puertos 80 y 443 libres para publicar la web."
        }
      } else {
        $message = $message.Replace("Hay conflictos en", "Los puertos 80/443 estan ocupados por")
      }
    }
    "UPnP" {
      $message = $message.Replace("UPnP visible en el router:", "Router con UPnP detectado:")
      $message = $message.Replace("El router expone UPnP, pero no hay reenvios activos para 80/443.", "El router soporta UPnP, pero aun no hay reenvios activos para 80/443.")
    }
    "IP publica" {
      $message = $message.Replace("IP publica detectada:", "IP publica detectada:")
    }
    "Topologia de red" {
      if ($Check.Status -eq "fail") {
        $message = "Hay doble NAT: este router sale a otra red privada antes de Internet, asi que DuckDNS no puede llegar directamente hasta tu PC."
      }
    }
    "TLS" {
      if ($Check.Status -eq "fail") {
        $message = "HTTPS aun no esta listo porque el certificado publico no ha podido emitirse."
      } elseif ($Check.Status -eq "ok") {
        $message = "HTTPS listo."
      }
    }
  }

  return [pscustomobject]@{
    Name = $Check.Name
    Status = $Check.Status
    Message = $message
  }
}

function Write-FriendlyChecksReport {
  param([Parameter(Mandatory)]$Checks)

  foreach ($check in $Checks) {
    $friendly = Convert-ToFriendlyCheck -Check $check
    switch ($friendly.Status) {
      "ok" { Write-Ok ("[OK] " + $friendly.Message) }
      "warn" { Write-Warn ("[WARN] " + $friendly.Message) }
      default { Write-Fail ("[FAIL] " + $friendly.Message) }
    }
  }
}

function Get-BlockingHint {
  param([Parameter(Mandatory)]$Checks)

  $failed = @($Checks | Where-Object { $_.Status -eq "fail" })
  if ($failed.Count -eq 0) {
    return $null
  }

  foreach ($check in $failed) {
    switch ($check.Name) {
      "DuckDNS" { return "Siguiente paso: ejecuta DUCKDNS SETUP desde el panel para dejar el dominio configurado." }
      "Tarea DuckDNS" { return "Siguiente paso: activa DuckDNS desde el panel para reanudar la actualizacion automatica del dominio." }
      "Ultimo update DuckDNS" { return "Siguiente paso: fuerza un update DuckDNS y revisa si el token o la red estan bien." }
      "DNS" { return "Siguiente paso: espera unos minutos a la propagacion del dominio y vuelve a revisar el estado." }
      "Frontend local" { return "Siguiente paso: inicia VIRU localmente antes de intentar publicar la web estable." }
      "Backend local" { return "Siguiente paso: inicia VIRU localmente antes de intentar publicar la web estable." }
      "Puertos 80/443" { return "Siguiente paso: libera los puertos 80/443 o cierra el proceso que los este usando." }
      "Caddy" { return "Siguiente paso: revisa si winget esta disponible o instala el servicio web estable manualmente." }
      "infra/.env" { return "Siguiente paso: vuelve a ejecutar DUCKDNS SETUP para regenerar la configuracion local." }
      "DOMAIN" { return "Siguiente paso: vuelve a ejecutar DUCKDNS SETUP para sincronizar el dominio web." }
      "Topologia de red" { return "Siguiente paso: abre tambien 80/443 en el router aguas arriba o confirma con tu operador si estas bajo CGNAT." }
      "TLS" { return "Siguiente paso: deja libres 80/443 hacia este PC y vuelve a publicar para que HTTPS pueda emitir el certificado." }
    }
  }

  return "Siguiente paso: corrige los puntos marcados como FAIL y vuelve a intentarlo."
}

function Start-StableWebService {
  param([Parameter(Mandatory)][string]$CaddyCli)

  $paths = Get-CaddyManagedPaths
  if (Test-Path $paths.OutLog) { Remove-Item $paths.OutLog -Force -ErrorAction SilentlyContinue }
  if (Test-Path $paths.ErrLog) { Remove-Item $paths.ErrLog -Force -ErrorAction SilentlyContinue }
  if (Test-Path $paths.PidFile) { Remove-Item $paths.PidFile -Force -ErrorAction SilentlyContinue }
  Unblock-File -Path $CaddyCli -ErrorAction SilentlyContinue

  $domain = (Read-DotEnv -Path (Get-InfraEnvPath))["DOMAIN"]
  $configPath = Join-Path (Get-InfraDir) "Caddyfile"
  $command = "`$env:DOMAIN='$domain'; & '$CaddyCli' run --config '$configPath' --adapter caddyfile"
  $proc = Start-Process -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $command) `
    -RedirectStandardOutput $paths.OutLog `
    -RedirectStandardError $paths.ErrLog `
    -WindowStyle Hidden `
    -PassThru

  Set-Content -Path $paths.PidFile -Value $proc.Id -Encoding ASCII
  Start-Sleep -Seconds 4
}

Write-Section "PUBLICAR WEB ESTABLE"

$duck = Read-DotEnv -Path (Get-DuckDnsConfigPath) -AllowMissing
if ($duck.ContainsKey("DUCKDNS_FQDN")) {
  $envInfo = Ensure-InfraEnv -Domain $duck["DUCKDNS_FQDN"]
  Write-Info ("Dominio estable sincronizado en: " + $envInfo.Path)
}

$upnp = Ensure-UpnpPortMappings -Ports @(80, 443)
if ($upnp.Supported) {
  foreach ($change in $upnp.Changes) {
    switch ($change.Action) {
      "added" { Write-Ok $change.Message }
      "ok" { Write-Info $change.Message }
      "conflict" { Write-Warn $change.Message }
      default { Write-Warn $change.Message }
    }
  }
}

$currentStatus = Get-CaddyRuntimeStatus
if ($currentStatus.Healthy) {
  $publicUrl = if ($currentStatus.Domain) { "https://$($currentStatus.Domain)" } elseif ($duck.ContainsKey("DUCKDNS_FQDN")) { "https://$($duck['DUCKDNS_FQDN'])" } else { $null }
  if ($publicUrl) {
    Write-Ok ("La web estable ya estaba activa en $publicUrl")
  } else {
    Write-Ok "La web estable ya estaba activa."
  }
  exit 0
}

Write-Info "Revisando dominio, DNS, servicios locales y puertos publicos..."
$preflight = Get-PublicDomainPreflight
Write-FriendlyChecksReport -Checks $preflight.Checks

if (-not $preflight.Ready) {
  Write-Host ""
  Write-Warn "La web estable aun no esta lista para publicarse."
  $hint = Get-BlockingHint -Checks $preflight.Checks
  if ($hint) {
    Write-Info $hint
  }
  exit 1
}

try {
  $caddyCli = Ensure-CaddyInstalled
} catch {
  $friendlyError = $_.Exception.Message.Replace("caddy", "el servicio web estable")
  Write-Fail $friendlyError
  exit 1
}

try {
  Start-StableWebService -CaddyCli $caddyCli
} catch {
  Write-Fail $_.Exception.Message
  exit 1
}

$postStatus = Get-CaddyRuntimeStatus
if ($postStatus.Healthy) {
  $publicUrl = if ($postStatus.Domain) { "https://$($postStatus.Domain)" } else { "https://$($preflight.DuckDnsFqdn)" }
  Write-Host ""
  Write-Ok ("Web estable publicada en $publicUrl")
  if ($postStatus.PublishedPorts.Count -gt 0) {
    Write-Info ("Puertos activos: " + ($postStatus.PublishedPorts -join ", "))
  }
  exit 0
}

Write-Host ""
Write-Fail "No pude dejar la web estable activa. Revisa logs/caddy.err.log para ver el detalle tecnico."
if (-not $AutoMode) {
  Write-Info "Puedes volver a mirar el estado con la opcion ESTADO WEB ESTABLE del panel."
}
exit 1
