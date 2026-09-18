# ESTADO ACTUAL (POST-HARDENING)

**Fecha de recuento:** 18 Septiembre 2026
**Ubicación:** `docs/post-cutover/CURRENT_STATE.md`
**Recuento:** verificación directa con grep/tests sobre el working tree.

## 1. Estado de Git (Recuento)
- Los artefactos de la era de migración (reportes raíz, notepad temporal, scripts ledger) se han
  archivado o eliminado. Ver `docs/archive/migration-era/` para el histórico.
- No quedan bases de datos SQLite temporales en `backend/` (solo `viru.db` del launcher local,
  ignorado por git, y `viru_local.db` con seeds de demo).

## 2. Inventario de Código (Recuento de referencias)

### 2.1. Frontend (`frontend/src`)
- **Auth storage mechanisms** (`localStorage`, `sessionStorage`): solo usos legítimos
  (preferencias de UI, temas, FTUE por usuario, borradores de búsqueda). **0 referencias** a
  `viru_token` / `sb_access_token` como autoridad de sesión.
- **Consumidores del cliente API legacy** (`apiFetch`, `apiFetchWithStatus`, `@/modules/shared/api`):
  **0 referencias** (solo comentarios históricos).
- **Autoridad de sesión**: 1 (Supabase SSR via `@supabase/supabase-js` + middleware
  `updateSession` en `frontend/middleware.ts`).

### 2.2. Backend
- **Menciones SQLite/Alembic en código de runtime (`backend/app`)**: solo `sqlite_where`
  (índices parciales condicionales, válidos también en Postgres) y tests.
- **Scripts**: eliminados los scripts de auditoría pre-Orval y los scripts ledger muertos
  (`update_ledger.js`, `test_patch.py`).

### 2.3. Tests E2E
- Todos los specs Playwright usan `tests/helpers/e2e-session.ts` (siembra de sesión Supabase
  SSR) en lugar del `viru_token` retirado.

## 3. Estado de los Gates Rápidos
- **Frontend Typecheck (`tsc --noEmit`):** PASS
- **Frontend Lint (`eslint . --max-warnings 0`):** PASS
- **Frontend Tests (`npm test`):** 609 tests, 592 passed, 17 skipped (pre-existentes), 0 failed
- **Backend Tests (`pytest`):** 1414 passed, 3 skipped, 0 failed

## 4. Conclusión y Siguientes Pasos
Los gates están verdes y la deuda de la era de migración está archivada. Pendientes de producto:
1. Validar el esquema/RLS contra un proyecto Supabase remoto real (staging).
2. Decidir el destino de la cuenta demo (`dashboard-demo-session.ts`, actualmente inerte).
