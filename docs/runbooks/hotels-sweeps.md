# Runbook Sweeps Hoteleros

**Estado:** vivo  
**Ultima revision:** 2026-06-04 (cierre Fase 10)  
**Fuente de verdad:** si  
**Area:** runbooks

## Resumen

Los sweeps hoteleros existen hoy como proceso ejecutable bajo demanda o mediante un worker opcional separado. No forman parte del startup del API ni tienen scheduler automatico activado por defecto.

## Que hace `run_hotel_sweep`

`run_hotel_sweep(db, provider=...)` crea un `HotelProviderRun`, ejecuta la ingesta del provider indicado y, al terminar, evalua reglas activas para crear `HotelAlertEvent` cuando corresponda.

Estados esperados de `HotelProviderRun`:

1. `running` al iniciar.
2. `completed` si la ingesta termina correctamente y se pudieron evaluar alertas.
3. `failed` si la ingesta o el provider lanzan error; el mensaje queda resumido en `error_message`.

## Comandos exactos

Ejecucion manual de una pasada:

```bash
cd backend
python -m app.worker.hotels_sweep --once --provider mock
```

Loop opcional con intervalo configurado:

```bash
cd backend
python -m app.worker.hotels_sweep --loop --provider mock --sleep-seconds 3600
```

## Variables necesarias

Minimas para sweep mock:

1. `HOTEL_FEATURE_ENABLED=true`
2. `HOTEL_SWEEP_ENABLED=true` solo si se usa el worker `app.worker.hotels_sweep`
3. `HOTEL_PROVIDER=mock` o `--provider mock`

Para Makcorps:

1. `HOTEL_FEATURE_ENABLED=true`
2. `HOTEL_SWEEP_ENABLED=true` si se usa el worker en `--once` o `--loop`
3. `HOTEL_PROVIDER=makcorps` o `--provider makcorps`
4. `MAKCORPS_API_KEY` valido
5. `HOTEL_PROVIDER_TIMEOUT_SECONDS`
6. `HOTEL_PROVIDER_MAX_RETRIES`

## Tablas afectadas

El sweep toca estas tablas del dominio hoteles:

1. `hotel_property`
2. `hotel_provider_alias`
3. `hotel_rate_snapshot`
4. `hotel_provider_run`
5. `hotel_alert_event`

Tambien lee:

1. `hotel_alert_rule`
2. `hotel_tracked_offer`

## Sweep de tracked offers (Fase 8)

Desde la Fase 8, `run_hotel_sweep` tambien ejecuta `sweep_tracked_offers` despues de la ingesta general y la evaluacion de alertas.

Que hace `sweep_tracked_offers`:

1. Lista todos los `HotelTrackedOffer` activos con fechas.
2. Para cada uno, busca el snapshot no vinculado mas barato que coincida (mismo hotel, fechas, huespedes, moneda).
3. Crea un nuevo `HotelRateSnapshot` vinculado al `tracked_offer_id` y `provider_run_id`.
4. Actualiza `current_price` en el tracked offer.
5. Crea `HotelAlertEvent` si el precio cambio respecto al snapshot anterior (con direccion y porcentaje).

La funcion retorna `{"offers_scanned": N, "snapshots_created": M}`.

### Limitacion con mock provider

El mock provider tiene datos estaticos. La ingesta deduplica por `(hotel_id, provider, check_in, check_out, guests, currency, amount)` exactos. Por tanto, ejecuciones sucesivas del sweep con mock no produciran snapshots nuevos para tracked offers.

Con un provider real (Makcorps u otro), cada ejecucion deberia producir nuevos snapshots y actualizar `current_price`.

## Como verificar el resultado

Checks minimos:

1. Ejecutar un sweep manual.
2. Confirmar que existe un `HotelProviderRun` nuevo con `provider`, `status`, `items_processed`, `started_at` y `finished_at`.
3. Si habia reglas activas y rates compatibles, confirmar nuevos registros en `HotelAlertEvent`.

Ejemplo rapido en shell SQL o cliente ORM:

```sql
SELECT provider, status, items_processed, error_message, started_at, finished_at
FROM hotel_provider_run
ORDER BY started_at DESC
LIMIT 5;
```

```sql
SELECT event_type, hotel_id, provider_run_id, created_at
FROM hotel_alert_event
ORDER BY created_at DESC
LIMIT 10;
```

## Scheduler opcional

Existe un worker separado en `app.worker.hotels_sweep` con estas variables:

1. `HOTEL_SWEEP_ENABLED=false` por defecto.
2. `HOTEL_SWEEP_INTERVAL_SECONDS=3600` por defecto.

Ese worker:

1. no se arranca solo con el API;
2. no bloquea requests ni startup;
3. puede ejecutarse `--once` o `--loop`.

## Contrato operativo actual

Desde la revision de Fase 58, el backend HTTP ya no intenta lanzar sweeps hoteleros en su `lifespan`.

Implicaciones:

1. `uvicorn app.main:app` no inicia scheduler hotelero.
2. `HOTEL_SWEEP_ENABLED` solo gobierna el worker `app.worker.hotels_sweep`.
3. Si nadie ejecuta el worker o el comando manual, no habra sweeps nuevos.

### Estrategias de despliegue recomendadas

**Opción A — Cron (recomendado para producción):**

Programar una tarea cron que ejecute el worker `--once` cada hora:

```bash
# crontab -e
0 * * * * cd /ruta/viru-air/backend && HOTEL_SWEEP_ENABLED=true python -m app.worker.hotels_sweep --once --provider makcorps >> logs/sweep.log 2>&1
```

Ventajas: simple, fiable, no consume recursos entre ejecuciones.

**Opción B — Systemd service (recomendado para servidores Linux):**

Crear un servicio systemd que ejecute el worker en `--loop`:

```ini
# /etc/systemd/system/viru-hotel-sweep.service
[Unit]
Description=Viru Air Hotel Sweep Worker
After=network.target

[Service]
Type=simple
WorkingDirectory=/ruta/viru-air/backend
Environment="HOTEL_SWEEP_ENABLED=true"
Environment="HOTEL_PROVIDER=makcorps"
Environment="MAKCORPS_API_KEY=..."
ExecStart=python -m app.worker.hotels_sweep --loop --sleep-seconds 3600
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

Ventajas: reinicio automático, logging vía journald, gestión nativa del SO.

**Opción C — Docker Compose (entorno actual del proyecto):**

Añadir el worker como servicio adicional en `docker-compose.yml`:

```yaml
hotel-sweep:
  build:
    context: .
    dockerfile: infra/docker/backend.Dockerfile
  command: python -m app.worker.hotels_sweep --loop --sleep-seconds 3600
  environment:
    - HOTEL_SWEEP_ENABLED=true
    - HOTEL_PROVIDER=${HOTEL_PROVIDER:-mock}
    - MAKCORPS_API_KEY=${MAKCORPS_API_KEY:-}
  depends_on:
    - backend
```

Ventajas: consistente con el resto de la infraestructura, mismo ciclo de despliegue.

**Opción D — Loop manual (desarrollo/pruebas):**

```bash
cd backend
HOTEL_SWEEP_ENABLED=true python -m app.worker.hotels_sweep --loop --provider mock --sleep-seconds 300
```

Ideal para desarrollo local con mock provider.

## Limitacion actual

No hay scheduler automatico integrado en el arranque del backend. Si nadie ejecuta el comando manual ni levanta el worker opcional, no habra sweeps hoteleros nuevos.
