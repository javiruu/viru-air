# TypeScript strict — tipos como barrera anti-slop

**Prioridad:** ALTA  
**Cuándo ejecutarlo:** Después de tooling estable; antes de generar clientes y mover server state.

## Objetivo para Viru

Elevar garantías del compilador sin “resolver” errores mediante `any`. `strict` activa una familia de comprobaciones estrictas y puede revelar deuda real; debe adoptarse de forma progresiva si el repo es grande.


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

- Detecta todos los `tsconfig*.json` y referencias/proyectos.
- Ejecuta typecheck actual y guarda número/tipo de errores.
- Cuenta `any`, `unknown`, `@ts-ignore`, `@ts-expect-error`, non-null assertions y JS con `checkJs` si aplica.
- Identifica generated code que no debe corregirse a mano.

## Plan de implementación

1. Si `strict` ya está activo, no hagas churn: audita excepciones y termina.
2. Si está desactivado, crea una estrategia incremental. Preferencia: habilitar `strict` y corregir por dominio; si el volumen bloquea, usa configs de transición explícitas con fecha de retirada, no silencios globales sin tracking.
3. Prioriza boundaries: API types, domain models, auth, persistence, money/prices/dates y workers.
4. Sustituye `any` por tipos reales o `unknown` + narrowing. No uses casts para saltarte validación runtime.
5. Mantén separado el concepto: TypeScript verifica compile-time; Zod/response models verifican datos externos runtime.
6. Añade script `typecheck` que no emita artefactos y CI gate.
7. Al introducir Orval/Supabase types, importa tipos generados en lugar de duplicarlos manualmente.
8. Usa `@ts-expect-error` solo para casos intencionados y acompáñalo de motivo/test. `@ts-ignore` nuevo queda prohibido salvo excepción documentada.
9. Corrige nullability según dominio; no multipliques `!`.
10. Documenta en ADR cualquier flag strict que deba permanecer desactivado temporalmente.

## Validación y pruebas obligatorias

- Typecheck limpio o deuda preexistente cuantificada y no incrementada.
- Tests tras correcciones de nullability/casts.
- Grep/lint para evitar nuevos `@ts-ignore` y crecimiento de `any`.
- Validar generated types tras regeneración.

## Rollback

Revertir flags strict específicos y commits de corrección si una incompatibilidad real bloquea release, conservando issue/ADR para reintroducción. No resolver rollback metiendo `any` masivamente.

## Anti-slop: errores que Codex NO debe cometer

- “Arreglar” 300 errores con `as any`.
- Modelar respuestas externas como tipos confiables sin validación runtime.
- Duplicar tipos de OpenAPI/Supabase a mano.
- Activar todos los flags en una PR inmanejable cuando el repo necesita transición.
- Añadir non-null assertions en lugar de corregir invariantes.



## Documentación oficial investigada

Investigación preparada el **2026-09-12**. Antes de ejecutar, Codex debe comprobar que las páginas siguen vigentes y respetar la versión realmente instalada en el repositorio.

- https://www.typescriptlang.org/tsconfig/strict
- https://www.typescriptlang.org/tsconfig/


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
