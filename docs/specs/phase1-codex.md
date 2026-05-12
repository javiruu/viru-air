Status: canonical
Scope: phase-1 MVP closure
Last reviewed: 2026-05-12
Canonical source: docs/specs/phase1-codex.md
Related: fase1.md, docs/reference/backend/quick-search-contract.md, docs/qa/traceability-matrix.md

---
# Phase 1 Codex MVP

## Objetivo

Congelar la ejecución de Fase 1 como cierre de MVP operativo y verificable, evitando deriva entre contrato, implementación y pruebas.

## Alcance incluido (P0/P1)

1. Auth core (`register`, `login`, `me`).
2. Catálogo de aeropuertos (`seeds`, `compatible`, `nearby`).
3. Builder frontend de quick search.
4. `POST /api/v1/search/quick` (contrato canónico + observabilidad).
5. Watchlist CRUD.
6. Refresh manual + `prices/history/batch`.
7. Alertas básicas (reglas, evaluate, events).
8. Preferencias mínimas (`/preferences` y aliases).

## Alcance excluido en Fase 1

- `ff_prediction_enabled`
- `ff_self_connect_enabled`
- `ff_everywhere_enabled`
- `ff_country_content`
- `ff_full_i18n`
- `ff_suggestions_pipeline`

## Definition of Done (Fase 1)

1. Contrato FE/BE de quick search alineado con `docs/reference/backend/quick-search-contract.md`.
2. Watchlist + refresh + history con ownership, cooldown e idempotencia verificables.
3. Alertas por umbral y cambio funcionando con eventos trazables.
4. Preferencias persistidas y reutilizables como defaults operativos.
5. Pruebas núcleo en verde para auth, quick search, watchlist, prices batch, alertas y preferencias.

## Checklist de verificación mínima

1. `backend/tests/integration/test_auth_flow.py`
2. `backend/tests/integration/test_quick_search_returns_results.py`
3. `backend/tests/integration/test_watchlist_flow.py`
4. `backend/tests/integration/test_watchlist_refresh_cooldown.py`
5. `backend/tests/integration/test_prices_batch_history.py`
6. `backend/tests/integration/test_search_alerts_flow.py`
7. `backend/tests/integration/test_preferences_flow.py`

## Riesgos aceptados en cierre Fase 1

1. Pueden persistir casos acotados de `HTTP 200` con `results: []` en quick search bajo degradación de proveedor.
2. `include_stops`, `max_stops`, `duration_max_min` y `risk_allowed` no tienen enforcement completo en todas las rutas.
3. Persisten aliases legacy temporales en quick search hasta completar sunset controlado.

## Política de no-regresión

1. No introducir campos canónicos nuevos en `search/quick` sin actualizar contrato backend + tests.
2. No cambiar semántica de cooldown/idempotencia de watchlist sin actualizar runbook y pruebas.
3. Cualquier cambio de nomenclatura/alias en search requiere seguir la política de sunset legacy.
