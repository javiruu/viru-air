# OpenAPI — contrato canónico backend ↔ frontend

**Prioridad:** CRÍTICA  
**Cuándo ejecutarlo:** Después del baseline/type gates; antes de Orval.

## Objetivo para Viru

Convertir endpoints reales en un contrato machine-readable estable. Si el backend es FastAPI, aprovechar sus modelos Pydantic y `/openapi.json`; no mantener un YAML manual divergente salvo que exista una razón arquitectónica fuerte.


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

- Inventaria todos los endpoints y consumidores.
- Detecta framework backend y versión de OpenAPI que emite.
- Si es FastAPI, revisa request bodies, `response_model`/return annotations, errores, auth dependencies y operation IDs.
- Detecta endpoints que devuelven dicts amorfos, unions no documentadas, streaming/files y respuestas fuera del schema.

## Plan de implementación

1. Decide source of truth: preferencia en FastAPI = código tipado/Pydantic → OpenAPI generado. En otro backend, define proceso equivalente.
2. Da a cada operación un `operationId` estable y semántico. Evita IDs derivados de nombres accidentales si Orval los consumirá.
3. Declara request y response schemas explícitos. En FastAPI, usa modelos Pydantic/return types para que el framework valide y filtre output.
4. Documenta errores importantes (400/401/403/404/409/422/429/5xx cuando proceda) y estructuras de error consistentes.
5. Define auth schemes sin incluir secretos.
6. Separa modelos internos del proveedor externo de los DTO públicos. No filtres payloads crudos de scrapers al frontend.
7. Exporta un snapshot reproducible de OpenAPI para CI/codegen, o genera el cliente directamente contra una instancia local determinista. Nunca apuntes codegen a producción como única estrategia.
8. Añade validación de spec y una prueba de drift: si cambia OpenAPI, el diff debe revisarse.
9. Versiona breaking changes deliberadamente. No renombres campos/operation IDs “por limpieza” sin migrar consumidores.
10. Para FastAPI, evita customizar `.openapi()` salvo necesidad real; si se hace, cachea/valida correctamente y añade tests.

## Validación y pruebas obligatorias

- Validar que spec se genera desde un checkout limpio.
- Probar endpoints críticos contra sus response models.
- Comparar inventario de endpoints vs `paths` OpenAPI.
- Comprobar que ningún secret/example sensible aparece en el schema.
- Ejecutar generación Orval en dry-run/branch para confirmar que nombres/tipos son utilizables.

## Rollback

Mantener endpoints actuales y revertir cambios de schema/annotations que rompieron consumidores. Como OpenAPI debe describir comportamiento real, nunca “rollback” ocultando de la spec un endpoint que sigue existiendo.

## Anti-slop: errores que Codex NO debe cometer

- OpenAPI manual que diverge del backend.
- Response schemas `object`/`additionalProperties: true` para evitar tipar.
- Exponer modelos internos o secretos.
- Operation IDs inestables que regeneran medio frontend.
- Hacer breaking changes silenciosos.
- Generar spec desde prod con datos/config dependientes del entorno.

## Nota de versión

La especificación OpenAPI publica ramas 3.0/3.1/3.2. No fuerces la “más nueva” si el framework/codegen actual no la soporta bien. FastAPI documenta generación 3.1.0 por defecto en su flujo actual; compatibilidad real > perseguir número de versión.

## Documentación oficial investigada

Investigación preparada el **2026-09-12**. Antes de ejecutar, Codex debe comprobar que las páginas siguen vigentes y respetar la versión realmente instalada en el repositorio.

- https://spec.openapis.org/oas/
- https://fastapi.tiangolo.com/tutorial/body/
- https://fastapi.tiangolo.com/tutorial/response-model/
- https://fastapi.tiangolo.com/how-to/extending-openapi/


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
