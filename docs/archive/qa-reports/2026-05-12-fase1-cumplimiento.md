**Estado:** vivo  
**Última revisión:** 2026-05-12  
**Fuente de verdad:** sí  
**Área:** qa

## Resumen

Checklist de cumplimiento estricto de `fase1.md` con evidencia verificable por test/archivo.

## Cumplimiento por paquete

1. Auth core: cumplido.
: Evidencia: `backend/tests/integration/test_auth_flow.py` (`register/login/me`), `19 passed` en suite núcleo.
2. Catálogo de aeropuertos: cumplido.
: Evidencia: `backend/tests/unit/test_airports_seed_catalog.py`, `backend/tests/unit/test_airports_endpoints.py`.
3. Builder frontend quick search: cumplido.
: Evidencia: `frontend/tests/quick-search-refactor-utils.test.ts` cubre `prepareQuickSearchRequest`, `buildQuickSearchCanonicalPayload`, `buildQuickSearchExpectedSignatures`.
4. `POST /api/v1/search/quick`: cumplido.
: Evidencia: `backend/tests/integration/test_quick_search_returns_results.py` (AGP->DUB), `backend/tests/integration/test_search_alerts_flow.py` (MAD->DUB), `backend/tests/unit/test_quick_search_error_observability.py` (envelope trazable).
5. Watchlist CRUD: cumplido.
: Evidencia: `backend/tests/integration/test_watchlist_flow.py`; 409 `watch_already_exists`; validación `origin_equals_destination`.
6. Refresh + history batch: cumplido.
: Evidencia: `backend/tests/integration/test_watchlist_refresh_cooldown.py` (200/429/200 + `Retry-After`), `backend/tests/integration/test_prices_batch_history.py`.
7. Alertas básicas: cumplido.
: Evidencia: `backend/tests/unit/test_alert_rule_aliases.py`, `backend/tests/integration/test_search_alerts_flow.py`, `backend/tests/integration/test_time_ordering_regression.py`.
8. Preferencias mínimas: cumplido.
: Evidencia: `backend/tests/integration/test_preferences_flow.py`.

## Constraints de Fase 1

1. Sin expansión a flags posteriores (`prediction`, `self_connect`, `everywhere`, `country_content`, `full_i18n`, `suggestions_pipeline`): cumplido.
2. Consolidación + endurecimiento contractual + cierre QA: cumplido.

## Nota obligatoria de riesgo residual

Se mantiene riesgo acotado de escenarios degradados con `HTTP 200` y `results: []` en quick search; queda registrado en `docs/specs/phase1-codex.md` y en el enfoque de pruebas de degradación.
