# Runbook: publicacion web por tuneles

**Estado:** vivo
**Ultima revision:** 2026-06-23
**Fuente de verdad:** si
**Area:** runbooks

## Resumen

La historia operativa oficial para exponer `viru-tracker` desde un PC local pasa a ser:

| Camino | Cuando usarlo | URL publica |
|---|---|---|
| `Cloudflare Tunnel` | camino estable principal | URL publica de Cloudflare o dominio propio |
| `Tailscale Funnel` | alternativa estable cuando ya usas Tailscale | URL publica de Tailscale |

La operativa visible ya no depende de IP publica domestica, puertos `80/443`, routers, UPnP ni DuckDNS.

## Flujo recomendado desde el panel

```text
VIRU_PANEL.bat
  Opcion 4: PUBLICAR WEB ESTABLE
  Opcion 5: ESTADO WEB ESTABLE
  Opcion 6: DETENER WEB ESTABLE
  Opcion 7: USAR TAILSCALE FUNNEL
  Opcion 8: ESTADO TAILSCALE FUNNEL
  Opcion 9: DETENER TAILSCALE FUNNEL
  Opcion A: Ver logs del tunel
```

`PUBLICAR WEB ESTABLE` intenta abrir la web con `Cloudflare Tunnel` por defecto.

## Requisitos locales

- frontend vivo en `3000`
- backend vivo en `8000`
- `cloudflared` instalado para la ruta principal
- `tailscale` instalado y con sesion iniciada si quieres usar la alternativa Funnel

## Cloudflare Tunnel

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

Si prefieres Tailscale:

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

Los logs se guardan en `logs/` y el panel muestra automaticamente el proveedor activo, la URL publica y el siguiente paso humano.

## Troubleshooting

| Problema | Solucion |
|---|---|
| Frontend o backend no aparecen | Inicia VIRU localmente antes de abrir el tunel |
| `cloudflared` no esta instalado | Instala Cloudflare Tunnel y repite `PUBLICAR WEB ESTABLE` |
| Cloudflare abre quick tunnel pero quieres dominio propio | Crea un tunel named y añade `infra/cloudflare-tunnel.local.yml` |
| Tailscale no aparece | Instala Tailscale en el equipo |
| Tailscale aparece pero Funnel no abre | Inicia sesion y revisa `tailscale funnel status --json` |
| No ves URL publica | Mira `scripts/stable-tunnel-logs.ps1` o la opcion `Ver logs del tunel` |

## Referencias

- [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
- [Tailscale Funnel](https://tailscale.com/kb/1223/funnel)
