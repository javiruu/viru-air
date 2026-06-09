# Runbook: Activación y operación de GTFS en `/puerta-a-puerta`

**Estado:** vivo
**Última revisión:** 2026-06-09
**Fuente de verdad:** sí
**Área:** runbooks

## Resumen

Este runbook documenta cómo activar, verificar y operar el provider `gtfs_transit` para que `/puerta-a-puerta` ofrezca horarios reales de transporte público.

## Requisitos previos

- **Variable `DOOR_TO_DOOR_ENABLE_GTFS_TRANSIT=true`** en `.env`
- **Variable `DOOR_TO_DOOR_ENABLE_REAL_PROVIDERS=true`** en `.env`
- **Manifest de feeds** configurado en una de estas fuentes (en orden de prioridad):
  1. `DOOR_TO_DOOR_GTFS_FEEDS_JSON` — string JSON inline
  2. `DOOR_TO_DOOR_GTFS_FEEDS_FILE` — ruta a archivo JSON
  3. Archivo por defecto: `backend/app/door_to_door/providers/gtfs_feeds.json`

## Formato del manifest

```json
[
  {
    "id": "mom_treviso",
    "name": "Mobilità di Marca (MOM) Treviso",
    "region": "treviso",
    "url": "https://mobilitadimarca.it/treviso/google_transit.zip",
    "source_type": "open_data",
    "attribution": "Mobilità di Marca S.p.A.",
    "license_url": "https://creativecommons.org/licenses/by/4.0/",
    "enabled_by_default": true,
    "notes": "✅ VERIFICADO: HTTP 200, 140 rutas bus, 4,431 paradas"
  }
]
```

Campos obligatorios: `id`, `url`.
Campos recomendados: `name`, `region`, `attribution`, `license_url`, `notes`.

## Flujo de activación paso a paso

### 1. Añadir un feed al manifest

Edita `gtfs_feeds.json` (o tu archivo de manifest) y añade una entrada con `id`, `url`, y metadatos.

### 2. Verificar la URL del feed

```bash
curl -I <URL_DEL_FEED>
```

Debe devolver HTTP 200 con Content-Type `application/zip` (o similar). Si requiere autenticación (HTTP 401/403), el feed no es usable directamente — necesita autenticación previa o proxy.

### 3. Activar flags

En `.env`:
```
DOOR_TO_DOOR_ENABLE_REAL_PROVIDERS=true
DOOR_TO_DOOR_ENABLE_GTFS_TRANSIT=true
DOOR_TO_DOOR_GTFS_CACHE_DIR=.gtfs_cache
DOOR_TO_DOOR_GTFS_CACHE_TTL_SECONDS=86400
DOOR_TO_DOOR_GTFS_MAX_WALK_RADIUS_METERS=2000
```

### 4. Verificar con el probe

```bash
cd backend
python -m app.door_to_door.tools.gtfs_probe --feed-id <ID_DEL_FEED>
```

El probe descarga, parsea y muestra:
- Archivos encontrados en el zip
- Número de rutas, paradas, viajes
- Cobertura de fechas (calendar.txt / calendar_dates.txt)
- Paradas cercanas a coordenadas de prueba

### 5. Verificar con healthcheck

Con el backend corriendo:

```bash
curl http://localhost:8000/api/v1/door-to-door/providers/status | jq '.[] | select(.name == "gtfs_transit")'
```

Debe mostrar `enabled: true`, `status: "functional_open_data"`, y `notes` con detalles por feed (✅ cargado / ❌ no cargado).

### 6. Probar una búsqueda real

Envía una búsqueda a `/api/v1/door-to-door/search` con coordenadas que caigan dentro del área de cobertura del feed. Verifica que la respuesta incluya opciones con `source_types: ["open_data"]` y legs con horarios reales.

## Diagnóstico de fallos comunes

| Síntoma | Warning | Causa probable | Solución |
|---------|---------|---------------|----------|
| Feed no aparece en resultados | `GTFS_FEED_UNAVAILABLE` | URL inaccesible, zip corrupto, o faltan archivos requeridos | Verifica URL con curl, revisa logs, comprueba que el zip contiene `agency.txt`, `stops.txt`, `routes.txt`, `trips.txt`, `stop_times.txt` |
| Sin paradas cercanas | `GTFS_NO_NEARBY_STOPS` | El origen/destino está fuera del radio configurado | Aumenta `DOOR_TO_DOOR_GTFS_MAX_WALK_RADIUS_METERS` (máx 5000m) o usa coordenadas más cercanas a paradas |
| Sin servicio para la fecha | `GTFS_NO_SERVICE_FOR_DATE` | El feed tiene cobertura limitada en el tiempo | Comprueba `calendar.txt`/`calendar_dates.txt` del feed. Si solo cubre 2 semanas, necesitas feeds actualizados |
| Sin viajes que encajen | `GTFS_NO_MATCHING_SERVICE` | El horario del viaje no encaja con la ventana del vuelo | Aumenta `min_airport_buffer_minutes` o busca vuelos en horarios con más cobertura |
| Solo un tramo cubierto | `GTFS_PARTIAL_COVERAGE` | El feed cubre origen→aeropuerto pero no aeropuerto→destino (o viceversa) | Añade feeds para la región del tramo faltante |
| Sin tarifas | `GTFS_PRICE_UNAVAILABLE` | El feed no incluye `fare_attributes.txt` | Normal: la mayoría de feeds GTFS no incluyen tarifas. El usuario consulta con el operador |

## Mantenimiento

- Los feeds GTFS caducan: la mayoría cubren 2-12 semanas. Renueva el manifest periódicamente.
- El caché en `.gtfs_cache/` se invalida automáticamente tras `DOOR_TO_DOOR_GTFS_CACHE_TTL_SECONDS` (por defecto 24h).
- Si un feed deja de estar disponible, el sistema usa el caché expirado como fallback.
- Limpia el caché manualmente si sospechas corrupción: `rm -rf .gtfs_cache/`

## Corredores de cobertura

Cada corredor representa una ruta geográfica concreta donde GTFS puede (o podrá) ofrecer horarios reales. Las definiciones completas están en `backend/app/door_to_door/providers/gtfs_corridors.json`.

### Corredores verificados (producen resultados reales)

| Corredor | Aeropuerto | Feeds | Estado | Notas |
|----------|-----------|-------|--------|-------|
| Treviso urbano → TSF | TSF | MOM Treviso | ✅ verificado | Rutas 101/103/6, ~25-35 min, cobertura hasta ago 2026 |
| Venecia → VCE | VCE | ACTV Venice | ⚠️ verificado limitado | Ventana de calendario solo 2 semanas; requiere actualización frecuente |

### Corredores planeados (bloqueados por autenticación)

| Corredor | Aeropuerto | Feeds | Estado | Bloqueo |
|----------|-----------|-------|--------|---------|
| Málaga urbano → AGP | AGP | EMT Málaga (NAP) | ❌ planeado | HTTP 401 — requiere registro en nap.transportes.gob.es |
| Almería → AGP regional | AGP | CTAN Andalucía (NAP) | ❌ planeado | HTTP 401 — requiere registro en NAP |

### Cómo interpretar las señales de corredor

Cuando una búsqueda cae dentro de un corredor conocido, el provider emite warnings:
- `GTFS_CORRIDOR_VERIFIED`: la ruta está en un corredor con feeds funcionales. Si además hay resultados, los horarios son reales.
- `GTFS_CORRIDOR_PLANNED`: la ruta está en un corredor conocido pero los feeds no están accesibles (requieren autenticación o configuración).

Si no se emite ninguna señal de corredor, la ruta está fuera de los corredores conocidos. Puedes añadir nuevos corredores editando `gtfs_corridors.json`.

## Feeds verificados actualmente

Ver `backend/app/door_to_door/providers/gtfs_feeds.json` para la lista completa con estado de verificación y notas.
