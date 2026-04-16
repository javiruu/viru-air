Status: reference
Scope: historical consolidated change log
Last reviewed: 2026-04-15
Canonical source: docs/changelog/2026-03-08-c1-c6-consolidated.md
Related: docs/INDICE_UNICO.md

---
# Changelog consolidado C1–C6

Date: 2026-03-08

## C1 — Session hardening + route bridge cleanup
- Frontend: manejo unificado de 401/sesión y `returnUrl` saneado.
- Frontend: rutas puente centralizadas para legacy paths.
- Backend: errores auth estandarizados a `invalid_auth`.
- Commit referencia: `b355e80`.

## C2/C2.1 — Quick-search refactor (sin cambio funcional)
- Modularización de quick-search (`api/` + `state/` + i18n).
- Ajustes de copy y reset i18n.
- Evidencia QA + screenshots C2.1.
- Commits referencia: `0554b4d`, `6315938`, `e811024`.

## C3 — Navegación canónica y rutas
- Unificación de rutas y mapeo canónico.
- Commit referencia: `7755acc`.

## C4 — Robustez backend operativa
- Contrato de errores uniforme (`status/code/message/details`).
- Idempotencia en endpoints críticos.
- Correlation ID normalizado.
- Commit referencia: `0434e57`.

## C5 — DB baseline operativa
- Baseline PostgreSQL + migraciones + índices + backup/restore.
- Runbooks operativos y riesgos explícitos.
- Commit referencia: `7bda9d1`.

## C6 — Consolidación final y readiness
- QA integral consolidado (flows críticos + smoke de errores operativos).
- Alineación de living docs (arquitectura/rutas/error/DB/runbooks).
- Checklist de salida y acta de readiness.
- Bugs hallados/fijados en C6:
  1. Deprecación de status HTTP 422 en `backend/app/main.py` (`HTTP_422_UNPROCESSABLE_ENTITY` -> `HTTP_422_UNPROCESSABLE_CONTENT`).
  2. Flake en test de watchlist refresh por dependencia externa real (Ryanair 500): se fijó test con provider fake determinístico (`test_watchlist_flow.py`).





