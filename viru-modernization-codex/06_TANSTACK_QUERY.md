# TanStack Query — server state del frontend

**Prioridad:** ALTA  
**Cuándo ejecutarlo:** Después de Orval en frontend React; `NOT_APPLICABLE` si no es React/TanStack-compatible.

## Objetivo para Viru

Concentrar fetching/caching/invalidation de server state y retirar `useEffect` + caches manuales. No debe usarse como store global para estado puramente UI.


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

- Confirma framework y versión de React.
- Inventaria todos los fetches y clasifica: server state, local UI state, form state, realtime stream.
- Busca caches manuales, polling, dedupe y abort controllers.
- Identifica queries que contienen datos sensibles o demasiado grandes para persistencia cliente.

## Plan de implementación

1. Instala `@tanstack/react-query` solo en frontend React.
2. Crea un único `QueryClient` con defaults conscientemente elegidos. La documentación advierte que queries son stale por defecto y pueden refetchear al montar/focus/reconnect; no cambies globales sin entenderlo.
3. Define política de query keys consistente, idealmente apoyada por helpers generados de Orval.
4. Migra GET/read operations primero. Elimina `loading/error/data` manual solo después de paridad.
5. Migra mutations y define invalidación quirúrgica en `onSuccess`; evita invalidar todo el cache.
6. Usa staleTime según semántica: aeropuertos casi estáticos ≠ precios de vuelo dinámicos. Documenta valores anómalos.
7. Propaga AbortSignal a fetchers generados cuando esté soportado para cancelar trabajo obsoleto.
8. Decide polling solo donde exista necesidad y visibility/network behavior sea correcto.
9. Devtools solo en desarrollo si se desea.
10. No persistas cache a storage por defecto; requiere análisis de privacidad, invalidez y tamaño.

## Validación y pruebas obligatorias

- Tests de queries/mutations clave con backend mock/controlado.
- Playwright comprueba que crear/borrar watchlist actualiza UI sin refresh accidental.
- Confirmar que volver al tab no dispara tormenta de requests.
- Medir número de requests en journeys antes/después.
- Probar abort/cambio rápido de parámetros en búsquedas.

## Rollback

Se puede volver por feature a hooks/fetchers previos. QueryClient provider puede mantenerse mientras se revierte una pantalla. Eliminar queries viejas al cerrar migración.

## Anti-slop: errores que Codex NO debe cometer

- Usarlo para todo el estado de React.
- `staleTime: Infinity` global para “arreglar demasiados requests”.
- Invalidar todas las queries tras cualquier mutation.
- Duplicar cache de TanStack con Zustand/Redux/local state para los mismos datos.
- Ignorar cancelación en búsquedas rápidas.
- Asumir que datos cached están runtime-validados solo porque están tipados.



## Documentación oficial investigada

Investigación preparada el **2026-09-12**. Antes de ejecutar, Codex debe comprobar que las páginas siguen vigentes y respetar la versión realmente instalada en el repositorio.

- https://tanstack.com/query/latest/docs/framework/react/guides/important-defaults
- https://tanstack.com/query/latest/docs/framework/react/guides/invalidations-from-mutations
- https://tanstack.com/query/latest/docs/framework/react/guides/query-cancellation
- https://tanstack.com/query/latest/docs/framework/react/guides/query-functions


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
