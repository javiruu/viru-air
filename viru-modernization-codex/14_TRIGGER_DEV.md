# Trigger.dev — background jobs durables/colas/schedules

**Prioridad:** OPCIONAL / útil si workers actuales duelen  
**Cuándo ejecutarlo:** Solo tras auditar jobs actuales y demostrar problemas de retry, cron, dedupe, observabilidad o concurrencia.

## Objetivo para Viru

Sustituir cron/workers ad-hoc por tasks observables y resilientes cuando haya valor claro. Trigger.dev es principalmente TypeScript, aunque dispone de mecanismos/extensiones para ejecutar Python; si el núcleo de workers Viru es Python, el coste de frontera debe evaluarse antes.


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

- Inventaria jobs actuales con frecuencia, duración, lenguaje, retries, concurrency, locks, side effects y SLA.
- Identifica cuáles son idempotentes y cuáles no.
- Cuenta incidentes reales: duplicados, cron perdidos, jobs colgados, overload de providers.
- Decide Cloud vs self-host. La documentación señala que self-host carece de algunas capacidades Cloud como checkpoints/auto-scaling/warm starts en la matriz actual; verificar antes de elegir.

## Plan de implementación

1. Piloto con UN job no crítico y claramente idempotente.
2. Define payload con schema estable/versionable y IDs, no blobs enormes.
3. Configura retry por error class: network/429 retryable; validation/4xx lógico normalmente no. Usa exponential backoff/jitter.
4. Añade idempotency keys para side effects. Atención: docs actuales indican que desde v4.3.1 raw strings usan scope `run` por defecto; usa scope `global` explícito cuando esa sea la semántica deseada.
5. Usa queues/concurrency para límites de proveedores. No confundir retry con rate limit.
6. Para schedules estáticos, preferir declarativos/versionados; para dinámicos, usa `deduplicationKey` y timezone IANA. Documentación advierte que la dedup key de schedule es per-project, no per-environment: incluye entorno si procede.
7. Define TTL para runs que ya no tienen valor si quedan en cola (precio refresh antiguo).
8. Side effects deben ser idempotentes: notification/email/DB mutation con unique constraint o idempotency key.
9. Integra logs/traces correlacionados y dashboard/run IDs.
10. Migra job por job; durante cutover deshabilita scheduler antiguo antes de activar el nuevo para evitar dobles ejecuciones.

## Validación y pruebas obligatorias

- Forzar fallo retryable y comprobar número/backoff.
- Forzar fallo no-retryable.
- Disparar mismo idempotency key dos veces y verificar semántica.
- Probar concurrency limit con múltiples jobs.
- Probar schedule/timezone y dedup.
- Simular worker deploy/restart.
- Verificar no hay doble scheduler activo.
- Playwright si UI muestra estado de tasks.

## Rollback

Mantener código del worker previo hasta validar periodo acordado. Rollback = desactivar schedule/task Trigger, esperar/cancelar runs según semántica, reactivar scheduler anterior, reconciliar side effects usando IDs/idempotency records.

## Anti-slop: errores que Codex NO debe cometer

- Migrar todos los workers a la vez.
- Retry de operaciones no idempotentes.
- Raw idempotency key suponiendo scope global.
- Duplicar schedules por entorno.
- Concurrency ilimitada contra proveedor con rate limit.
- Self-hosting por defecto ignorando feature differences actuales.
- Usar Trigger.dev para una función síncrona de 20 ms sin necesidad.



## Documentación oficial investigada

Investigación preparada el **2026-09-12**. Antes de ejecutar, Codex debe comprobar que las páginas siguen vigentes y respetar la versión realmente instalada en el repositorio.

- https://trigger.dev/docs/introduction
- https://trigger.dev/docs/tasks/overview
- https://trigger.dev/docs/errors-retrying
- https://trigger.dev/docs/idempotency
- https://trigger.dev/docs/queue-concurrency
- https://trigger.dev/docs/tasks/scheduled
- https://trigger.dev/docs/self-hosting/overview


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
