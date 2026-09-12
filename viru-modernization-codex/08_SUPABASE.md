# Supabase — PostgreSQL/Auth/RLS como capa de estado

**Prioridad:** CRÍTICA pero posterior a contratos/tests  
**Cuándo ejecutarlo:** Cuando baseline, OpenAPI y tests estén estables. Migración dominio por dominio.

## Objetivo para Viru

Hacer explícito y reproducible el estado persistente de Viru, empezando por dominios commodity (usuarios, auth, preferencias, watchlists, historial) sin tocar la inteligencia propia del motor de búsqueda/scrapers. Supabase debe introducirse mediante migrations versionadas y RLS probado, no cambios manuales irrepetibles en Dashboard.


## Contrato de ejecución para Codex

Este documento es una **especificación de migración**, no una invitación a reescribir el proyecto. Antes de modificar código:

1. Lee `00_START_HERE.md`, `00_GLOBAL_GUARDRAILS.md` y `00_BACKEND_AUDIT.md`.
2. Detecta el stack real. No asumas React, Vite, npm, FastAPI, PostgreSQL ni una estructura de carpetas concreta.
3. Detecta el package manager a partir del lockfile y **no mezcles** npm/pnpm/yarn/bun.
4. Ejecuta y registra el baseline actual: build, tests, typecheck/lint disponibles y los flujos E2E existentes.
5. Crea una rama/worktree de migración y realiza cambios pequeños, revisables y reversibles.
6. No elimines una implementación antigua hasta demostrar paridad funcional y tener rollback documentado.
7. No cambies simultáneamente arquitectura, diseño visual y comportamiento de negocio salvo que este documento lo exija explícitamente.
8. Nunca introduzcas secretos, tokens, contraseñas, claves service-role o DSN privados en el repositorio, fixtures, logs o screenshots.
9. Todo código generado automáticamente debe quedar claramente separado del código escrito a mano y, cuando sea viable, regenerarse en CI para detectar drift.
10. Si la documentación oficial actual contradice este archivo por una actualización posterior, **la documentación oficial gana**. Documenta la diferencia antes de continuar.

### Gate obligatorio antes de cerrar la tarea

La tarea NO está terminada por “compila en mi máquina”. Debe existir evidencia de:

- build correcto;
- typecheck correcto si el proyecto usa TypeScript;
- linter/formatter correcto si aplica;
- unit/integration tests relevantes correctos;
- Playwright correcto para los flujos afectados;
- cero secretos añadidos;
- diff revisado para detectar archivos generados accidentalmente, duplicación y código muerto;
- actualización de `MIGRATION_STATUS.md` con cambios, comandos ejecutados, resultados, riesgos y rollback.

Si un gate previo ya estaba roto, no lo ocultes. Registra exactamente qué fallaba antes y demuestra que la migración no lo empeora.


## Descubrimiento obligatorio antes de tocar código

- Identifica DB actual, schema, tamaño, constraints, índices, FKs, triggers y migrations existentes.
- Mapea auth actual: IDs de usuario, hash/identity provider, sesiones, refresh, emails.
- Determina qué datos pertenecen a Supabase y cuáles deben seguir en backend/workers.
- Localiza todas las lecturas/escrituras por dominio.
- Define ownership: backend-only vs acceso cliente permitido vía Supabase SDK.
- Haz inventario de datos sensibles y requerimientos de retención.

## Plan de implementación

### A. Preparación reproducible
1. Añade Supabase CLI como herramienta de desarrollo según stack y ejecuta `supabase init` en repo. El directorio `supabase/` se versiona.
2. Usa stack local mediante container runtime. No experimentes primero en producción.
3. Si ya existe proyecto remoto, trae su estado al workflow local según docs antes de crear migrations divergentes.
4. Crea `seed.sql` con datos sintéticos mínimos, nunca dumps de PII real.

### B. Diseño de schema
5. Modela tablas por dominio con PK/FK/NOT NULL/CHECK/UNIQUE e índices reales. Evita JSONB como escape universal.
6. Usa migrations SQL pequeñas y nominales (`supabase migration new ...`). Reproduce desde cero con reset local.
7. Genera TypeScript types desde schema y no los edites manualmente.

### C. Seguridad RLS
8. En toda tabla de schema expuesto, habilita RLS y define grants/policies explícitas. La documentación actual advierte que una tabla expuesta sin RLS puede ser accesible a roles con grants.
9. Separa `anon`, `authenticated` y service/backend. Nunca expongas service-role en frontend.
10. Testea SELECT/INSERT/UPDATE/DELETE positivos y **negativos** con pgTAP / `supabase test db`.
11. Indexa columnas usadas por policies. Cuando aplique, patrones como `(select auth.uid()) = user_id` pueden evitar evaluar la función por fila; verifica plan/performance.
12. Views accesibles deben respetar RLS; en Postgres moderno considera `security_invoker = true` cuando corresponda.

### D. Migración de datos — expand/contract
13. Elige un dominio inicial de bajo riesgo (p.ej. preferencias o watchlists, no todo auth a la vez).
14. Crea schema nuevo sin romper lecturas actuales.
15. Backfill idempotente con counts/constraints y reporte de errores.
16. Si necesitas dual-write temporal, añade idempotency/reconciliation y métrica de divergencia. Evítalo si puedes hacer cutover corto.
17. Shadow-read/compare en entorno controlado cuando sea viable.
18. Cambia lectores/escritores por feature flag o release reversible.
19. Ejecuta E2E y métricas.
20. Solo después retira implementación anterior y, en otra migration, columnas/tablas antiguas.

### E. Auth
21. Tratar auth como migración independiente. No cambies IDs de usuario sin una tabla/mapa estable de identidad. Revisa métodos oficiales de migración disponibles para el proveedor actual en la documentación vigente.
22. Prueba signup/login/logout/refresh/reset/email/OAuth que realmente use Viru, además de ownership de datos tras login.

### F. CI/CD
23. CI debe levantar Supabase local, aplicar migrations desde cero, ejecutar `supabase test db`, generar types y detectar drift.
24. Producción: backup/snapshot verificado, ventana/locks estudiados, migrations revisadas. No usar Dashboard como única fuente de cambios.

## Validación y pruebas obligatorias

- `supabase db reset` o flujo local equivalente recrea proyecto desde cero.
- `supabase test db` verde con RLS positive/negative cases.
- Type generation deterministic.
- Conteos y relaciones post-backfill coinciden con origen.
- Dos usuarios de prueba no pueden leer/modificar datos del otro.
- Usuario anon no puede acceder a datos privados.
- Service path solo existe server-side.
- Playwright de auth/watchlist/historial según dominio migrado.
- Medir query plans/latencia en tablas/policies relevantes.

## Rollback

Cada dominio requiere runbook. Antes de cutover conservar origen y backup. Si falla: desactivar feature flag/cambiar router al source anterior; detener writers nuevos si existe riesgo de divergencia; reconciliar writes producidos durante ventana; no borrar schema nuevo hasta entender fallo. Cambios destructivos solo después del periodo de seguridad definido.

## Anti-slop: errores que Codex NO debe cometer

- “Migra todo a Supabase” en una PR.
- Crear tablas a mano en Dashboard sin migration.
- Desactivar RLS para que “funcione”.
- Usar service-role en browser.
- Policy `for all` permisiva sin tests negativos.
- Usar JSONB para evitar diseño de schema.
- Dual-write sin reconciliación.
- Borrar DB vieja inmediatamente tras primer deploy.
- Mezclar migración de Auth y cambio de todos los IDs/domain models a la vez.
- Tener Supabase migrations y Drizzle migrations compitiendo por el mismo schema.



## Documentación oficial investigada

Investigación preparada el **2026-09-12**. Antes de ejecutar, Codex debe comprobar que las páginas siguen vigentes y respetar la versión realmente instalada en el repositorio.

- https://supabase.com/docs/guides/local-development
- https://supabase.com/docs/guides/local-development/cli-workflows
- https://supabase.com/docs/guides/local-development/database-migrations
- https://supabase.com/docs/guides/deployment/database-migrations
- https://supabase.com/docs/guides/database/postgres/row-level-security
- https://supabase.com/docs/guides/local-development/testing/overview
- https://supabase.com/docs/guides/local-development/cli/testing-and-linting
- https://supabase.com/docs/guides/api/rest/generating-types


## Informe que Codex debe dejar al terminar

Añade a `MIGRATION_STATUS.md` una entrada con este formato:

```md
### <tecnología> — <fecha>
Status: DONE | PARTIAL | BLOCKED | NOT_APPLICABLE
Scope: <archivos/módulos tocados>
Baseline: <comandos + resultado antes>
Validation: <comandos + resultado después>
Behavior changes: <ninguno o lista explícita>
Data changes: <ninguno o migraciones exactas>
Security impact: <resumen>
Performance impact: <mediciones si aplica>
Rollback: <pasos concretos>
Deferred work: <lista>
```
