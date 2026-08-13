# Hotel Mock Canary and Kill-Switch Design

**Fecha:** 2026-08-09
**Estado:** aprobado para implementación local/fixture
**Relacionado con:** H37, H41, H43, H45 y `2026-08-09-hotel-provider-latency-persistence-plan.md`

## Objetivo

Cerrar la siguiente frontera segura sin activar provider live: ejecutar un canary reproducible con el provider `mock` sobre una DB SQLite aislada, verificar la persistencia de latencia por `HotelProviderRun` y demostrar que el kill switch global bloquea antes de cualquier I/O o mutación de datos.

## Alcance aprobado

- Perfil `local_fixture` o `local_demo` explícito.
- Provider `mock` únicamente.
- Base de datos temporal/aislada proporcionada explícitamente por el runner.
- Evidencia JSON redacted y bounded.
- Caso nominal: run mock completado, muestras de latencia y agregados persistidos.
- Caso kill switch: `HOTEL_FEATURE_ENABLED=false`, run bloqueado y cero llamadas del adapter.
- No se activan `makcorps`, geocoder externo, credenciales, red ni tráfico comercial.

## Diseño

Un runner Python (`backend/scripts/hotel_mock_canary.py`) recibirá una ruta SQLite temporal nueva, restringida al workspace temporal, y la preparará ejecutando Alembic hasta `0055_hotel_alert_baseline_metadata`, el head actual que incluye las columnas H26 que consulta el sweep. Antes del caso nominal comprobará el perfil, provider y flags efectivos. Ejecutará `run_hotel_sweep(provider="mock")` con un adapter contador y consultará únicamente contadores agregados: estado del run, cantidad de muestras/agregados, operaciones/outcomes allowlisted, resolución del adapter y llamadas I/O del Mock. No emitirá IDs internos, nombres de hoteles, payloads ni excepciones raw.

El caso de kill switch usará una segunda sesión/DB aislada, mantendrá el provider Mock envuelto con un contador y fijará `HOTEL_FEATURE_ENABLED=false`. El runner invocará la misma frontera común y verificará que el run termina bloqueado antes de resolver/ejecutar I/O. La evidencia distinguirá `provider_resolver_calls` y `provider_io_calls` de las llamadas externas (`external_calls_expected=0`, `external_calls_observed=0`); los I/O nominales son lecturas locales del fixture Mock, no tráfico de red. También registrará el motivo allowlisted y comprobará ausencia de mutaciones de provider.

## Contrato de evidencia

El reporte contendrá solo:

- `schema_version`, `generated_at`, `runner`, `profile`, `provider_mode`, `migration_revision`;
- estado `passed|partial|blocked|failed` por escenario;
- `external_calls_expected/observed`;
- counts de runs, snapshots, latency aggregates y outcomes allowlisted;
- `known_limitations` indicando que es fixture/mock y no evidencia field/live.

El runner fallará closed si falta una DB aislada, el perfil no es canónico, el provider no es `mock`, aparece una llamada inesperada o el reporte contiene claves prohibidas (`user_id`, `hotel_id`, `provider_run_id`, `api_key`, `token`, `payload`, `secret`).

## Tests

- Test unitario del runner nominal con fixture mock.
- Test del kill switch con adapter instrumentado y cero llamadas.
- Test de redaction/forbidden keys del reporte.
- Test de flags incoherentes/proveedor no mock bloqueado.
- Gate de migración/DB aislada y suite hotelera focalizada.

## Fuera de alcance

- Makcorps o cualquier provider live.
- Credenciales, URLs externas, canary comercial, cohortes reales o tráfico dividido.
- Dashboard RED productivo, SLO, p95/p99 de campo o coste comercial.
- Commit, deploy, alteración de producción o reset de una DB no temporal.
