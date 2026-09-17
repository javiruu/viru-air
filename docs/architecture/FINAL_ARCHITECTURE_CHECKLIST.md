# Checklist de Arquitectura de Viru Tracker (Auditoría Post-Migración)

Estado verificado y reconciliado con evidencia de código y runtime (reconciliación final: 2026-09-16).

- [x] **Los journeys críticos están cubiertos por Playwright:** Landing, responsive mobile, quick-search (con modales) y watchlist con autenticación en `frontend/tests/e2e/` (6 tests en 3 specs pasados).
- [x] **Lint, format y typecheck automatizados:**
  - Typecheck: `tsc --noEmit` pasa con 0 errores en todo el proyecto.
  - Linter rector: ESLint (`next/core-web-vitals`) activo, `--max-warnings 0` en verde.
  - Biome (`frontend/biome.json`): formatter activado y formateo global aplicado sobre los 473 archivos en alcance. `biome check` reporta 0 errores (75 avisos de nivel `warn`, no bloqueantes). `src/api/generated` permanece excluido.
- [x] **Contrato OpenAPI determinista y exportable:**
  - Exportador reproducible en `backend/scripts/export_openapi.py` (121 paths únicos, 151 operaciones).
  - `frontend/src/api/generated/` generado mediante Orval (`npm run api:check` pasa sin diff).
  - *Nota de adopción:* El frontend mantiene sus clientes HTTP nativos (`src/modules/shared/api.ts`); la adopción directa de los clientes generados en pantallas permanece como scaffold desacoplado para evitar roturas de UI.
- [x] **React QueryProvider configurado en RootLayout:**
  - `QueryProvider` activo en `frontend/src/app/layout.tsx` con políticas de cache (`staleTime: 30s`).
  - *Nota de adopción:* Server state en páginas históricas utiliza 243 `useEffect` probados y estables. La migración a `useQuery` será por pantalla a demanda.
- [x] **Datos no confiables validados con Zod en boundaries dedicados:**
  - Variables de entorno validadas con `src/lib/env.ts`.
  - Payloads de sesión y almacenamiento local tipados con `src/modules/shared/auth-schema.ts`.
- [x] **Autoridad Única de Base de Datos clarificada:**
  - **Supabase migrations es la única autoridad DDL** (`supabase/migrations/20260912000001_canonical_baseline_schema.sql`, 62 tablas canónicas + `20260912000002_enable_user_rls_policies.sql`, 30 políticas RLS con `auth.uid()`).
  - Alembic está retirado: carpeta `backend/alembic/` eliminada, dependencia ausente de `pyproject.toml` y `uv.lock`, y sin referencias en runtime. Lo garantiza `test_schema_migration_authority.py`.
  - Runtime de base de datos: PostgreSQL (psycopg v3) apuntando a Supabase; `DB_URL` obligatoria con `sslmode=require` para hosts remotos.
- [x] **Primitivas UI estandarizadas en `src/components/ui/`:**
  - Primitivas `Button`, `Badge`, `Card` disponibles para nuevos desarrollos conforme a `AGENTS.md`, sin imponer rediseño forzado sobre componentes existentes.
- [x] **Gobernanza de Privacidad y Analytics:**
  - Wrapper seguro en `frontend/src/lib/posthog.ts` con `autocapture: false` y enmascaramiento total de inputs. No conectado en runtime dev/test por defecto.
- [x] **Módulo de Telemetría (Observabilidad Local):**
  - Módulo `backend/app/core/telemetry.py` con filtrado de atributos sensibles (`password`, `token`, `authorization`). Clasificado como `LOCAL_ONLY_SCAFFOLD` sin exporter de red configurado.

