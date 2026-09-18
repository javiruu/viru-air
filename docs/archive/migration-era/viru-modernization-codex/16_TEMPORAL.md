# Temporal — workflows durables de alta complejidad

**Prioridad:** DEFER / última opción  
**Cuándo ejecutarlo:** Solo si Trigger.dev/workers simples dejan de ser suficientes y existen workflows multi-step críticos de larga duración.

## Objetivo para Viru

Temporal garantiza reanudación durable de workflows tras fallos, pero introduce un modelo mental y una plataforma considerable. Para Viru debe ser una decisión de escala/fiabilidad demostrada, no una mejora estética. Workflows, Activities, Workers, versioning y safe deployments requieren disciplina específica.


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

Decision gate: documentar al menos un workflow que necesite estado durable durante minutos/días, múltiples pasos/side effects, recovery tras process crash, señales/timers o compensación y que no se resuelva limpiamente con jobs existentes/Trigger.dev. Si no existe, DEFER.

## Plan de implementación

1. Realiza un spike fuera del critical path con SDK del lenguaje real del worker; Temporal soporta múltiples SDKs, no migres lenguaje solo por usar TypeScript.
2. Modela Workflow como orquestación determinista; I/O y side effects van a Activities. No llames APIs/DB/random/time no determinista directamente desde Workflow salvo APIs soportadas por SDK.
3. Define timeouts/retry policies de Activities según operación y idempotencia.
4. IDs de Workflow deben modelar identidad de negocio para evitar duplicados cuando corresponda.
5. Usa Signals/Updates/Queries según semántica oficial, no polling casero alrededor de Temporal.
6. Planifica versioning/safe deployments antes del primer workflow productivo: workflows históricos pueden re-ejecutar código mediante event history.
7. Tests con entorno oficial/in-memory/time-skipping donde soporte SDK; no dependas solo de E2E lentos.
8. Instrumenta Workers y task queues. Capacity/concurrency se dimensiona por carga real.
9. Define data retention/encryption/converters si payloads contienen datos sensibles.
10. Migración desde worker anterior: inicia workflows nuevos en Temporal; termina/drain antiguos; no intentes importar estado in-flight sin estrategia específica.

## Validación y pruebas obligatorias

- Test de crash/restart: workflow continúa correctamente.
- Activity retry no duplica side effect.
- Timeout/cancel propagation.
- Upgrade compatible con workflows en ejecución siguiendo versión/safe deployment recomendado por SDK.
- Observabilidad de stuck workflows/task queues.
- Load test Worker capacity si llega a producción.

## Rollback

Parar creación de nuevos workflows y enrutar nuevos jobs al sistema anterior. Los workflows existentes no pueden abandonarse sin entender su estado: drain/complete/cancel/terminate según semántica. Esto exige runbook específico y es una razón para no adoptar Temporal prematuramente.

## Anti-slop: errores que Codex NO debe cometer

- Meter I/O dentro de Workflow.
- Cambiar lógica de workflow incompatible sin versioning.
- Usar Temporal como simple cron de dos líneas.
- Reescribir todos los workers.
- Activities no idempotentes con retries.
- Ignorar payload size/PII/event history.
- Adoptarlo antes de tener tests y observabilidad sólidos.

## Regla de parada

Si Codex no puede demostrar por escrito por qué una solución más simple falla, **no instalar Temporal**. La complejidad que evita en sistemas distribuidos grandes puede convertirse en AI slop infraestructural en un proyecto que todavía no la necesita.

## Documentación oficial investigada

Investigación preparada el **2026-09-12**. Antes de ejecutar, Codex debe comprobar que las páginas siguen vigentes y respetar la versión realmente instalada en el repositorio.

- https://docs.temporal.io/
- https://docs.temporal.io/develop
- https://docs.temporal.io/develop/typescript
- https://docs.temporal.io/develop/typescript/workflows
- https://docs.temporal.io/develop/typescript/activities
- https://docs.temporal.io/develop/typescript/testing-suite


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
