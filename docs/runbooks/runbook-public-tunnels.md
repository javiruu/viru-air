# Runbook: publicacion web por tuneles

**Estado:** vivo
**Ultima revision:** 2026-06-23
**Fuente de verdad:** si
**Area:** runbooks

## Resumen

La historia operativa oficial para exponer `viru-air` desde un PC local pasa a ser:

| Camino | Cuando usarlo | URL publica |
|---|---|---|
| `Cloudflare Tunnel` | primer proveedor que intenta el panel | URL publica de Cloudflare o dominio propio |
| `Tailscale Funnel` | segundo proveedor que intenta el panel | URL publica de Tailscale |

La operativa visible ya no depende de IP publica domestica, puertos `80/443`, routers, UPnP ni DuckDNS.
El flujo simplificado intenta dejar las dos URLs activas a la vez cuando el equipo lo permite.

## Flujo recomendado desde el panel

```text
VIRU_PANEL.bat
  Opcion 4: PUBLICAR WEB
  Opcion 5: ESTADO WEB PUBLICA
  Opcion 6: DETENER WEB PUBLICA
  Opcion 7: VER LOGS PUBLICACION
```

`PUBLICAR WEB` comprueba la app local, intenta `Cloudflare Tunnel`, intenta `Tailscale Funnel` y devuelve todas las URLs que queden disponibles en ese momento.

## Requisitos locales

- frontend vivo en `3000`
- backend vivo en `8000`
- `cloudflared` instalado o instalable por `winget`
- `tailscale` instalado o instalable por `winget`
- sesion iniciada en Tailscale para que Funnel pueda quedar listo

## Cloudflare Tunnel

### Preparacion automatizada

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\cloudflare-tunnel-setup.ps1 -InstallIfMissing
```

Si ya tienes el tunnel creado en Cloudflare, puedes dejar preparada la config local de una vez:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\cloudflare-tunnel-setup.ps1 `
  -InstallIfMissing `
  -Domain viru-air.example.com `
  -TunnelId <tu-tunnel-id-o-nombre> `
  -Hostname viru-air.example.com `
  -CredentialsFile C:\Users\TU_USUARIO\.cloudflared\<tu-tunnel>.json
```

### Modo rapido

Si `cloudflared` esta instalado pero todavia no has preparado un tunel named, el panel puede abrir un quick tunnel:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\public-stable-start.ps1
```

Eso genera una URL publica temporal de Cloudflare sin pedir puertos abiertos en casa.

### Modo dominio propio

Si quieres un hostname propio, crea un tunel named en tu cuenta Cloudflare y deja una config local en:

- `infra/cloudflare-tunnel.local.yml`
- o `infra/cloudflare-tunnel.local.yaml`

Puedes partir de:

- `infra/cloudflare-tunnel.example.yml`

Luego el mismo flujo del panel reutiliza esa configuracion automaticamente.

### Diagnostico rapido

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\cloudflare-tunnel-status.ps1
```

Mensajes esperados:

- `Cloudflare Tunnel activo`
- `Cloudflare Tunnel no esta autorizado todavia`
- `Cloudflare Tunnel no esta instalado`
- `Falta asociar hostname/dominio`

## Tailscale Funnel

### Preparacion automatizada

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\tailscale-funnel-setup.ps1 -InstallIfMissing
```

Eso deja Tailscale instalado cuando sea posible. El login final puede seguir abriendo el flujo interactivo de Tailscale, asi que en algunos equipos todavia hara falta completar `tailscale up`.

Si prefieres revisar solo Tailscale:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\tailscale-funnel-start.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\tailscale-funnel-status.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\tailscale-funnel-stop.ps1
```

Mensajes esperados:

- `Tailscale Funnel activo`
- `Tailscale no esta instalado`
- `Tailscale no tiene sesion iniciada`
- `Falta activar Funnel`

## Logs

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\stable-tunnel-logs.ps1
```

Los logs se guardan en `logs/` y el panel muestra automaticamente las URLs publicas disponibles y el siguiente paso humano cuando falte alguna.

## Troubleshooting

| Problema | Solucion |
|---|---|
| Frontend o backend no aparecen | Inicia VIRU localmente antes de abrir el tunel |
| `cloudflared` no esta instalado | Instala Cloudflare Tunnel o deja que el script lo intente por `winget`, luego repite `PUBLICAR WEB` |
| Cloudflare abre quick tunnel pero quieres dominio propio | Crea un tunel named y añade `infra/cloudflare-tunnel.local.yml` |
| Tailscale no aparece | Instala Tailscale en el equipo |
| Tailscale aparece pero Funnel no abre | Inicia sesion y revisa `tailscale funnel status --json` |
| Solo aparece una de las dos URLs | La otra no ha quedado lista todavia; usa `ESTADO WEB PUBLICA` para ver el siguiente paso concreto |
| No ves ninguna URL publica | Mira `scripts/stable-tunnel-logs.ps1` o la opcion `VER LOGS PUBLICACION` |

## Referencias

- [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
- [Tailscale Funnel](https://tailscale.com/kb/1223/funnel)
