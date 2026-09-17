# Post-Migration Baseline

**Fecha:** 2026-09-12  
**Commit auditado (HEAD):** 91e6717d9bbd43d4ba148c6a114426266fabb823  
**Rama:** main  

## 1. Versiones de Runtimes y Gestores de Paquetes
- **Node.js:** v24.13.1
- **npm:** 11.8.0
- **Python:** 3.14.3 (Python virtualenv en ackend/.venv)
- **Git status inicial:** 6 archivos modificados, 23 archivos/carpetas no trackeados (incluye iru-post-migration-audit/, scaffolds de modernización previa).

## 2. Scripts Disponibles
- **Frontend (rontend/package.json):**
  - 
pm test (	sx --test)
  - 
pm run test:e2e (playwright test)
  - 
pm run test:e2e:quick-search
  - 
pm run qa:visual:quick-search
  - 
pm run lint (slint . --max-warnings 0)
  - 
pm run lint:biome (iome lint)
  - 
pm run format:biome (iome format)
  - 
pm run check:biome (iome check)
  - 
pm run typecheck (	sc --noEmit)
  - 
pm run api:generate (orval)
  - 
pm run api:check (orval && git diff --exit-code src/api/generated)
  - 
pm run build (
ext build)
- **Backend (ackend):**
  - pytest con venv de Python 3.14.3 (.venv\Scripts\pytest)
  - alembic (.venv\Scripts\alembic)
  - scripts: xport_openapi.py, etc.

## 3. Número Real de Tests Descubiertos
- **Backend pytest:** 1.441 tests descubiertos en 0.93s (pytest --collect-only).
- **Frontend unit/integration:** 138 archivos de test en rontend/tests/.
- **Frontend E2E (Playwright):** 5 archivos en rontend/tests/e2e/ (más tests e2e específicos en tests/).
- **Supabase test db:** 0 tests existentes en supabase/tests/ (no existe suite de test db preconfigurada).

## 4. Rutas / Endpoints Reales
- **FastAPI pp.routes:** 155 rutas totales registradas.
  - 4 rutas internas excluidas de schema: /openapi.json, /docs, /docs/oauth2-redirect, /redoc.
  - 151 rutas de aplicación correspondientes a operaciones de endpoints.
- **OpenAPI spec['paths']:** 121 rutas (paths únicos).
- **OpenAPI total operaciones HTTP:** 151 operaciones (GET, POST, PUT, DELETE, PATCH).
- **Diferencia 155 vs 121:** Reconciliada exactamente. 155 rutas en runtime = 121 paths únicos + 30 métodos múltiples en la misma ruta + 4 rutas internas de Swagger/ReDoc.

## 5. Migraciones Existentes
- **Alembic:** 65 versiones de migración en ackend/alembic/versions/ (0001_initial hasta 0062_prune_legacy_expiry_indexes y revisiones auxiliares).
- **Supabase:** 1 migración en supabase/migrations/20260912000001_create_flight_watch.sql.

## 6. Vulnerabilidades y Fallos Preexistentes (Diagnóstico Inicial)
- RLS en Supabase no tiene tests automatizados (supabase/tests/ vacío).
- Doble migrator potencial: Alembic gestiona todo el schema public en Postgres; Supabase tiene una migración SQL aislada para light_watch.
- Coexistencia Biome / ESLint sin delimitación clara de alcance (Biome fue corrido solo sobre 16 archivos en la modernización anterior).
- Dependencias y wrappers (shadcn, telemetry, posthog) pendientes de verificación de call sites reales frente a placebo.

