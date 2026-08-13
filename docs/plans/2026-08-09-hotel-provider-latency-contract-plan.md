# Hotel Provider Latency Contract Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Definir y persistir de forma segura la medición de latencia provider hotelera por run, sin activar provider live.

**Estado de esta frontera:** contrato e instrumentación de fixture están implementados; la persistencia agregada por run está implementada en la migración `0053_hotel_provider_latency_aggregate` y validada con tests/roundtrip. H37 y H41 mantienen pendientes el canary live, la evidencia field y los dashboards/SLO productivos.

**Architecture:** La duración se medirá alrededor de la llamada bloqueante con un reloj monotónico y se expresará en milisegundos enteros, separada del tiempo total del run. En esta frontera se fija el envelope, la taxonomía, la política de redacción, la persistencia agregada bounded por run y el plan de canary; la migración es explícita y compatible con históricos.

**Tech Stack:** Python estándar (`time.monotonic`), FastAPI/SQLAlchemy en la futura implementación, pytest/Ruff, documentación H37/H41/H43/H45.

---

## Alcance de esta frontera

No se activa ningún provider live. El contrato dispone de una instrumentación opcional de fixture/canary (`latency_sink`) alrededor de las llamadas efectivas de ingestion, revalidation y area search; usada sin run sigue siendo no persistente. Cuando existe un `HotelProviderRun`, el sink se compone con un acumulador y persiste agregados multi-operación bounded mediante la migración `0053_hotel_provider_latency_aggregate`; el canary real y las métricas field siguen pendientes. No se debe presentar ninguna latencia existente de `QuickSearchCacheEntry` como latencia de sweeps hoteleros.

## Contrato de medición

### Envelope interno futuro

```json
{
  "operation": "ingestion|revalidation|area_search|detail|rates|search",
  "provider": "mock|makcorps|local|unknown",
  "outcome": "success|empty|partial|rate_limited|timeout|unavailable|unsupported|invalid_response|failed|skipped_mapping|skipped_budget|skipped_circuit|skipped_window",
  "duration_ms": null,
  "attempt": 1,
  "error_code": "safe_code_or_null"
}
```

- `duration_ms` es la duración de la llamada al provider, no el tiempo total de serialización, DB, mapping o UI. En este documento `null` es un placeholder de contrato: no es una medición observada; la futura implementación emitirá un entero no negativo cuando exista una llamada efectiva.
- Se mide con `time.monotonic()` antes y después del bloque bloqueante.
- Se normaliza a entero no negativo y se aplica un techo de seguridad antes de persistir/exportar.
- Una excepción debe producir igualmente un outcome terminal medible; no se descarta la muestra por fallar.
- `attempt` comienza en 1 para cada llamada efectiva; una denegación de budget/circuit antes de I/O no se cuenta como llamada provider.
- `error_code` es allowlisted y nunca contiene `str(exc)`, URL, query, headers, payload ni stack.

### Separación de relojes

| Señal | Significado | Fuente futura |
|---|---|---|
| `provider_duration_ms` | Tiempo de la llamada bloqueante externa | `time.monotonic()` alrededor del adapter |
| `run_duration_seconds` | Tiempo total de `HotelProviderRun` | `started_at`/`finished_at` persistidos |
| `lease_duration` | Tiempo de ownership del lock | `lock_acquired_at`/`lease_expires_at` |
| `db_duration_ms` | Tiempo de persistencia/mapping, si se decide medir | medición separada, no derivada |

Nunca se debe usar `run_duration_seconds` como sustituto de latencia provider.

## Privacidad y cardinalidad

- No incluir `user_id`, `hotel_id`, `tracked_offer_id`, fingerprints, correlation IDs, intents, provider request IDs inseguros, URLs, credenciales ni payloads.
- Provider, operation, outcome y error code son dimensiones allowlisted de baja cardinalidad.
- El detalle por entidad permanecerá fuera del endpoint admin agregado; si se necesita investigación, se usará logging redacted con acceso controlado.
- Los valores desconocidos se normalizan a `unknown`; las claves arbitrarias no se conservan.

## Suficiencia y claims

- Una sola muestra o fixture no demuestra p50/p95/p99 ni cumplimiento de Web Vitals.
- El canary debe separar fixture/mock, provider disabled, provider live y errores simulados.
- Para cada combinación provider/operation/outcome se conservará `sample_count`; cualquier percentil con volumen insuficiente se etiqueta `non_conclusive`.
- No se fija un umbral universal de latencia antes de tener hardware, provider, operación, ventana y baseline definidos.
- El dashboard futuro deberá mostrar muestras, ventana, estado de suficiencia y si el valor es lab/canary/field.

## Plan futuro de implementación

### Task 1: Añadir helper puro de medición

**Files:**
- Modify: `backend/app/services/hotel_observability_metrics.py` o crear un módulo de observabilidad provider dedicado.
- Test: `backend/tests/unit/test_hotel_provider_latency.py`.

**Steps:**
1. Testear duración no negativa con reloj monotónico controlado.
2. Testear excepción con outcome/error code terminal.
3. Testear clamp/techo y rechazo de dimensiones no allowlisted.
4. Implementar helper sin DB ni efectos externos.
5. Ejecutar `python -m pytest ...` y Ruff.

### Task 2: Instrumentar adapters en modo fixture/canary

**Estado:** instrumentación local y persistencia agregada por run están implementadas y cubiertas para ingestion, revalidation y area search; canary real pendiente.

**Files:**
- Modify: `backend/app/hotels/ingestion.py`, `backend/app/services/hotels_service.py` y adapters solo donde exista una llamada efectiva.
- Test: tests unitarios de ingestion/sweep y provider contract.

**Rules:**
- Medir únicamente alrededor de `fetch_hotels`/`fetch_hotel_rates`/operaciones equivalentes.
- No medir budget/circuit denials como provider latency.
- Mantener propagación de outcome aun cuando la llamada falle.
- No cambiar activación por defecto ni habilitar provider live.

### Task 3: Persistencia compatible

**Estado:** implementada y validada mediante modelo `HotelProviderLatencyAggregate`, migración `0053`, upsert sin commit interno, lectura admin bounded y roundtrip SQLite. No hay filas sintéticas para runs históricos sin muestras.

**Files:**
- Modify: `backend/app/infrastructure/db/models.py`.
- Create: nueva migración Alembic posterior a la revisión del contrato.
- Modify: `backend/app/services/hotel_observability_metrics.py`, `backend/app/api/v1/admin.py`.
- Tests: migración roundtrip SQLite/PostgreSQL-compatible, endpoint admin y privacidad.

**Rules:**
- La persistencia soporta varias operaciones, intentos y outcomes dentro de un mismo `HotelProviderRun`; cada grupo se reemplaza de forma idempotente dentro del run, sin sobrescribir otros grupos.
- La forma preferente es una tabla/event ledger agregada por `(run, provider, operation, outcome)` con `sample_count` y estadísticas derivadas. Una columna nullable `provider_latency_ms` en `HotelProviderRun` solo será válida si se demuestra que el run representa exactamente una llamada provider.
- No elegir columna simple hasta resolver y probar la cardinalidad multi-operación del sweep.
- El endpoint debe distinguir `sample_count`, `avg` y percentiles no concluyentes.

### Task 4: Canary y evidencia

**Files:**
- Modify: `docs/reference/backend/hoteles-benchmark-rate-limits-locks-cost-h37.md`.
- Modify: `docs/reference/backend/hoteles-observability-e2e-h41.md`.
- Modify: `docs/reference/backend/hoteles-flags-canary-killswitch-h43.md`.
- Modify: `docs/reference/backend/hoteles-release-canary-smoke-rollback-h45.md`.
- Create/modify: comando QA y evidencia redacted.

**Gates:**
- fixture mock: outcomes y duración controlada;
- provider disabled: cero llamadas y cero muestras provider;
- error/timeout/429 simulado: outcome terminal y error code seguro;
- redaction adversarial: cero secretos/PII/URLs;
- suficiente volumen: percentiles solo cuando proceda;
- rollback: flag off sin side effects.

## Criterio de salida de esta frontera

Esta frontera queda cerrada cuando:

1. el contrato está enlazado desde H37/H41, distingue la persistencia implementada de la preparación de canary y no contradice H09/H43/H45;
2. queda explícita la diferencia entre latencia provider y duración total de run;
3. no existe claim de latencia productiva: la instrumentación aislada sin run es no persistente, mientras que los runs persistidos usan agregados bounded; el provider live sigue apagado;
4. la futura implementación tiene tests, límites, privacidad y canary definidos;
5. el provider live permanece apagado por defecto.
