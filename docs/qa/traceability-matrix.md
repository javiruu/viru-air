# QA Traceability Matrix

| Requisito | Endpoint/Ruta | Test inicial |
|---|---|---|
| F-USER-001/002 | POST /api/v1/auth/register, /login | backend/tests/unit/test_health.py (base) |
| F-TRACK-001 | POST /api/v1/watchlist/{id}/refresh-now | pendiente integration |
| F-ALERT-001/003 | POST /api/v1/alerts/rules | pendiente unit rules |
| F-SEARCH-FAST-001 | POST /api/v1/search/quick | pendiente contract |
| F-PREF-001 | PUT /api/v1/preferences | pendiente integration |

Notas:
- Se deja preparada la estructura para ampliar suites P0/P1 según Fase 8.
