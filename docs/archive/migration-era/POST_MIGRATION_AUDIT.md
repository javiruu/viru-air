# Post-Migration Audit

**Commit audited (baseline del programa):** 91e6717d9bbd43d4ba148c6a114426266fabb823
**Fecha de auditoría original:** 2026-09-12 · **Reconciliación final y re-verificación completa:** 2026-09-16 · **Hardening de seguridad (code review):** 2026-09-16

## Verdict
**PASS — CUTOVER CERRADO Y VERIFICADO**

El cutover de modernización (Alembic/SQLite → Supabase PostgreSQL + RLS, Supabase Auth, Orval/TanStack Query, Zod, shadcn/ui, PostHog, OpenTelemetry, dependencias parcheadas) está ejecutado, verificado de extremo a extremo con suites reales y reconciliado documentalmente. La verificación del 2026-09-16 se ejecutó desde cero sobre el working tree final, no se heredan resultados previos.

## Verified claims (re-verificación 2026-09-16)
- **Backend pytest completo:** 1.413 passed, 3 skipped, 0 failed (unit: 1.110 + integration/db_remote: 303). Duración total ~7 min.
- **Frontend unit (`npm test`, tsx --test):** 620 tests — 603 passed, 17 skipped, 0 failed.
- **E2E Playwright:** 6/6 passed (landing/navegación, quick-search, watchlist).
- **Typecheck (`tsc --noEmit`):** 0 errores.
- **Contrato OpenAPI (`npm run api:check`):** regeneración Orval determinista, diff 0.
- **ESLint (`--max-warnings 0`):** limpio.
- **Biome (`biome check`):** 0 errores tras activar el formatter y aplicar formateo global (473 archivos en alcance, 348 reformateados; 75 avisos de nivel `warn` no bloqueantes; `src/api/generated` excluido).
- **Build de producción (`next build`):** exit 0.
- **`npm audit`:** found 0 vulnerabilities (maplibre-gl 6.9.0, next 15.5.25, sharp 0.35.4).
- **Autoridad de esquema:** `test_schema_migration_authority.py` valida que Supabase migrations es la autoridad canónica (baseline de 62 tablas) y que alembic no figura en `pyproject.toml`. `Base.metadata` = 62 tablas alineadas 1:1 con el baseline SQL.

## Problems found and fixed during final verification (2026-09-16)
1. **Regresión del cutover: modelo `RefreshToken` eliminado por error.** El conteo de tablas bajó a 61 y 4 tests fallaban (`no such table: quick_search_popularity_counter`, `Expected 62 application tables, found 61`). El baseline SQL canónico incluye `refresh_token`, el propio test del cutover exige 62 tablas y la ruta `/auth/refresh` está activa (aunque devuelva 410). Se restauró el modelo SQLAlchemy verbatim desde el historial.
2. **Tests de quick-search con `TestClient` a nivel de módulo** contra una app cuya DB por defecto dejó de auto-crear esquema (`schema_compat` ya no recorre metadatos en el arranque). Se convirtieron a funciones pytest con el fixture `client` del conftest (DB temporal con `create_all` completo).
3. **Helper de tests desconectado de la DB del cliente:** `register_and_token` insertaba usuarios en `SessionLocal` global (ahora DB en memoria) en vez de la DB temporal del override `get_db`. Corregido: resuelve la sesión del override del `TestClient` con fallback a `SessionLocal` para scripts. Este cambio arregló 17 fallos de integración (hoteles/notificaciones).
4. **Falsos positivos E2E + fixture desactualizado:** el fixture de Playwright inyectaba `viru_token`/`viru_refresh_token` pero la app del cutover lee `sb_access_token`/`sb_refresh_token`. Los specs que pasaban solo verificaban `main` visible (también presente en el login). Fixture actualizado y E2E 6/6 reales.
5. **Bug real en `clearStoredToken` (`src/modules/shared/api.ts`):** tras un 401 limpiaba `sb_access_token` pero dejaba el refresh en `viru_refresh_token` (clave anterior). Corregido a `sb_refresh_token`.
6. **2 errores de ESLint preexistentes** en `tests/e2e/fixtures/auth.fixture.ts` (`react-hooks/rules-of-hooks` — falso positivo con fixtures de Playwright). Resuelto con `eslint-disable` documentado a nivel de archivo.
7. **14 tests de conformidad de fuente rotos por el formateo global:** aserciones regex sobre código fuente que el formatter re-fluyó. Se adaptaron las regex para tolerar espacios/saltos sin debilitar la semántica verificada.

## Database authority
- **Autoridad DDL única:** Supabase migrations (`supabase/migrations/20260912000001_canonical_baseline_schema.sql` — 62 tablas; `20260912000002_enable_user_rls_policies.sql` — 30 políticas RLS con `auth.uid()`).
- **Runtime:** PostgreSQL via psycopg v3; `DB_URL` obligatoria (falla rápido sin ella), `sslmode=require` automático para hosts remotos. Sin `create_all` de negocio en arranque: el backend es consumidor del esquema, no autor.
- **Alembic:** retirado (directorio eliminado, dependencia fuera de `pyproject.toml` y `uv.lock` regenerado).

## Supabase status
**ACTIVO COMO AUTORIDAD DE ESQUEMA.** Migraciones canónicas versionadas + RLS. La validación con `supabase test db` local sigue bloqueada por ausencia de CLI de Supabase (ver `UNRESOLVED_RISKS.md`).

## Security
- Cero claves de servicio, tokens de base de datos o secretos expuestos en frontend (`NEXT_PUBLIC_*` limpio).
- `npm audit`: 0 vulnerabilidades. Runtime Python sin CVEs de aplicación.
- Pruebas negativas de autenticación y aislamiento cross-user incluidas en la suite (`test_supabase_auth_negative.py` y flujos de integración).

## Exact final gates (2026-09-16)
| Gate | Command | Result |
|---|---|---|
| **Backend pytest completo** | `.venv/Scripts/pytest tests/unit tests/integration tests/db_remote -q` | **1.425 passed, 3 skipped, 0 failed** (incluye 19 tests del hardening) |
| **Frontend unit** | `npm test` | **606 passed, 17 skipped, 0 failed (623 tests)** |
| **Frontend E2E** | `npx playwright test` | **6 passed (3 specs)** |
| **Typecheck** | `npm run typecheck` | **0 errores** |
| **OpenAPI drift** | `npm run api:check` | **0 diff** |
| **ESLint** | `npm run lint` | **0 errores/warnings** |
| **Biome** | `npx biome check .` | **0 errores (75 warn no bloqueantes)** |
| **Production build** | `npm run build` | **Success (exit 0)** |
| **npm audit** | `npm audit` | **0 vulnerabilities** |

## Security hardening (code review adversarial, 2026-09-16)

La revisión de código posterior a la verificación encontró una cadena de autenticación explotable en el cutover; quedó resuelta con regresión cubierta:

1. **C1 — Bypass con clave JWT vacía (crítico, corregido).** `SUPABASE_JWT_SECRET` caía a `""` sin secretos exportados y python-jose acepta HS256 con clave vacía (forja verificada empíricamente). Ahora `resolve_supabase_jwt_secret()` falla al arranque con clave vacía/placeholder, avisa si se usa el fallback legacy `JWT_SECRET`, y `security.py` (con su placeholder público y sin importadores) fue eliminado.
2. **C2 — Auto-provisionamiento inseguro (crítico, corregido).** El primer login creaba usuarios desde claims sin verificar y elevaba a admin desde `app_metadata.claims_admin`. Ahora exige `email_verified` + claim `email`, nunca deriva admin del token (promoción explícita en DB), y registra IP/User-Agent reales en la auditoría en lugar de placeholders. Políticas y mapping RLS de Supabase documentados en `docs/migration/`.
3. **C3 — Mock silencioso de Supabase en producción (corregido).** `lib/supabase/client.ts` caía a `https://mock.supabase.co` sin variables de entorno; en producción ahora falla rápido, el mock queda acotado a desarrollo/tests con regresión (`tests/supabase-client-config.test.ts`).
4. **Higiene (corregida).** `except Exception` → `JWTError` y imports a nivel de módulo en `deps.py`; `clearStoredToken` purga también las claves legacy `viru_token`/`viru_refresh_token`; mensaje del launcher alineado con la DB real que escribe; kwarg `sqlite_where` restaurado a su forma literal; comentario de estado inerte del demo-account (endpoint 410).

Tests nuevos: `test_empty_key_signature_token_returns_401`, `test_provisioning_requires_email_verified`, `test_provisioning_requires_email_claim`, `test_provisioning_never_grants_admin_from_claims`, `test_provisioned_user_records_real_ip_and_user_agent` y 7 casos del guard de secretos (`TestSecretResolutionGuard`).

## Remaining deferred risks
Ver `UNRESOLVED_RISKS.md`: adopción TanStack por pantalla (SL-08), validación local de Supabase, Playwright multi-navegador y exporter OTLP.

## Cleanup delta (cierre 2026-09-16)
- Restaurado `RefreshToken` en `backend/app/infrastructure/db/models.py`.
- Regenerado `backend/uv.lock` (sin alembic/mako/markupsafe).
- Eliminado `supabase/supabase/` (scaffold duplicado accidental del CLI).
- Corregidos `backend/tests/helpers.py`, `backend/tests/unit/test_quick_search_observability.py`, `backend/tests/unit/test_quick_search_error_observability.py`, `frontend/src/modules/shared/api.ts`, `frontend/tests/e2e/fixtures/auth.fixture.ts`.
- Biome formatter activado + formateo global (348 archivos) y 14 tests de conformidad adaptados.
- `.gitignore`: carpetas de programas históricas de agentes y `.freebuff/` ignoradas.
- Documentación reconciliada: este archivo, `UNRESOLVED_RISKS.md`, `docs/architecture/FINAL_ARCHITECTURE_CHECKLIST.md`, `docs/migration/CUTOVER_LEDGER.md`, `HISTORY.md`.
- **Hardening de seguridad post-review:** `backend/app/api/deps.py` reescrito (guard de secretos + provisión verificada), `backend/app/core/security.py` eliminado, `frontend/src/lib/supabase/client.ts` fail-fast en producción, purga de claves legacy en `api.ts`. Detalle en la sección *Security hardening*.
