# Door-to-door API contract

**Estado:** vivo
**Última revisión:** 2026-05-21
**Fuente de verdad:** sí
**Área:** backend

> **V1.2** añade GTFS/open data transit provider (`gtfs_transit`) con `source_type=open_data` y `status=functional_open_data`.

## Resumen

Contrato backend de `Puerta a puerta` para planificar itinerarios normalizados alrededor de un vuelo guardado.

Base path: `/api/v1/door-to-door`

Todos los endpoints requieren usuario autenticado.

## POST `/search`

Calcula opciones puerta a puerta para un `flight_watch_id` del usuario.

También acepta alias `watchId` en el payload para compatibilidad frontend.

### Request

```json
{
  "flight_watch_id": "watch_123",
  "origin": {
    "type": "city",
    "label": "Almería",
    "lat": 36.834,
    "lng": -2.463
  },
  "final_destination": {
    "type": "city",
    "label": "Treviso centro"
  },
  "preferences": {
    "min_airport_buffer_minutes": 120,
    "max_price": 80,
    "passengers": 1,
    "luggage": "cabin",
    "allow_bus": true,
    "allow_train": true,
    "allow_rideshare": true,
    "allow_shuttle": true,
    "allow_taxi": false,
    "allow_car": true,
    "public_transport_only": false,
    "sort_by": "best_balance"
  },
  "save_origin_as_default": false
}
```

### Response

```json
{
  "flight": {
    "origin_airport": "AGP",
    "destination_airport": "TSF",
    "departure_at": "2026-06-14T14:20:00+02:00",
    "arrival_at": "2026-06-14T16:55:00+02:00",
    "flight_time_confidence": "estimated"
  },
  "summary": {
    "recommended_option_id": "option_best",
    "cheapest_option_id": "option_cheap",
    "lowest_risk_option_id": "option_safe",
    "history_id": "history_123",
    "chosen_option_id": null
  },
  "options": [],
  "warnings": []
}
```

V1.1 devuelve combinaciones según providers habilitados por entorno y guarda un historial resumido del cálculo.

Warnings relevantes:

- `ESTIMATED_MOCK_DATA`: hay opciones mock estimadas activas.
- `FLIGHT_TIME_ESTIMATED`: no hay horario completo del vuelo guardado; se usa salida conocida y llegada estimada.
- `NO_REAL_PROVIDER_COVERAGE`: no hay providers reales activos para la ruta/configuración actual.
- `NO_COVERAGE`: no quedan opciones válidas tras filtros/cobertura.
- `UNCONFIRMED_PRICE`: hay opciones sin precio confirmado (por ejemplo deeplink) que se mantienen para abrir proveedor.
- `GOOGLE_ROUTES_UNAVAILABLE`: no se pudo calcular rutas reales con Google en ese intento.
- `PROVIDER_PARTIAL_COVERAGE`: un provider activo solo pudo cubrir parte de la consulta.
- `BLABLACAR_DEEPLINK_PARTIAL`: el deeplink de BlaBlaCar no pudo prellenar todos los parámetros (ej. aeropuerto sin ciudad mapeada). El enlace se mantiene; el usuario debe ajustar búsqueda en proveedor.
- `GOOPTI_DEEPLINK_PARTIAL`: el deeplink de GoOpti no pudo prellenar todos los parámetros. El enlace se mantiene; el usuario debe ajustar búsqueda en proveedor.
- `GTFS_FEED_UNAVAILABLE`: no se pudo descargar o parsear el feed GTFS configurado. La búsqueda continúa con otros providers.
- `GTFS_PARTIAL_COVERAGE`: el feed GTFS tiene datos pero no cubre la ruta/origen/destino completo.
- `GTFS_NO_MATCHING_SERVICE`: el feed está disponible pero no se encontraron viajes para la consulta.
- `GTFS_PRICE_UNAVAILABLE`: se encontraron horarios GTFS pero sin información de tarifa.

### Filtros y `NO_COVERAGE`

- `max_price` se interpreta como precio máximo del grupo. Una opción queda disponible si su `total_price_min` no supera ese valor.
- `public_transport_only` limita modos terrestres a bus, tren y caminata.
- Los flags `allow_*` ocultan opciones que contienen tramos terrestres no permitidos.
- Si no queda ninguna opción, `options` será `[]` y `warnings` incluirá `NO_COVERAGE`.
- Si `max_price` está definido y una opción no tiene precio confirmado (`total_price_min = null`), la opción puede mantenerse y se reporta `UNCONFIRMED_PRICE`.
- Si `final_destination.type` es `airport_only`, el backend omite el tramo terrestre de llegada.
- Si `allow_rideshare` es `false`, no se ofrecen opciones de BlaBlaCar.
- Si `allow_shuttle` es `false`, no se ofrecen opciones de GoOpti.
- Si `public_transport_only` es `true`, no se ofrecen opciones de rideshare/shuttle (salvo decisión explícita documentada).
- Si `max_price` está definido y una opción no tiene precio confirmado (`total_price_min = null`), la opción se mantiene con warning `UNCONFIRMED_PRICE`.
- Si `public_transport_only` es `true`, se priorizan providers GTFS/open data y se ocultan rideshare/shuttle.
- Si `allow_bus` es `false`, no se devuelven opciones GTFS con `mode=bus`.
- Si `allow_train` es `false`, no se devuelven opciones GTFS con `mode=train` o `mode=metro`.
- Si `final_destination.type` es `airport_only`, GTFS no calcula tramo terrestre final.

### Opción elegida

`summary.chosen_option_id` devuelve la última opción elegida para ese watch si esa opción sigue presente en los resultados filtrados.

## GET `/suggestions`

Devuelve sugerencias para autocomplete.

Query params:

- `q`: texto opcional.

Si Google Places está activo (`DOOR_TO_DOOR_ENABLE_REAL_PROVIDERS=1`, `DOOR_TO_DOOR_ENABLE_GOOGLE_PLACES=1`, `GOOGLE_MAPS_API_KEY`), mezcla sugerencias `source_type: "api"` con las `local_static`.

Cada sugerencia conserva su fuente y puede incluir `place_id` para resolver coordenadas reales en búsquedas posteriores.

## GET `/providers/status`

Devuelve el registro de providers con estado funcional real:

- `name`
- `enabled`
- `status` (`functional_api`, `functional_mock`, `functional_deeplink`, `functional_open_data`, `functional_scraper`, `scraper_base_only`, `deeplink_stub`, `pure_stub`, `disabled`)
- `source_type` (`api`, `open_data`, `aggregator`, `deeplink`, `scraper`, `mock`)
- `production_ready`
- `supports_search`
- `supports_booking_url`
- `has_tests`
- `notes`

## Saved location

- `GET /saved-location`: devuelve la ubicación global guardada o `null`.
- `PUT /saved-location`: guarda o reemplaza la ubicación global.
- `DELETE /saved-location`: borra la ubicación global.

La ubicación guardada contiene tipo, etiqueta, lat/lng opcionales y `updated_at`.

## History

- `GET /history?watch_id=...`: últimos cálculos del usuario, opcionalmente filtrados por watch.
- `POST /history/{history_id}/chosen`: marca una opción como elegida.

La retención funcional V1 es 90 días.

## Providers

La interfaz común de providers vive en `app.door_to_door.providers.base.DoorToDoorProvider`.

V1.1 incluye:

- mock provider configurable por flag (`DOOR_TO_DOOR_ENABLE_MOCK_PROVIDER`);
- deeplink providers funcionales para primer paso real parcial (`blablacar_deeplink`, `goopti_deeplink`) bajo `DOOR_TO_DOOR_ENABLE_REAL_PROVIDERS`;
  - `blablacar_deeplink`: genera URL de búsqueda en BlaBlaCar con origen, ciudad del aeropuerto de salida y fecha del vuelo. No confirma precio ni disponibilidad. Respeta `allow_rideshare`.
  - `goopti_deeplink`: genera URL de búsqueda en GoOpti con aeropuerto de llegada, destino final y fecha de llegada. No confirma precio ni disponibilidad. Respeta `allow_shuttle` y `airport_only`.
- `gtfs_transit` como primer provider open_data real para horarios de transporte público, activable con:
  - `DOOR_TO_DOOR_ENABLE_REAL_PROVIDERS`
  - `DOOR_TO_DOOR_ENABLE_GTFS_TRANSIT`
  - `DOOR_TO_DOOR_GTFS_FEEDS_JSON` con al menos un feed configurado
  - `gtfs_transit`: consulta horarios reales desde feeds GTFS estáticos. Descarga, cachea y parsea archivos mínimos (`agency.txt`, `stops.txt`, `routes.txt`, `trips.txt`, `stop_times.txt`, `calendar.txt`/`calendar_dates.txt`). Devuelve opciones con `source_type="open_data"`, `confidence="cached"`/`"live"`, `provider="gtfs_transit"`, sin precio confirmado (`UNCONFIRMED_PRICE`). Respeta `allow_bus`, `allow_train`, `public_transport_only` y `airport_only`. No genera `booking_url`. Sin scraping. Sin login.
- `google_routes` como primer provider API real para duración/distancia (sin precio confirmado), activable con:
  - `DOOR_TO_DOOR_ENABLE_REAL_PROVIDERS`
  - `DOOR_TO_DOOR_ENABLE_GOOGLE_ROUTES`
  - `GOOGLE_MAPS_API_KEY`
- `google_places` para suggestions reales, activable con:
  - `DOOR_TO_DOOR_ENABLE_REAL_PROVIDERS`
  - `DOOR_TO_DOOR_ENABLE_GOOGLE_PLACES`
  - `GOOGLE_MAPS_API_KEY`
- placeholders/stubs para APIs, open data y agregadores;
- scraper base + status explícito (`scraper_base_only`) para BlaBlaCar, GoOpti, ALSA y Renfe, controlado por `DOOR_TO_DOOR_ENABLE_SCRAPERS`.

Los scrapers están apagados por defecto y requieren flag explícita por proveedor. No se permite login scraping, captcha bypass, evasión de protecciones ni sesiones privadas.
