# PR Final Notes — Watchlist hardening (Cycle 4)

## Resumen
Este PR cierra hardening de `/watchlist` en 4 frentes:
1. Batch history para eliminar patrón N+1 (`POST /api/v1/prices/history/batch`).
2. Guardrails de payload (`max_rows`, `captured_since_utc`) + benchmark formal N+1 vs batch.
3. Cooldown operativo de refresh (`WATCH_REFRESH_COOLDOWN_SECONDS`, `429`, `Retry-After`, logs).
4. Integridad de datos por unicidad de watchlist con migración segura y fallback API `409 watch_already_exists`.

## Impacto esperado
- Menor latencia y carga DB en watchlist con múltiples vuelos.
- Menor riesgo de ráfagas hacia proveedor y snapshots redundantes.
- Integridad de datos reforzada (sin duplicados semánticos por ruta+fecha+usuario).

## Riesgos abiertos
- UX aún puede mejorar copy de cooldown (mensaje más humano en frontend).
- Aún no hay cola asíncrona de refresh; hoy sigue síncrono con guardrail.
- Caché Redis para histórico/comparativas sigue fuera de este PR.

## Rollback
- API/backend: revertir commits del PR si fuera necesario.
- DB unicidad:
  - downgrade a `0007_pg_ops_idx` elimina el índice único.
  - **Nota:** no recrea duplicados consolidados (esperado).

## Checklist de despliegue
1. Backup DB.
2. Pre-check duplicados:
   ```bash
   backend/.venv/bin/python backend/scripts/check_watchlist_duplicates.py
   ```
3. Ejecutar migraciones:
   ```bash
   cd backend
   DB_URL=<db_url> .venv/bin/alembic upgrade head
   ```
4. Reiniciar backend/frontend.
5. Smoke release:
   ```bash
   backend/.venv/bin/python backend/scripts/smoke_watchlist_release.py
   ```
6. Verificar logs 429 cooldown (`event=watch_refresh_denied_cooldown`).

## Deuda técnica registrada (fuera de PR)
- Async refresh queue (Redis + worker).
- Cache de histórico/comparativas.
- Microcopy frontend para cooldown con tiempo restante.
- SLO/latency dashboards por endpoint watchlist/prices.
