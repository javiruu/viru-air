# Door-to-door API contract

**Estado:** vivo
**Última revisión:** 2026-05-20
**Fuente de verdad:** sí
**Área:** backend

## Resumen

Contrato backend de `Puerta a puerta` para planificar itinerarios normalizados alrededor de un vuelo guardado.

Base path: `/api/v1/door-to-door`

Todos los endpoints requieren usuario autenticado.

## POST `/search`

Calcula opciones puerta a puerta para un `flight_watch_id` del usuario.

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

V1 devuelve opciones mock estimadas y guarda un historial resumido del cálculo.

## GET `/suggestions`

Devuelve sugerencias mock para autocomplete.

Query params:

- `q`: texto opcional.

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

V1 incluye:

- mock provider activo;
- placeholders para APIs, open data y agregadores;
- scraper base y adapters opt-in para BlaBlaCar, GoOpti, ALSA y Renfe.

Los scrapers están apagados por defecto y requieren flag explícita por proveedor. No se permite login scraping, captcha bypass, evasión de protecciones ni sesiones privadas.
