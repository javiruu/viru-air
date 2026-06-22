# Runbook: DuckDNS + publicacion temporal

**Estado:** vivo  
**Ultima revision:** 2026-06-22  
**Fuente de verdad:** si  
**Area:** runbooks

## Resumen

La historia operativa oficial para exponer `viru-tracker` queda separada en dos modos:

| Modo | Cuando usarlo | URL publica |
|---|---|---|
| `DuckDNS + Caddy nativo` | dominio estable en Windows con frontend/backend locales | `https://tu-subdominio.duckdns.org` |
| `Publico temporal` | laptop, demos rapidas, IP dinamica o CGNAT | URL efimera |

`DuckDNS` es el dominio canonico. El modo temporal no intenta fingir ese dominio: solo abre una URL efimera mientras el frontend corre en local.

## Modo A: DuckDNS + Caddy nativo

Ideal para despliegue estable con IP publica y puertos `80/443` accesibles.

### 1. Crear el subdominio DuckDNS

1. Entra en [Duck DNS](https://www.duckdns.org/).
2. Crea tu subdominio, por ejemplo `virutracker`.
3. Guarda el token asociado a tu cuenta.

### 2. Preparar el updater local

Desde la raiz del repo:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-duckdns.ps1 -Domain virutracker -Token <tu-token>
```

Ese setup:

1. Escribe `infra/duckdns.local.env`.
2. Genera o sincroniza `infra/.env` con `DOMAIN`, `NEXT_PUBLIC_API_URL`, `JWT_SECRET` y `APP_ENV`.
3. Registra la tarea programada `ViruTracker-DuckDNS`.
4. Fuerza una actualizacion inicial contra DuckDNS.
5. Deja el log en `logs/duckdns-update.log`.
6. Lanza un preflight de publicacion estable.
7. Intenta instalar/arrancar `Caddy` nativo automaticamente solo si frontend, backend, `DOMAIN`, DNS y puertos `80/443` estan listos.

Puedes revisar el estado en cualquier momento:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\duckdns-status.ps1
```

### 3. Levantar Caddy nativo con el dominio estable

```bash
cp infra/.env.prod.example infra/.env
```

Editar `infra/.env`:

```env
DOMAIN=virutracker.duckdns.org
NEXT_PUBLIC_API_URL=/api/v1
JWT_SECRET=<genera-un-valor-seguro>
APP_ENV=production
```

Validar prerequisitos antes de levantar Caddy:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\public-domain-preflight.ps1
```

Iniciar `frontend` y `backend` localmente, luego gestionar Caddy desde scripts:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\caddy-start.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\caddy-status.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\caddy-stop.ps1
```

### 4. Verificar

```bash
curl https://virutracker.duckdns.org/api/v1/health
curl -I https://virutracker.duckdns.org/
```

Si frontend y API comparten el mismo dominio, no hace falta configurar CORS adicional.

Para API separada:

```env
DOMAIN=api.virutracker.duckdns.org
CORS_ALLOW_ORIGINS=https://virutracker.duckdns.org
```

### 5. Activar o pausar DuckDNS

Mantener la config local pero pausar o reactivar la tarea programada:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\duckdns-disable.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\duckdns-enable.ps1
```

## Modo B: Publico temporal

Ideal para compartir una instancia local desde laptop sin abrir puertos ni exigir un dominio estable.

### Opcion rapida desde el panel

```text
VIRU_PANEL.bat
  Opcion 1: Iniciar VIRU
  Opcion 4: PUBLICO TEMPORAL START
  Opcion 5: PUBLICO TEMPORAL STATUS
  Opcion 6: PUBLICO TEMPORAL STOP
  Opcion G: PREFLIGHT PUBLICACION ESTABLE
  Opcion H: CADDY START
  Opcion I: CADDY STATUS
  Opcion J: CADDY STOP
  Opcion K: PUBLICAR RAPIDO
```

### Flujo manual

```powershell
# Terminal 1
.\iniciar_viru.ps1 -Foreground

# Terminal 2
.\scripts\iniciar_viru_publico.ps1
```

El script usa `localhost.run` y devuelve una URL efimera. No sustituye el dominio DuckDNS; solo sirve para compartir la sesion local mientras dura el tunel.

## Troubleshooting

| Problema | Solucion |
|---|---|
| DuckDNS responde `KO` | Verifica `DUCKDNS_DOMAIN` y `DUCKDNS_TOKEN` en `infra/duckdns.local.env` |
| DuckDNS esta pausado | Reactiva la tarea con `scripts/duckdns-enable.ps1` o la opcion `C` del panel |
| La tarea no aparece | Reejecuta `scripts/setup-duckdns.ps1` con una PowerShell con permisos normales del usuario |
| El dominio no resuelve | Espera unos minutos y revisa `scripts/duckdns-status.ps1` o `scripts/public-domain-preflight.ps1` |
| Caddy no estaba instalado | `scripts/caddy-start.ps1` intenta instalarlo con `winget` automaticamente |
| Caddy no arranca | Revisa `infra/.env`, `DOMAIN`, frontend/backend locales y ejecuta `scripts/public-domain-preflight.ps1` |
| Caddy no emite TLS | Asegura que `80/443` estan abiertos y que el registro A ya apunta a tu IP publica |
| El dominio sigue sin responder desde fuera | Verifica firewall/router/NAT. En Windows, abrir `80/443` requiere permisos de administrador |
| No sale URL temporal | Comprueba que `ssh` este disponible y revisa `logs/public_temp_tunnel*.log` |
| La URL temporal responde mal | Verifica antes que frontend/backend locales esten vivos en `3000/8000` |

## Referencias

- [Duck DNS install](https://www.duckdns.org/install.jsp)
- [Duck DNS](https://www.duckdns.org/)
- [Caddy Docs](https://caddyserver.com/docs/)
