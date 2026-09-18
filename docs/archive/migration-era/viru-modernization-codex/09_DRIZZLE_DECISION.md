# Drizzle ORM — decision gate, NO instalar por defecto

**Prioridad:** OPCIONAL  
**Cuándo ejecutarlo:** Solo después de decidir Supabase/schema ownership.

## Objetivo para Viru

Decidir si un ORM/query builder TypeScript aporta valor. Con Supabase, Drizzle puede convivir, pero **debe existir un único dueño de migrations/schema**. Si el backend principal es Python/FastAPI, introducir Drizzle únicamente para “hacer la DB más moderna” probablemente añade complejidad.


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

- ¿Qué lenguaje hace queries servidor actualmente?
- ¿Supabase migrations serán source of truth?
- ¿Existe ORM actual maduro?
- ¿Hay query duplication/dynamic SQL que Drizzle solucionaría?
- ¿Drizzle permitiría eliminar más código del que añade?

## Plan de implementación

### Decision gate
Implementa Drizzle SOLO si se cumplen todas:
1. Existe un runtime TypeScript server-side relevante que necesita acceso SQL directo.
2. No se crea una segunda capa equivalente a ORM existente.
3. Se decide claramente quién gestiona migrations.
4. El beneficio se demuestra con un slice concreto.

### Si se adopta con Supabase como source of truth
- Preferencia: migrations de Supabase/SQL siguen siendo autoridad.
- Usa Drizzle como query layer y, si necesitas schema TS, genera/pull de forma controlada o mantenlo alineado mediante CI.
- No alternes `supabase db push` y `drizzle-kit push` sobre producción.

### Si Drizzle es source of truth (solo decisión explícita)
- Usa `drizzle-kit generate` + migrations revisadas y `drizzle-kit migrate`.
- Integra RLS/funciones/DDL especial con custom SQL migrations cuando sea necesario.
- Asegura que tooling Supabase no genere una historia paralela incompatible.

Prueba primero un dominio pequeño y mide reducción real de código.

## Validación y pruebas obligatorias

- Reproducir schema desde cero.
- Detectar drift entre Drizzle y DB/Supabase.
- Tests de queries y RLS siguen verdes.
- Ninguna migration aplicada por dos sistemas distintos.

## Rollback

Si el piloto no reduce complejidad, retirar Drizzle y conservar SQL/Supabase source of truth. Al no haber hecho migrations irreversibles exclusivas, rollback debe ser simple.

## Anti-slop: errores que Codex NO debe cometer

- Dos migration histories.
- `drizzle-kit push` a prod por comodidad.
- Drizzle en frontend.
- Reescribir un backend Python solo para usar Drizzle.
- Duplicar Supabase generated types y Drizzle models por todas partes.



## Documentación oficial investigada

Investigación preparada el **2026-09-12**. Antes de ejecutar, Codex debe comprobar que las páginas siguen vigentes y respetar la versión realmente instalada en el repositorio.

- https://orm.drizzle.team/docs/migrations
- https://orm.drizzle.team/docs/drizzle-kit-generate
- https://orm.drizzle.team/docs/drizzle-kit-migrate
- https://orm.drizzle.team/docs/connect-supabase


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
