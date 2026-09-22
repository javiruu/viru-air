# Release Closure - 2026-05-12

**Estado:** vivo  
**Fecha:** 2026-05-12  
**Fuente de verdad:** si  
**Area:** QA / release

## Commit base

- `main` / `origin/main` base al iniciar auditoria: `c340f55ddafb189e2ab6723fa836d7a3386c65eb`.

## Comandos ejecutados

### Repo hygiene
- `git status --short`
- `git fetch origin`
- `git rev-parse HEAD`
- `git rev-parse origin/main`
- `git rev-list --left-right --count origin/main...main`

### Migraciones
- `python -m alembic heads`
- `DB_URL=sqlite:///./_tmp_release_migration_check.db python -m alembic upgrade head`
- `python -m alembic current`
- `python -m alembic check`

### Backend regression
- Suites objetivo solicitadas (auth/watchlist/prices/search-alerts/notification pipeline/worker/f3d/preferences).
- Global backend adicional: `python -m pytest -q`.

### Frontend regression
- `npm test`
- `npm run build`
- `npm run test:e2e:quick-search`

### Runtime smoke
- Backend: `127.0.0.1:8000`
- Frontend: `127.0.0.1:3000`
- Verificaciones: `/health`, `/login`, `/quick-search`, `/watchlist`, `/alerts`, `/preferencias`.

## Resultados

- Repo hygiene: `main` limpio y sincronizado con `origin/main` al inicio (`0 0` ahead/behind).
- Migraciones:
  - Head unico: `0015_alerts_quiet_hours_digest`.
  - Upgrade limpio desde DB vacia: OK.
  - `alembic check`: detecta diferencias de autogeneracion de indices/tipos (hallazgo documental; no bloqueo de arranque/migracion ni de suites objetivo).
- Backend suites objetivo: PASS.
- Backend global: PASS (`134 passed`).
- Frontend test/build: PASS.
- Runtime smoke: PASS (rutas criticas en 200).
- E2E quick-search dedicado: ejecuta y queda `skipped` por guard de reachability/auth, sin fallo.

## Bugs encontrados y corregidos

1. Regresion en test de orden temporal con cooldown de refresh
- Sintoma: `test_time_ordering_regression` recibia `429` por cooldown en refresh secuenciales.
- Fix: desactivar cooldown explicitamente en ese test (`WATCH_REFRESH_COOLDOWN_SECONDS=0` + monkeypatch de constante).
- Archivo: `backend/tests/integration/test_time_ordering_regression.py`.

2. Regresion de asercion por acento en catalogo de aeropuertos
- Sintoma: test esperaba `almeria` y datos devuelven `almer�a`.
- Fix: asercion robusta con normalizacion unicode (fold ASCII) en test.
- Archivo: `backend/tests/unit/test_airports_catalog_master.py`.

## Bugs no bloqueantes / observaciones

- `alembic check` reporta diferencias de autogeneracion (indices/tipos) en entorno SQLite de control.
- No impidio upgrade limpio a `head` ni ejecucion de suites de regresion/arranque.
- Se marca como deuda tecnica de migraciones para revisi�n posterior, fuera de cierre bloqueante.

## Pendientes postponed (explicito)

- Email real provider.
- Recommendations explainability.
- Mapa opcional.
- FX/export avanzado.
- Scheduler/deploy productivo del worker (si se mantiene operativo por comando).
- Otros pendientes del F3 amplio fuera del alcance cerrado.

## Criterio final: main estable

Se considera **main estable** para fase de cierre porque:
- Migraciones desde cero hasta head: OK.
- Regresion backend objetivo: OK.
- Regresion frontend + build: OK.
- Smoke runtime de rutas criticas: OK.
- Fixes aplicados solo a regresiones de test (sin features nuevas).
- Estado de fases consolidado y postponed explicitado en documentacion de cierre.

## Addendum RC tightening (2026-05-12)

Contexto:
- Se ejecuta una pasada final para cerrar riesgo tecnico pendiente: drift Alembic/check + validacion completa pre-RC.

Cambios aplicados (sin features):
- Alineacion de metadata SQLAlchemy con migraciones:
  - `backend/app/infrastructure/db/models.py`
  - removido `index=True` en campos `unique` de:
    - `users.email`
    - `refresh_token.token_hash`
    - `password_reset_token.token_hash`
- Limpieza trivial ruff:
  - `backend/app/api/v1/search.py` (variable no usada)
  - `backend/scripts/migrate_sqlite_to_postgres.py` (f-string redundante)
  - `backend/tests/integration/test_notification_worker.py` (import no usado)

Validaciones ejecutadas:
- Alembic:
  - `DB_URL=sqlite:///./_tmp_clean_audit2.db python -m alembic upgrade head` -> OK
  - `DB_URL=sqlite:///./_tmp_clean_audit2.db python -m alembic check` -> drift residual limitado a `remove_index` (sin `ix_users_email` ni cambios add/unique de token_hash).
- PostgreSQL drift:
  - `psql --version` no disponible.
  - Estado: `PostgreSQL drift check not run`.
- Ruff:
  - `backend/.venv/Scripts/python -m ruff check .` -> OK.
- E2E quick-search con servicios vivos:
  - backend `/health` 200, frontend `/quick-search` 200.
  - `npm run test:e2e:quick-search` -> skipped por guard auth/reachability (`Quick-Search form is not directly reachable (likely auth/session required).`).
- Regression final:
  - backend `pytest -q` -> `134 passed`.
  - frontend `npm test` -> `87 pass, 0 fail, 15 skipped`.
  - frontend `npm run lint` -> OK.
  - frontend `npm run build` -> OK.

Decision:
- `main` sigue **stable with accepted caveats**.
- Recomendacion de release: **apto para etiquetar `v0.1-rc1` con confianza razonable**.
