# Playwright — baseline E2E y agentes de test

**Prioridad:** CRÍTICA / primera tecnología  
**Cuándo ejecutarlo:** Antes de cualquier migración estructural.

## Objetivo para Viru

Crear una red de seguridad que capture el comportamiento real de Viru antes de refactorizar. Los tests deben comprobar resultados visibles y contratos de usuario, no detalles internos frágiles. Playwright dispone de planner/generator/healer para loops agentic y de Trace Viewer para diagnosticar fallos.


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

- Detecta framework y comando real para arrancar frontend/backend en test.
- Localiza tests E2E existentes y evita crear una segunda suite paralela.
- Detecta auth: decide fixtures/usuarios de prueba sin usar credenciales personales.
- Lista flujos críticos a partir de `00_BACKEND_AUDIT.md`.
- Identifica datos externos inestables. Decide qué debe mockearse, qué debe usar sandbox y qué merece un smoke real.

## Plan de implementación

1. Instala `@playwright/test` usando el package manager ya existente.
2. Inicializa configuración conservando estructura existente. Define `baseURL`, `webServer` y proyectos solo necesarios. Empieza por Chromium si eso reduce flaky; amplía a WebKit/Firefox después.
3. Configura `trace: "on-first-retry"` en CI, screenshots/video con política razonable y retries solo en CI. Un retry no debe convertir un bug determinista en verde.
4. Crea fixtures para estado/auth. Nunca dependas del orden entre tests.
5. Usa locators accesibles (`getByRole`, labels, test ids solo cuando sea necesario) y web-first assertions. Prohibidos sleeps arbitrarios salvo justificación.
6. Cubre primero happy path y luego fallos: búsqueda, cambios de fechas, ida/vuelta, resultados, watchlist, paginación, persistencia relevante, responsive y errores del backend.
7. Si APIs externas hacen los tests no deterministas, introduce un boundary mock explícito; conserva al menos smoke tests controlados para verificar integración.
8. Integra en CI con instalación reproducible de browsers/deps. Para estabilidad inicial, la documentación oficial recomienda 1 worker en CI; subir paralelismo solo tras medir aislamiento.
9. Ejecuta `npx playwright init-agents --loop=codex` solo si encaja con el flujo de Codex usado en el repo. Versiona las definiciones generadas y regenéralas al actualizar Playwright.
10. Guarda planes humanos en `specs/` si usas agents. El test es la autoridad; el healer no puede “arreglar” expectativas para esconder una regresión real.

## Validación y pruebas obligatorias

- Baseline E2E verde en máquina limpia/CI.
- Ejecutar cada journey crítico individualmente y suite completa.
- Forzar un fallo de ejemplo y confirmar que trace/report permiten diagnosticarlo.
- Comprobar que no existen waits fijos innecesarios, tests dependientes de orden o credenciales reales.
- Ejecutar viewport móvil representativo y desktop en journeys donde el layout sea crítico.

## Rollback

Eliminar configuración y dependencia Playwright solo si aún no se ha usado para otros gates. Si una migración posterior falla, **no rollback de Playwright**: se revierte la migración que rompió el comportamiento.

## Anti-slop: errores que Codex NO debe cometer

- Tests que solo comprueban “la página carga”.
- Selectores CSS frágiles copiados del DOM actual.
- `waitForTimeout(5000)` para ocultar race conditions.
- Mocks de absolutamente todo que hagan imposible detectar integración rota.
- Test data compartida mutable.
- Hacer que healer cambie el test hasta que pase sin comprobar si cambió el producto.
- Activar tres browsers + paralelismo masivo desde el día 1 y generar flakiness.



## Documentación oficial investigada

Investigación preparada el **2026-09-12**. Antes de ejecutar, Codex debe comprobar que las páginas siguen vigentes y respetar la versión realmente instalada en el repositorio.

- https://playwright.dev/docs/test-agents
- https://playwright.dev/docs/trace-viewer
- https://playwright.dev/docs/ci
- https://playwright.dev/docs/best-practices


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
