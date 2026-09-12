# Orval — cliente TypeScript generado desde OpenAPI

**Prioridad:** CRÍTICA  
**Cuándo ejecutarlo:** Solo cuando OpenAPI sea suficientemente estable.

## Objetivo para Viru

Eliminar fetchers y tipos duplicados escritos a mano. Orval debe generar un cliente reproducible; el output es desechable y nunca source of truth. Puede generar TanStack Query hooks y schemas Zod/runtime validation según configuración.


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

- Detecta dónde viven API clients/fetch wrappers actuales.
- Lista interceptors: auth headers, base URL, refresh, correlation IDs, locale, abort signals.
- Localiza tipos frontend duplicados de DTOs backend.
- Detecta si usa fetch o axios y no cambies transporte sin razón.

## Plan de implementación

1. Añade Orval como dev dependency.
2. Configura `orval.config.ts` con input reproducible (snapshot local o endpoint local), output en directorio claramente generado y `clean`/estructura apropiada.
3. Para React + TanStack Query, usa `client: "react-query"`; para otros frontends usa cliente compatible. No instales React Query si la app no es React.
4. Mantén el transporte actual (`fetch` o axios) salvo decisión explícita. Implementa un mutator para auth/baseURL/error normalization si hace falta, fuera del generated output.
5. Decide mode (`tags-split` suele escalar mejor) solo después de ver tags/operationIds. Evita cientos de archivos absurdos por tags mal diseñadas.
6. Añade `api:generate` y `api:check`/drift en CI. Generar desde un spec inmutable para la misma revisión.
7. Migra endpoint por endpoint: reemplaza types/fetchers manuales por generated client y elimina duplicados después de tests.
8. Activa AbortSignal en queries cuando corresponda.
9. Si se usa runtime validation de Orval + Zod, evita validar dos veces la misma frontera sin beneficio.
10. Nunca editar output generado. Toda personalización debe vivir en config/mutators/adapters.

## Validación y pruebas obligatorias

- Regenerar dos veces y confirmar working tree limpio (determinismo).
- Typecheck generated code.
- Test auth headers/base URL/error mapping.
- Comparar requests/responses de journeys críticos antes/después.
- CI debe fallar si OpenAPI cambia y generated client quedó stale, según estrategia elegida.

## Rollback

Revertir consumidores a cliente manual anterior mientras se conserva OpenAPI. El output generado puede borrarse y regenerarse. No conservar dos clientes activos indefinidamente.

## Anti-slop: errores que Codex NO debe cometer

- Editar generated code a mano.
- Generar nombres horribles porque OpenAPI tiene operation IDs malos en vez de arreglar el contrato.
- Hardcodear URL prod.
- Duplicar modelos generados en `/types`.
- Crear un “API service” wrapper por encima de cada función generada sin aportar lógica.
- Regeneración no determinista contra prod.



## Documentación oficial investigada

Investigación preparada el **2026-09-12**. Antes de ejecutar, Codex debe comprobar que las páginas siguen vigentes y respetar la versión realmente instalada en el repositorio.

- https://orval.dev/docs/
- https://orval.dev/docs/guides/basics/
- https://orval.dev/docs/guides/react-query/
- https://orval.dev/docs/reference/configuration/output/


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
