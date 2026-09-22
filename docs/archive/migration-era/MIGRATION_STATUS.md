# MIGRATION_STATUS

Bitácora de progreso del programa de modernización de Viru Tracker.

## Baseline
- Commit: 750e9a1fa06fede4fcad5076c8d90d188402bf9a
- Date: 2026-09-12
- Frontend stack: Next.js 15.5.22, React 19.0.0, TypeScript 5.7.2, Tailwind v4, clsx, lucide-react, Orval 8.32.0, TanStack Query 5.102.8, Zod 4.6.2, shadcn/ui primitives, PostHog 1.430.2
- Backend stack: Python 3.12+, FastAPI 0.116.0, SQLAlchemy 2.0.36, Alembic 1.14.0, Pydantic v2, OpenTelemetry 1.44.0
- DB: SQLite local (viru.db / viru_local.db), PostgreSQL compatible con driver psycopg v3, Supabase migrations versionadas
- Package manager(s): npm (frontend, package-lock.json), uv / pip (backend)
- Build: Next.js build (`npm run build`)
- Typecheck: `npm run typecheck` (Frontend limpio, 0 errores)
- Unit tests: Frontend `npm test` (tsx --test, tests pasando); Backend `pytest tests/unit` (1117 tests pasando)
- E2E: Suite Playwright en `frontend/tests/e2e` (6 tests pasando en Chromium)
- Known pre-existing failures: Ninguno en tests unitarios ni typecheck

## Etapas

### 00_BACKEND_AUDIT — 2026-09-12
Status: DONE
Scope: `docs/architecture/current.md`, `MIGRATION_STATUS.md`
Baseline: Código existente sin mapa documental exhaustivo ni inventario unificado.
Validation: Auditoría completa de 155 endpoints, 62 tablas SQLAlchemy, flujos de autenticación, observabilidad de background workers, inventario de scrapers/proveedores, escaneo de patrones anti-slop (0 bare excepts, 0 TODOs/FIXMEs activos en backend, 0 @ts-ignore en frontend, 162 useEffects clasificados).
Behavior changes: Ninguno (etapa exclusivamente de análisis y documentación).
Data changes: Ninguno.
Security impact: Auditoría de secretos, CORS y verificación de tokens; no se detectaron credenciales expuestas en repo.
Performance impact: N/A.
Rollback: Eliminar `docs/architecture/current.md`.
Deferred work: Ninguno para esta etapa.

### 01_PLAYWRIGHT — 2026-09-12
Status: DONE
Scope: `frontend/playwright.config.ts`, `frontend/tests/e2e/`, `frontend/package.json` (`test:e2e` script)
Baseline: Tests dispersos usando `tsx --test` en Node.js, paquete `playwright` 1.59.1 presente sin runner unificado.
Validation: Instalado `@playwright/test@1.59.1`, configurado `playwright.config.ts` con webServer automático (`dev:warm` en puerto 3000), creadas fixtures de autenticación desacopladas de credenciales reales, implementados 3 specs de journeys críticos (landing/navegación responsive, quick-search con mocks de límites, watchlist con items activos). Ejecución: 6/6 tests pasando en 16.7s.
Behavior changes: Ninguno en la aplicación.
Data changes: Ninguno.
Security impact: Fixtures sin credenciales personales ni secretos en repo.
Performance impact: Suite rápida enfocada en Chromium local con 1 worker para estabilidad.
Rollback: Eliminar `frontend/playwright.config.ts`, `frontend/tests/e2e/` y script `test:e2e`.
Deferred work: Configuración multi-browser (Firefox/WebKit) para CI posterior.

### 02_BIOME — 2026-09-12
Status: DONE
Scope: `frontend/biome.json`, `frontend/package.json` (`lint:biome`, `format:biome`, `check:biome`)
Baseline: ESLint 8.57.1 clásico (`eslint-config-next`).
Validation: Instalado `@biomejs/biome@2.5.13`, configurado `biome.json` con identación de 2 espacios (alineada con el código existente), reglas recomendadas y migración de reglas Next.js. Formateados y verificados archivos E2E (`tests/e2e` 100% verde sin errores). ESLint preservado temporalmente para no perder reglas propietarias de Next.js.
Behavior changes: Ninguno.
Data changes: Ninguno.
Security impact: Ninguno.
Performance impact: Biome analiza archivos en menos de 10ms.
Rollback: Eliminar `frontend/biome.json` y scripts asociados.
Deferred work: Retirada definitiva de ESLint una vez alcanzada paridad total.

### 03_TYPESCRIPT_STRICT — 2026-09-12
Status: DONE
Scope: `frontend/tsconfig.json`, `frontend/package.json` (`typecheck` script)
Baseline: `strict: true` ya activo en `tsconfig.json`, pero sin script `typecheck` formalizado.
Validation: Auditoría de tipos completada (0 `@ts-ignore`, 0 `@ts-expect-error`, 0 `@ts-nocheck`, solo 5 menciones de `any` en comentarios o tipos externos). Añadido script `"typecheck": "tsc --noEmit"` a `package.json`. `npm run typecheck` ejecuta limpio con 0 errores.
Behavior changes: Ninguno.
Data changes: Ninguno.
Security impact: Ninguno.
Performance impact: Compile-time check estricto garantizado.
Rollback: Eliminar script `typecheck` en `package.json`.
Deferred work: Tipos generados en boundaries vía Orval (Fase 1).

### 04_OPENAPI — 2026-09-12
Status: DONE
Scope: `backend/scripts/export_openapi.py`, `docs/architecture/openapi.json`, `backend/tests/unit/test_openapi_contract.py`
Baseline: Endpoint `/openapi.json` generado dinámicamente por FastAPI sin snapshot versionado en repo ni tests de contrato.
Validation: Creado script `export_openapi.py` que exporta el esquema formal a `docs/architecture/openapi.json` (121 rutas, OpenAPI 3.1.0). Creada suite de tests `test_openapi_contract.py` (2 tests pasando) que valida integridad de rutas críticas y sincronización del snapshot contra drift.
Behavior changes: Ninguno.
Data changes: Ninguno.
Security impact: No se exponen secretos ni variables de entorno en el esquema.
Performance impact: N/A.
Rollback: Eliminar script de exportación, snapshot y test unitario.
Deferred work: Conexión con codegen Orval en `05_ORVAL.md`.

### 05_ORVAL — 2026-09-12
Status: DONE
Scope: `frontend/orval.config.ts`, `frontend/src/api/`, `frontend/tests/orval-client.test.ts`, `frontend/package.json` (`api:generate`, `api:check`)
Baseline: Llamadas manuales dispersas a través de wrappers `apiFetch` y tipos DTO escritos a mano en frontend.
Validation: Instalado `orval@8.32.0`. Configurado `orval.config.ts` en modo `tags-split` contra el snapshot `docs/architecture/openapi.json`. Implementado mutator desacoplado `src/api/mutator/custom-client.ts` con inyección de JWT, correlation IDs y normalización de errores. Generados 19 dominios tipados con cabecera de prohibición de edición manual. Añadidos scripts `api:generate` y `api:check` (prueba de drift sin cambios en working tree). Creada suite de pruebas unitarias `tests/orval-client.test.ts` (3/3 pasando). Typecheck y Biome limpios con 0 errores.
Behavior changes: Ninguno en la aplicación (el cliente generado queda listo para el consumo progresivo).
Data changes: Ninguno.
Security impact: Conexión segura preservando tokens JWT en headers y bloqueando SSRF/exposición de credenciales.
Performance impact: Generación instantánea (<1s).
Rollback: Eliminar `src/api/generated`, `src/api/mutator`, `orval.config.ts` y scripts de package.json.
Deferred work: Integración con hooks de TanStack Query v5 en `06_TANSTACK_QUERY.md`.

### 06_TANSTACK_QUERY — 2026-09-12
Status: DONE
Scope: `frontend/src/app/providers/QueryProvider.tsx`, `frontend/src/app/layout.tsx`, `frontend/orval.config.ts`, `frontend/src/api/generated/`, `frontend/package.json`
Baseline: Estado del servidor administrado con `useEffect` locales dispersos y fetches directos sin política de invalidación quirúrgica ni caché unificado.
Validation: Instalado `@tanstack/react-query@^5.102.8` (compatible con React 19). Implementado `QueryProvider` con defaults defensivos (staleTime 30s, gcTime 5m, refetchOnWindowFocus desactivado para evitar tormentas de peticiones accidentales, reintento único). Integrado en `RootLayout`. Orval configurado con `client: "react-query"` para emitir hooks tipados de TanStack Query y query keys estructuradas (`useQuery`, `useMutation`). Regeneración determinista verificada con `api:check`. Typecheck limpio con 0 errores.
Behavior changes: Soporte universal de server state disponible en toda la aplicación; cero roturas visuales o de navegación.
Data changes: Ninguno.
Security impact: Ninguno; no se persiste caché de queries en LocalStorage por defecto.
Performance impact: Evita peticiones duplicadas mediante deduplicación nativa de TanStack Query y staleTime consciente.
Rollback: Revertir `RootLayout` y retirar `QueryProvider`.
Deferred work: Sustitución paulatina de los `useEffect` existentes en cada pantalla.

### 07_ZOD — 2026-09-12
Status: DONE
Scope: `frontend/src/lib/env.ts`, `frontend/src/modules/shared/auth-schema.ts`, `frontend/tests/runtime-validation-zod.test.ts`, `frontend/package.json`
Baseline: Tipos compile-time de TypeScript sin comprobaciones runtime en fronteras externas no confiables (variables de entorno, datos en almacenamiento local del navegador, claims de sesión).
Validation: Instalado `zod@^4.6.2` (Zod 4 estable). Implementados esquemas tipados con `z.infer` en límites críticos: validación estricta de entorno (`validateEnv`, que falla rápido en arranque sin imprimir secretos) y esquema de sesión/almacenamiento (`parseStoredAuth`, `sessionTokenPayloadSchema`, que aísla de datos corruptos mediante `safeParse`). Creada suite de pruebas unitarias `tests/runtime-validation-zod.test.ts` (4/4 pasando) cubriendo casos válidos, fallos esperados y estructuras malformadas. Formateo y linter limpios en Biome (7ms). Typecheck limpio con 0 errores.
Behavior changes: Mayor robustez en el arranque y lectura de almacenamiento; sin cambios visuales ni roturas funcionales.
Data changes: Ninguno.
Security impact: Falla de forma temprana ante configuraciones de entorno inválidas sin volcar secretos; valida claims de JWT antes de su consumo cliente.
Performance impact: Inapreciable (<3ms por parseo).
Rollback: Eliminar esquemas Zod en `src/lib/env.ts` y `src/modules/shared/auth-schema.ts`.
Deferred work: Integración progresiva de validación runtime en formularios de usuario (Fase 3).

### 08_SUPABASE — 2026-09-12
Status: PARTIAL
Scope: `supabase/config.toml`, `supabase/migrations/20260912000001_create_flight_watch.sql`, `supabase/seed.sql`
Baseline: Persistencia única en SQLite local (`viru.db`) o Postgres backend sin RLS formalizado.
Validation: Inicializada estructura con Supabase CLI (`supabase init`). Modelado el dominio inicial de bajo riesgo (`flight_watch`) con tipos PostgreSQL nativos, restricciones de unicidad e índices de rendimiento. Implementadas 5 políticas estrictas de Row Level Security (RLS) aislando el acceso entre usuarios autenticados (`auth.uid()`), bloqueando acceso anónimo y habilitando bypass seguro para `service_role` (workers backend). Añadido `seed.sql` con datos sintéticos no-PII.
Behavior changes: Ninguno (estructura preparada para migración gradual sin romper lecturas actuales).
Data changes: Nueva migración de esquema declarativo en `supabase/migrations/`.
Security impact: RLS obligatorio impide que usuarios lean o modifiquen registros de otros usuarios incluso ante vulnerabilidad de consulta en frontend.
Performance impact: Índices dedicados en `user_id` y claves compuestas de ruta para acelerar evaluación de políticas RLS.
Rollback: Eliminar carpeta `supabase/`.
Deferred work: Conexión con proyecto remoto (diferido según política del host).

### 09_DRIZZLE_DECISION — 2026-09-12
Status: NOT_APPLICABLE
Scope: `docs/architecture/adr/0001-drizzle-decision.md`
Baseline: Evaluación obligatoria requerida por el decision gate antes de introducir dependencias adicionales.
Validation: Evaluados los cuatro criterios de decisión. Viru cuenta con SQLAlchemy 2.0 y Alembic como ORM maduro en Python y el frontend Next.js consume datos vía API REST tipada generada por Orval, por lo que Drizzle introduciría duplicación innecesaria de esquemas y riesgo de colisiones de migraciones. Creado ADR formal registrando el rechazo de Drizzle.
Behavior changes: Ninguno.
Data changes: Ninguno.
Security impact: Ninguno.
Performance impact: Evita añadir paquetes pesados de ORM no necesarios en el bundle.
Rollback: Reabrir evaluación mediante nuevo ADR si cambia la arquitectura del frontend a consultas SQL directas.
Deferred work: Ninguno.

### 10_SHADCN_UI — 2026-09-12
Status: DONE
Scope: `frontend/components.json`, `frontend/src/components/ui/button.tsx`, `frontend/src/components/ui/badge.tsx`, `frontend/src/components/ui/card.tsx`, `frontend/tests/shadcn-ui-primitives.test.tsx`, `frontend/package.json`
Baseline: Componentes locales y estilos a medida sin primitivas UI estandarizadas en `components/ui`.
Validation: Configurado `components.json` con aliases de Viru Air y Tailwind v4. Instalado `class-variance-authority@^0.7.1` (Radix Slot ya integrado). Implementadas primitivas base (`Button`, `Badge`, `Card`) preservando la identidad cálida aeronáutica y tokens de color sin rediseñar globalmente la UI. Creada suite unitaria `tests/shadcn-ui-primitives.test.tsx` (4/4 pasando con renderToString). Biome y typecheck limpios con 0 errores.
Behavior changes: Primitivas accesibles disponibles para el diseño de componentes; cero impacto visual en pantallas existentes.
Data changes: Ninguno.
Security impact: Ninguno.
Performance impact: Primitivas ligeras basadas en clases CSS y CVA sin dependencias de runtime pesadas.
Rollback: Eliminar primitivas en `src/components/ui/`.
Deferred work: Adopción gradual en pantallas específicas sin forzar reescrituras masivas.

### 11_POSTHOG — 2026-09-12
Status: DONE
Scope: `frontend/src/lib/posthog.ts`, `frontend/tests/posthog-governance.test.ts`, `frontend/package.json`
Baseline: Sin analítica de producto ni feature flags para rollouts canarios reversibles.
Validation: Instalado `posthog-js@^1.430.2`. Creado wrapper gobernado `src/lib/posthog.ts` con taxonomía estricta de 5 eventos de producto (`search_initiated`, `search_completed`, `watchlist_item_added`, `watchlist_item_removed`, `alert_rule_created`). Enmascaramiento total de inputs en grabaciones de sesión (`maskAllInputs: true`). Operación no bloqueante con no-op seguro cuando `NEXT_PUBLIC_POSTHOG_KEY` no está configurado (tests/local). Helper `isFeatureFlagEnabled` con fallback seguro. Creada suite de pruebas unitarias `tests/posthog-governance.test.ts` (2/2 pasando).
Behavior changes: Ninguno en la UI; telemetría y feature flags opcionales listas para producción.
Data changes: Ninguno.
Security impact: Autocapture desactivado; cero captura de contraseñas, tokens de autenticación ni datos sensibles de proveedores.
Performance impact: Carga condicional y ejecución silenciosa en segundo plano.
Rollback: Eliminar `src/lib/posthog.ts` y dependencia `posthog-js`.
Deferred work: Configuración de dashboards en PostHog Cloud tras despliegue de producción.

### 12_OPENTELEMETRY — 2026-09-12
Status: DONE
Scope: `backend/app/core/telemetry.py`, `backend/tests/unit/test_telemetry.py`, `backend/.venv`
Baseline: Logs estructurados basados en `logging` con correlation IDs en ContextVar sin spans distribuidos ni semántica estándar de trazas.
Validation: Instalado `opentelemetry-api` y `opentelemetry-sdk` (v1.44.0). Implementado módulo `app/core/telemetry.py` con Resource estándar (`service.name: viru-backend`, `deployment.environment`), propagación de `correlation_id` a los spans y gestor de contexto `trace_operation` con redacción automática de atributos sensibles (tokens, secretos, contraseñas). Creada suite de tests unitarios `backend/tests/unit/test_telemetry.py` (3/3 pasando) verificando inicialización, inyección de correlación y captura de excepciones en spans.
Behavior changes: Trazabilidad OpenTelemetry estándar disponible en el backend sin alterar respuestas HTTP.
Data changes: Ninguno.
Security impact: Atributos de alta sensibilidad redactados automáticamente de los atributos del span.
Performance impact: Overhead mínimo (<0.1ms por span en proceso local).
Rollback: Eliminar `backend/app/core/telemetry.py` y `test_telemetry.py`.
Deferred work: Exportación OTLP hacia OpenTelemetry Collector en entorno productivo.

### 13_VALKEY — 2026-09-12
Status: READY / DEFERRED
Scope: `docs/architecture/adr/0002-infrastructure-gates.md`
Baseline: Evaluación de necesidad de caché distribuida.
Validation: Viru backend ya dispone de conectores compatibles con Redis/Valkey en `app/infrastructure/redis_client.py` y fallback en memoria. Despliegue de nodo Valkey dedicado diferido en ADR 0002 hasta requerimiento de escala productiva.
Behavior changes: Ninguno.
Data changes: Ninguno.
Security impact: Ninguno.
Performance impact: Ninguno.
Rollback: N/A.
Deferred work: Despliegue de clúster Valkey en producción.

### 14_TRIGGER_DEV — 2026-09-12
Status: NOT_APPLICABLE / DEFERRED
Scope: `docs/architecture/adr/0002-infrastructure-gates.md`
Baseline: Evaluación de jobs durables.
Validation: Workers de Viru están escritos en Python nativo acoplados a SQLAlchemy y scrapers. Trigger.dev está orientado a TypeScript; cruzar la frontera de lenguajes añadiría sobrecoste sin valor actual. Evaluado y documentado en ADR 0002.
Behavior changes: Ninguno.
Data changes: Ninguno.
Security impact: Ninguno.
Performance impact: Ninguno.
Rollback: N/A.
Deferred work: Ninguno.

### 15_TYPESENSE — 2026-09-12
Status: NOT_APPLICABLE
Scope: `docs/architecture/adr/0002-infrastructure-gates.md`
Baseline: Búsqueda de destinos y aeropuertos.
Validation: El catálogo de aeropuertos en memoria responde en <2 ms con normalización de diacríticos y prefijos IATA. Introducir Typesense duplicaría índices innecesariamente. Rechazado en ADR 0002.
Behavior changes: Ninguno.
Data changes: Ninguno.
Security impact: Ninguno.
Performance impact: Ninguno.
Rollback: N/A.
Deferred work: Ninguno.

### 16_TEMPORAL — 2026-09-12
Status: NOT_APPLICABLE
Scope: `docs/architecture/adr/0002-infrastructure-gates.md`
Baseline: Orquestación de workflows complejos.
Validation: Descartado formalmente según la regla 10 de los guardrails globales. Los workers actuales con reintentos y leases cubren la necesidad sin añadir la complejidad operativa de un servidor Temporal. Rechazado en ADR 0002.
Behavior changes: Ninguno.
Data changes: Ninguno.
Security impact: Ninguno.
Performance impact: Ninguno.
Rollback: N/A.
Deferred work: Ninguno.

