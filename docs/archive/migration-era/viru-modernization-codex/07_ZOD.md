# Zod — validación runtime en fronteras no confiables

**Prioridad:** ALTA  
**Cuándo ejecutarlo:** Después de tipos/contratos; introducir por boundary, no en cada función interna.

## Objetivo para Viru

Impedir que payloads externos, env vars, query params o storage entren en el dominio solo porque TypeScript “dice” que tienen cierta forma. Zod 4 es estable; la documentación actual marca Zod 4.6 disponible, por lo que hay que revisar breaking changes si el repo usa Zod 3.


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

- Detecta si ya hay Zod, Yup, Valibot, Joi, Pydantic-only validation u otra librería.
- Clasifica boundaries realmente no confiables: providers/scrapers, browser storage, forms complejos, env, webhooks, respuestas no cubiertas por Orval runtime validation.
- Busca casts `as SomeType` inmediatamente después de JSON parse/fetch.

## Plan de implementación

1. Si existe otra librería de validación funcionando, no metas Zod automáticamente: documenta por qué reemplazarla merece la pena.
2. Instala versión compatible; si hay Zod 3, lee guía de migración a 4 antes de cambiar APIs.
3. Define schemas junto al boundary, no un megafichero `schemas.ts` universal.
4. Para datos externos usa `safeParse` cuando el error forme parte del flujo esperado; `parse` cuando una violación sea excepcional y esté manejada.
5. Normaliza proveedor → modelo interno mediante schema/transform donde sea claro. Conserva raw payload solo si realmente hace falta para debugging y con redacción de PII.
6. Deriva tipos con `z.infer`; no declares interface duplicada.
7. Para env, falla temprano en startup con mensajes claros y sin imprimir secretos.
8. Si Orval genera schemas Zod y runtime validation, reutilízalos para la frontera API; no dupliques schemas manuales.
9. Añade fixtures malformed: missing fields, null, tipos erróneos, valores extremos, fechas inválidas.
10. Compilación AOT de Zod 4.6 solo si profiling muestra coste; no optimizar antes de medir.

## Validación y pruebas obligatorias

- Tests unitarios por schema crítico, incluyendo inválidos.
- Fuzz/property tests opcionales para parsers de proveedores particularmente frágiles.
- Playwright asegura que un payload inválido produce error UX controlado, no pantalla rota.
- Confirmar que logs de validation errors no incluyen tokens/PII innecesaria.

## Rollback

Mantener parser anterior detrás de un adapter temporal si un proveedor cambia inesperadamente. Revertir boundary concreto, no retirar Zod de todo el proyecto.

## Anti-slop: errores que Codex NO debe cometer

- Validar objetos internos ya confiables en cada capa.
- `catch(() => originalData as Type)` anulando la validación.
- Coerción indiscriminada que convierte basura en datos aparentemente válidos.
- Schemas duplicados de OpenAPI/Supabase.
- Logs enormes con payloads sensibles.
- Migrar Zod major version sin leer changelog.



## Documentación oficial investigada

Investigación preparada el **2026-09-12**. Antes de ejecutar, Codex debe comprobar que las páginas siguen vigentes y respetar la versión realmente instalada en el repositorio.

- https://zod.dev/
- https://zod.dev/basics
- https://zod.dev/v4/changelog
- https://zod.dev/api
- https://zod.dev/compile


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
