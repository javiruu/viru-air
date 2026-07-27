# Live flight tracking desde Watchlist

**Estado:** vivo
**Última revisión:** 2026-07-28
**Fuente de verdad:** sí
**Área:** backend

## Propósito

Este contrato separa dos dominios que conviven en una Watch:

- `FlightWatch` y `PriceSnapshot` siguen representando seguimiento de precio por ruta y fecha;
- `WatchTrackedFlightLeg` enlaza opcionalmente esa Watch con uno o varios vuelos exactos;
- `FlightOperationalSnapshot` conserva observaciones operacionales compartidas por identidad de vuelo.

Una ruta y una fecha no bastan para identificar un vuelo. Si no existen piernas
exactas, el backend intenta primero un autoenlace local y sin cuota: recorre las
capturas frescas de la Watch desde la más nueva, combina proveedor y hora con
ruta y fecha, y exige una única identidad completa observada en Fare Memory.
Una captura sin coincidencia completa no invalida otra captura fresca anterior.
Si una captura produce varias identidades plausibles, el proceso se detiene;
si ninguna produce una coincidencia única, devuelve `identity_missing`.

## Guardado de identidad exacta

`POST /api/v1/search/save-result` admite `legs` como campo opcional. Cada elemento incluye:

- `flight_number` y `carrier_code`, cuando existan;
- `origin_iata` y `destination_iata`;
- `departure_at` y `arrival_at`, cuando existan.

Reglas:

- máximo 8 piernas;
- `sequence` se deriva del orden recibido;
- el servidor deriva `flight_instance_fingerprint`; el cliente no lo elige;
- la primera y última IATA deben coincidir con la ruta guardada y las conexiones deben ser continuas;
- IATA, carrier y número se normalizan;
- guardar `legs` reemplaza el enlace anterior en una transacción;
- omitir `legs` conserva el enlace existente y mantiene compatibilidad con clientes antiguos;
- una Watch manual o legacy sigue siendo válida para precios aunque no tenga identidad operacional.
- una Watch manual o legacy puede recuperar una pierna con
  `identity_source=fare_memory` al consultar `/live` si la evidencia local es
  exacta y no ambigua; el enlace nunca llama a un proveedor externo.

La respuesta de `save-result` incluye `tracking_identity` como `linked`, `updated` o `missing`.

## Endpoint

```http
GET /api/v1/watchlist/{watch_id}/live?refresh=true
Authorization: Bearer <token>
```

- `refresh=true` intenta refrescar solo cuando el snapshot no es reutilizable y se obtiene el lease compartido.
- `refresh=false` devuelve únicamente el estado persistido.
- Watch inexistente, eliminada o perteneciente a otra persona responde `404 watch_not_found`.
- ausencia de proveedor, falta de cobertura, rate limit o caída remota se modelan dentro de una respuesta `200`; no rompen el resto de Watchlist.
- `no_match` y `ambiguous` conservan un cooldown de 5 minutos; `429` respeta `retry_after` entre 30 y 3600 segundos; errores remotos usan 60 segundos.
- cada usuario comparte además un límite de una tanda externa cada 30 segundos; una misma tanda puede resolver hasta 8 piernas.

## Respuesta

```json
{
  "watch_id": "watch-id",
  "coverage": "live",
  "provider_status": "ok",
  "generated_at": "2026-07-21T08:38:00Z",
  "refresh_after_seconds": 60,
  "legs": [
    {
      "sequence": 0,
      "identity": {
        "flight_instance_fingerprint": "fingerprint",
        "flight_number": "AZ61",
        "carrier_code": "AZ",
        "origin_iata": "MAD",
        "destination_iata": "FCO",
        "scheduled_departure_at": "2026-07-21T08:10:00Z",
        "scheduled_arrival_at": "2026-07-21T10:35:00Z"
      },
      "operational": {
        "status": "active",
        "status_raw": "active",
        "observed_at": "2026-07-21T08:37:30Z",
        "expires_at": "2026-07-21T08:38:30Z",
        "freshness": "fresh",
        "provider": "aviationstack",
        "callsign": "ITY61",
        "departure": {
          "scheduled_at": "2026-07-21T08:10:00Z",
          "estimated_at": "2026-07-21T08:24:00Z",
          "actual_at": "2026-07-21T08:27:00Z",
          "terminal": "1",
          "gate": "B26",
          "delay_minutes": 17
        },
        "arrival": {
          "scheduled_at": "2026-07-21T10:35:00Z",
          "estimated_at": "2026-07-21T10:48:00Z",
          "actual_at": null,
          "terminal": "3",
          "gate": null,
          "delay_minutes": 13
        },
        "position": {
          "latitude": 41.02,
          "longitude": 4.83,
          "altitude_m": 10363,
          "speed_mps": 238,
          "heading_deg": 82,
          "on_ground": false
        },
        "registration": "EI-IKU",
        "aircraft_iata": "A320",
        "aircraft_icao": "A320",
        "data_quality": "observed"
      },
      "delay_prediction": {
        "status": "not_applicable",
        "model_version": "viru_rotation_v1",
        "reason": "already_departed"
      }
    }
  ]
}
```

`operational` puede ser `null` por pierna. `position` solo existe cuando latitud y longitud superan la validación de límites; la línea del mapa continúa representando la ruta, nunca una posición estimada.
Todos los timestamps de respuesta representan UTC y se serializan con sufijo `Z`. Altitud y velocidad se normalizan a metros y metros por segundo aunque el proveedor entregue pies, centenas de pies, nudos o km/h.

## Predicción explicable por avión entrante

Cada pierna futura puede incluir `delay_prediction`. El modelo
`viru_rotation_v1` es determinista y auditable: no llama a un LLM ni presenta
una probabilidad calibrada. Busca en los snapshots operacionales compartidos el
tramo anterior de la misma matrícula, exige que termine en el aeropuerto de
origen y limita la rotación a las 25 horas previas. La señal operacional se
reutiliza globalmente, pero la identidad de ruta solo puede proceder de piernas
guardadas por la misma persona autenticada. Esta lectura no crea un cache
paralelo ni consume cuota adicional.

Cuando existe una rotación fiable, la forma es:

```json
{
  "status": "available",
  "model_version": "viru_rotation_v1",
  "risk": "high",
  "risk_score": 90,
  "confidence": "high",
  "predicted_delay_min_minutes": 20,
  "predicted_delay_max_minutes": 40,
  "turnaround_minutes": 20,
  "factor_codes": [
    "incoming_running_late",
    "tight_turnaround",
    "incoming_airborne"
  ],
  "incoming_aircraft": {
    "registration": "EC-ROT",
    "flight_number": "IB1234",
    "origin_iata": "BCN",
    "destination_iata": "MAD",
    "status": "active",
    "scheduled_arrival_at": "2026-07-28T10:30:00Z",
    "estimated_arrival_at": "2026-07-28T11:40:00Z",
    "actual_arrival_at": null,
    "observed_at": "2026-07-28T10:45:00Z",
    "freshness": "fresh"
  }
}
```

El rango parte del mayor entre el retraso oficial de salida y el margen que
falta para una escala base de 45 minutos. El score suma riesgo por escala
ajustada, demora del entrante, señal oficial y avión todavía en vuelo; se
clasifica como `low`, `elevated` o `high`. La confianza baja si el snapshot está
vencido y sube cuando existe hora estimada o real de llegada.

Si falta matrícula, horario, observación o rotación, la respuesta conserva
`status=insufficient_data` y un `reason` explícito. Para vuelos ya salidos o en
estado terminal usa `status=not_applicable`. La UI debe mostrar la estimación
junto al horario oficial, nunca reemplazarlo.

## Selección de proveedor y coste

El backend separa `status_schedule` de `position`. Consulta estado secuencialmente y solo enriquece posición cuando falta. Los campos de estado, horario, terminal y puerta del proveedor principal no son sobrescritos por telemetría posterior; `provider` refleja la procedencia combinada, por ejemplo `aerodatabox+opensky`.

La reserva de cuota se realiza antes de cada llamada en `flight_provider_quota`. La clave del proveedor, unidades gastadas, ventana diaria o mensual y bloqueos remotos sobreviven reinicios. El modo por defecto es `LIVE_FLIGHT_ZERO_COST_ONLY=true`: Amadeus test, Aviationstack, AeroDataBox y OpenSky pueden formar la cadena gratuita; FlightAware y ADS-B Exchange permanecen implementados pero excluidos. Una key de pago por sí sola nunca activa gasto.

## Semántica

### `coverage`

| Valor | Significado |
|---|---|
| `live` | existe al menos una observación fresca |
| `cached` | solo existe el último dato conocido, ya vencido |
| `identity_missing` | la Watch no tiene piernas exactas ni una coincidencia local única en Fare Memory |
| `not_configured` | no hay proveedor operacional activo |
| `no_coverage` | no hubo coincidencia exacta o fue ambigua |
| `temporarily_unavailable` | rate limit, timeout, red o error remoto; puede conservar dato previo |
| `completed` | todas las piernas observadas están en estado terminal |

### `provider_status`

`ok`, `not_configured`, `no_match`, `ambiguous`, `rate_limited` o `unavailable`.

### TTL y cadencia sugerida

- `active`: 60 segundos;
- `scheduled` observado: 5 minutos;
- a menos de 2 horas de salida sin snapshot: 5 minutos;
- dentro de 24 horas: 30 minutos;
- más lejos: 6 horas;
- `landed`, `cancelled` o `diverted`: 6 horas;
- identidad ausente: 1 hora.

El cliente respeta `refresh_after_seconds`, pausa al ocultarse y aborta solicitudes de una Watch que deja de estar seleccionada.

## Concurrencia, retención y privacidad

- un lease persistente por `flight_instance_fingerprint` evita llamadas duplicadas entre procesos y conserva cooldowns de outcomes negativos;
- la unicidad `(flight_instance_fingerprint, provider, observed_at)` deduplica observaciones;
- los snapshots operacionales se podan a 30 días con cadencia máxima de una ejecución cada 6 horas;
- el payload remoto crudo y la API key no se persisten ni se devuelven;
- la consulta filtra siempre por `watch_id` y `user_id`.
- la predicción nunca toma número o ruta desde la Watch de otra persona, aunque
  el snapshot operacional subyacente sea compartido;

## Fuentes relacionadas

- [ADR-005](../../adr/ADR-005-live-operational-flight-tracking.md)
- [ADR-006](../../adr/ADR-006-zero-cost-operational-provider-fallback.md)
- [Watchlist](../../product/watchlist.md)
- [Runbook live flight tracking](../../runbooks/runbook-live-flight-tracking.md)
- [Quick Search contract](quick-search-contract.md)
