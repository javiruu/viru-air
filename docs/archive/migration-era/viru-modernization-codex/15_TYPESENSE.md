# Typesense — búsqueda typo-tolerant e índices derivados

**Prioridad:** OPCIONAL  
**Cuándo ejecutarlo:** Solo cuando PostgreSQL/búsqueda actual no alcance UX/latencia/relevancia necesarias.

## Objetivo para Viru

Añadir búsqueda instantánea para destinos/aeropuertos/hoteles u otros catálogos. Typesense NO debe convertirse en source of truth: se indexan datos de la DB/sistema principal y se pueden reconstruir. Usa aliases para reindex sin downtime y scoped search keys si hay contenido multi-tenant.


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

- Mide tamaño de catálogo, p95 actual, relevancia, errores typo y necesidad de facetas/geosearch.
- Prueba primero Postgres/trigram/full-text si ya resuelve el caso con menos infraestructura.
- Identifica qué colección sería pública vs tenant-private.

## Plan de implementación

1. Diseña collection schema explícito: campos search, sort, facet. No indexar campos innecesarios.
2. Define pipeline DB → Typesense idempotente y reconstruible. Para bulk usa import/upsert en lotes; docs recomiendan bulk para volumen en vez de miles de requests individuales.
3. Usa versioned collection (`destinations_20260912`) + alias estable (`destinations`). Reindexa nueva colección, valida y cambia alias atómicamente.
4. Ajusta `query_by` y prioridad de campos. Typo tolerance es configurable; no aplicar 2 typos a códigos IATA cortos donde puede producir resultados absurdos.
5. API keys: browser solo key de búsqueda limitada. Si hay datos por usuario, usa scoped search key con `filter_by` embebido y parent key de search-only. Nunca main/admin key en cliente.
6. Diseña sync: evento/outbox/job periódico. No dual-write informal desde 15 lugares.
7. Define estrategia de deletes/tombstones.
8. Monitoriza indexing failures; import API puede tener fallos por documento, revisa resultado completo.
9. Search UI debe degradar si Typesense no responde, cuando sea viable.
10. No uses vector/conversational search hasta tener caso real independiente.

## Validación y pruebas obligatorias

- Golden query set: London/lond/londres, Gatwick/gatwik, IATA exacto, acentos, etc. adaptado a datos reales.
- Relevancia esperada y typo tolerance.
- Reindex + alias switch sin downtime.
- Eliminar documento en source termina retirándolo del índice.
- Scoped key no puede acceder a otro tenant.
- Admin key ausente del bundle.
- Load test del autocomplete.

## Rollback

Cambiar feature flag/search adapter de vuelta a PostgreSQL/buscador anterior. Alias permite volver a colección previa si aún existe. El índice se considera recreable, así que no almacena información exclusiva.

## Anti-slop: errores que Codex NO debe cometer

- Hacer Typesense primary DB.
- Main key en frontend.
- Indexar toda la DB.
- Dual-write acoplado a cada request sin recovery.
- Typo tolerance agresiva para códigos cortos.
- Reindex destructivo en colección activa en vez de alias/versionado.
- Ignorar errores parciales del bulk import.



## Documentación oficial investigada

Investigación preparada el **2026-09-12**. Antes de ejecutar, Codex debe comprobar que las páginas siguen vigentes y respetar la versión realmente instalada en el repositorio.

- https://typesense.org/docs/overview/
- https://typesense.org/docs/latest/api/collection-alias.html
- https://typesense.org/docs/29.1/api/documents.html
- https://typesense.org/docs/29.0/api/search.html
- https://typesense.org/docs/28.0/api/api-keys.html


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
