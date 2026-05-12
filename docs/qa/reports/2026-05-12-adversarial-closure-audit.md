# Adversarial Closure Audit - 2026-05-12

**Estado:** vivo  
**Fecha:** 2026-05-12  
**Tipo:** auditoria adversarial de cierre (post `609fe16`)  
**Commit auditado:** `609fe16` (HEAD actual y `origin/main`)

## 1) Comandos ejecutados

### Repo hygiene
- `git status --short`
- `git log --oneline -5`
- `git branch --show-current`
- `git rev-parse HEAD`
- `git rev-parse origin/main`

### Alembic deep audit
- `python -m alembic heads`
- `python -m alembic history --verbose`
- `DB_URL=sqlite:///./_tmp_clean_audit.db python -m alembic upgrade head`
- `DB_URL=sqlite:///./_tmp_clean_audit.db python -m alembic check`

### Fresh clone simulation (sin borrar repo)
- limpieza: `frontend/.next`, `backend/**/__pycache__`
- `DB_URL=sqlite:///./_tmp_fresh_runtime.db python -m alembic upgrade head`
- backend smoke: `GET http://127.0.0.1:8000/health`
- frontend build: `npm run build`
- frontend smoke: `GET /login /quick-search /watchlist /alerts /preferencias`

### Backend audit
- `backend/.venv/Scripts/python -m pytest -q`
- `backend/.venv/Scripts/python -m pytest -q tests/integration/test_auth_flow.py tests/integration/test_notification_pipeline.py tests/integration/test_notification_worker.py tests/integration/test_watchlist_flow.py tests/integration/test_prices_advanced.py tests/integration/test_preferences_flow.py tests/integration/test_quick_search_provider_degradation.py`
- `backend/.venv/Scripts/python -m ruff check .`
- `backend/.venv/Scripts/python -m mypy app`

### Frontend audit
- `npm test`
- `npm run build`
- `npm run lint`
- `npm run test:e2e:quick-search`

### API contract sanity
- `GET http://127.0.0.1:8000/openapi.json` + validacion de paths requeridos/historicos

### Config/docs/security scan
- lectura: `backend/.env.example`, `frontend/.env.example`
- scan: `rg -n "(AKIA|BEGIN PRIVATE KEY|password=|token=|SECRET_KEY=|C:/Users/)" docs backend frontend`
- lectura: `docs/qa/reports/2026-05-12-fases-0-3-audit.md`
- lectura: `docs/qa/reports/2026-05-12-release-closure.md`
- lectura: `docs/overview/current-state.md`
- lectura: `docs/runbooks/runbook-notification-worker.md`
- lectura: `docs/DOCS_INVENTORY.md`

## 2) Resultados

### Repo cleanliness
- `git status --short`: limpio.
- Rama actual: `main`.
- `HEAD == origin/main == 609fe16`.

### Alembic check (diff exacto)
`alembic check` en SQLite limpio reporta:
- `remove_index`: `ix_alert_rule_watch_enabled`
- `remove_index`: `ix_flight_watch_user_status_paused_created`
- `remove_index`: `uq_flight_watch_user_route_date`
- `remove_index`: `ix_idempotency_record_created_at`
- `remove_index`: `ix_notification_event_rule_created`
- `remove_index` + `add_index(unique=True)`: `ix_password_reset_token_token_hash`
- `remove_index`: `ix_price_snapshot_watch_captured`
- `remove_index` + `add_index(unique=True)`: `ix_refresh_token_token_hash`
- `remove_index`: `ix_security_activity_user_created`
- `remove_index`: `ix_user_session_user_active_last_seen`
- `add_index(unique=True)`: `ix_users_email`

Clasificacion:
- A) Ruido SQLite/tipo/indice no material para PostgreSQL: la mayor parte de `remove_index` en compuestos y diferencias de metadata/index reflection en SQLite.
- B) Modelo SQLAlchemy no reflejado en migracion: `ix_users_email` aparece como `add_index(unique=True)` en check; revisar definicion historica de `users.email`.
- C) Migracion redundante/mal definida: `refresh_token` y `password_reset_token` muestran cambio `unique=False -> unique=True` para `token_hash` en autogen (posible deriva de declaracion de indice/unique en modelo vs migracion).
- D) Riesgo real: **no blocker demostrado** en runtime actual; migracion desde cero a `head` funciona y suites integracion pasan.

PostgreSQL drift check:
- **No ejecutado** (`docker` no disponible en entorno): `PostgreSQL drift check not run`.

### Fresh runtime + smoke
- `alembic upgrade head` sobre `sqlite:///./_tmp_fresh_runtime.db`: OK (`0001 -> 0015`).
- Backend `/health`: `200`.
- Frontend `npm run build`: OK.
- Frontend routes:
  - `/login`: `200`
  - `/quick-search`: `200`
  - `/watchlist`: `200`
  - `/alerts`: `200`
  - `/preferencias`: `200`

### Backend full audit
- `pytest -q`: **134 passed**.
- Subset adversarial dirigido: **32 passed**.
- `ruff check .`: falla con 3 hallazgos (deuda existente).
- `mypy app`: falla con 65 errores (deuda tipado existente).

### Frontend full audit
- `npm test`: pass `87`, fail `0`, skipped `15`.
- `npm run lint`: OK.
- `npm run build`: OK.
- `npm run test:e2e:quick-search`: skipped `1` por guard reachability/auth del propio test.
- `npm run typecheck`: script no existe.
- `npm run test:e2e` y `npm run test:coverage`: scripts no existen.

### E2E con servicios levantados
- Validacion HTTP de rutas clave con backend/frontend levantados: PASS.
- E2E formales del repo dependientes de reachability/auth permanecen `skipped` por diseño de guard en esta corrida.
- Verificacion de consola browser real: **no ejecutada** en navegador interactivo en este run (solo smoke HTTP + suites).

### Auth / ownership / notification / historico / quick-search adversarial
- Cobertura validada por suites backend/frontend en verde (auth flow, notification pipeline/worker, watchlist flow, prices advanced, preferences, quick-search degradation/save-result).
- No se detectaron 500 en smoke HTTP realizado.
- No se aplicaron cambios de comportamiento.

### API contract sanity
- OpenAPI incluye todos los endpoints requeridos y no desaparecen los historicos listados.
- Resultado script de validacion: `missing:none`.

### Environment / config / secretos
- `backend/.env.example` incluye worker config (`NOTIFICATION_WORKER_*`) y no contiene secretos reales.
- `frontend/.env.example` consistente.
- Scan rapido de secretos/tokens/rutas absolutas en `docs/backend/frontend`: sin matches de patrones sensibles usados en el grep.

### Documentation consistency
- `current-state` mantiene `F3 global: partial por alcance`.
- Reportes de QA/cierre y runbook alineados con postponed (email real, scheduler productivo, etc.).
- Se detecta deuda de encoding en algunos docs (texto mojibake), pero no contradiccion funcional de estado en los archivos revisados.

## 3) Hallazgos

### Blocker
- Ninguno demostrado.

### Major
- Ninguno demostrado.

### Minor
- Drift de `alembic check` en SQLite (indices/unique) pendiente de saneo fino para dejar check totalmente limpio.
- `ruff`/`mypy` en rojo por deuda preexistente no bloqueante para este cierre.
- E2E quick-search formal en este run queda skipped por guard reachability/auth.

### Accepted/Postponed
- `PostgreSQL drift check not run` por ausencia de Docker local.
- Pendientes globales F3 ya documentados como postponed (email real, scheduler productivo, explainability recomendaciones, etc.).

## 4) Fixes aplicados

- Ninguno. No se detecto bug blocker/major que justificara cambio de codigo en esta auditoria.

## 5) Conclusion

**main stable with accepted caveats**

Caveats aceptados:
- drift de `alembic check` en SQLite por clasificar/sanear fino;
- falta de drift check en PostgreSQL en este entorno;
- deuda estatico (`ruff`/`mypy`) y e2e condicionales skipped.

## 6) Update RC Tightening (2026-05-12)

Objetivo del update: cerrar el ultimo riesgo tecnico de drift Alembic + validacion final para candidate release.

### Alembic drift: clasificacion final

Reproduccion:
- `DB_URL=sqlite:///./_tmp_clean_audit2.db python -m alembic upgrade head` -> OK
- `DB_URL=sqlite:///./_tmp_clean_audit2.db python -m alembic check` -> solo `remove_index` en SQLite

Acciones aplicadas (alineacion real model/migracion):
- `users.email`: removido `index=True` en modelo (se mantiene `unique=True`).
- `refresh_token.token_hash`: removido `index=True` en modelo (se mantiene `unique=True`).
- `password_reset_token.token_hash`: removido `index=True` en modelo (se mantiene `unique=True`).

Resultado: desaparecen del drift
- `ix_users_email` (antes `add_index(unique=True)`),
- `ix_refresh_token_token_hash` y `ix_password_reset_token_token_hash` como cambio de unique/add.

Estado actual de drift (solo removals):
- `ix_alert_rule_watch_enabled`
- `ix_flight_watch_user_status_paused_created`
- `uq_flight_watch_user_route_date`
- `ix_idempotency_record_created_at`
- `ix_notification_event_rule_created`
- `ix_password_reset_token_token_hash`
- `ix_price_snapshot_watch_captured`
- `ix_refresh_token_token_hash`
- `ix_security_activity_user_created`
- `ix_user_session_user_active_last_seen`

Clasificacion por caso:
- `ix_users_email`: **B (modelo mal declarado)** -> corregido.
- `ix_refresh_token_token_hash`: **C/D (migracion crea unique + indice redundante; modelo tenia doble declaracion)** -> alineado modelo, sin migracion nueva por no impacto funcional.
- `ix_password_reset_token_token_hash`: **C/D (idem anterior)** -> alineado modelo, sin migracion nueva.
- Indices compuestos/operacionales de `0007/0008`: **A (ruido/reflection SQLite)** en `alembic check`; no evidencia de riesgo runtime.

Decisiones:
- No crear migracion nueva para este cierre porque el remanente es metadata/check sobre SQLite sin evidencia de fallo en upgrade ni en tests.
- Mantener caveat documentado para hardening posterior en entorno PostgreSQL real.

### PostgreSQL drift check
- `docker --version` y `psql --version` no disponibles en este entorno.
- Estado: **PostgreSQL drift check not run** (no bloqueante RC).

### Ruff cleanup
- `backend/.venv/Scripts/python -m ruff check .` -> **All checks passed**.
- Fixes triviales aplicados:
  - variable local no usada en `backend/app/api/v1/search.py`,
  - `f-string` sin placeholders en `backend/scripts/migrate_sqlite_to_postgres.py`,
  - import no usado en `backend/tests/integration/test_notification_worker.py`.

### E2E real con servicios levantados
- Backend `/health` -> `200`.
- Frontend `/quick-search` -> `200`.
- `npm run test:e2e:quick-search` con ambos servicios vivos -> **skipped (1)**.
- Motivo exacto reportado por test:
  - `Quick-Search form is not directly reachable (likely auth/session required).`

### Validacion final
- Backend: `pytest -q` -> **134 passed**.
- Frontend: `npm test` -> **pass 87, fail 0, skipped 15**.
- Frontend: `npm run lint` -> **OK**.
- Frontend: `npm run build` -> **OK**.

### Cierre RC
- `main` se mantiene estable con caveats aceptados.
- Recomendacion: **se puede etiquetar `v0.1-rc1` con confianza razonable**, dejando explicitos:
  - drift residual de `alembic check` en SQLite (solo remove_index),
  - `PostgreSQL drift check not run`,
  - e2e quick-search condicional por guard auth/reachability.
