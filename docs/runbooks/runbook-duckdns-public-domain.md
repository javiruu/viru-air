# Runbook: DuckDNS + publicacion temporal

**Estado:** vivo  
**Ultima revision:** 2026-06-04  
**Fuente de verdad:** si  
**Area:** runbooks

## Resumen

La historia operativa oficial para exponer `viru-tracker` queda separada en dos modos:

| Modo | Cuando usarlo | URL publica |
|---|---|---|
| `DuckDNS + Caddy` | dominio estable, VPS o servidor con puertos abiertos | `https://tu-subdominio.duckdns.org` |
| `Publico temporal` | laptop, demos rapidas, IP dinamica o CGNAT | URL efimera |

`DuckDNS` es el dominio canonico. El modo temporal no intenta fingir ese dominio: solo abre una URL efimera mientras el frontend corre en local.

## Modo A: DuckDNS + Caddy

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
2. Registra la tarea programada `ViruTracker-DuckDNS`.
3. Fuerza una actualizacion inicial contra DuckDNS.
4. Deja el log en `logs/duckdns-update.log`.

Puedes revisar el estado en cualquier momento:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\duckdns-status.ps1
```

### 3. Levantar Caddy con el dominio estable

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

Desplegar:

```bash
cd infra
DOMAIN=virutracker.duckdns.org docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
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

## Modo B: Publico temporal

Ideal para compartir una instancia local desde laptop sin abrir puertos ni exigir un dominio estable.

### Opcion rapida desde el panel

```text
VIRU_PANEL.bat
  Opcion 1: Iniciar VIRU
  Opcion 4: PUBLICO TEMPORAL START
  Opcion 5: PUBLICO TEMPORAL STATUS
  Opcion 6: PUBLICO TEMPORAL STOP
  Opcion E: PUBLICAR RAPIDO
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
| La tarea no aparece | Reejecuta `scripts/setup-duckdns.ps1` con una PowerShell con permisos normales del usuario |
| El dominio no resuelve | Espera unos minutos y revisa `scripts/duckdns-status.ps1` |
| Caddy no emite TLS | Asegura que `80/443` estan abiertos y que el registro A ya apunta a tu IP publica |
| No sale URL temporal | Comprueba que `ssh` este disponible y revisa `logs/public_temp_tunnel*.log` |
| La URL temporal responde mal | Verifica antes que frontend/backend locales esten vivos en `3000/8000` |

## Referencias

- [Duck DNS install](https://www.duckdns.org/install.jsp)
- [Duck DNS](https://www.duckdns.org/)
- [Caddy Docker Docs](https://caddyserver.com/docs/running#docker)
