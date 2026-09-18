# shadcn/ui — componentes UI en código propio

**Prioridad:** MEDIA/ALTA si frontend React  
**Cuándo ejecutarlo:** Después de estabilizar datos; `NOT_APPLICABLE` si Viru no usa React y no hay decisión separada de migrarlo.

## Objetivo para Viru

Estandarizar primitives/components sin convertir la integración en un rediseño masivo. shadcn/ui copia componentes al proyecto: Codex puede leerlos y modificarlos, pero eso también significa que Viru es responsable de mantener esos archivos.


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

- Confirma React y framework/bundler.
- Detecta Tailwind y versión, aliases y estructura monorepo.
- Inventaria componentes UI existentes y design tokens.
- Identifica primitives de accesibilidad ya usadas (Radix/Base/etc.) para no duplicar.

## Plan de implementación

1. Si no hay React, marca NOT_APPLICABLE. No migres framework dentro de esta tarea.
2. Si React/Vite, sigue guía oficial de existing project; conserva alias/style existentes cuando sea posible.
3. Inicializa `components.json` revisándolo antes de aceptar cambios de CSS/tokens.
4. Añade solo componentes necesarios para un slice. Empieza primitives (Button/Dialog/Input/etc.), no bloques gigantes.
5. Crea `components/ui` como primitives y components de dominio fuera de ese directorio.
6. Preserva semántica/accesibilidad y testea teclado/focus en dialogs, menus, comboboxes.
7. No edites una docena de componentes para “hacerlos Viru” si se resuelve con tokens/variants.
8. Para registries de terceros, revisar source/dependencies antes de instalar. La propia documentación oficial recomienda revisar código third-party.
9. Si se usa monorepo, deja al CLI manejar rutas conforme a la guía oficial en vez de copiar manualmente.
10. Puedes instalar skill/MCP oficial para agentes si el entorno Codex lo soporta, pero no es requisito para runtime.

## Validación y pruebas obligatorias

- Visual regression/screenshot para componentes migrados.
- Playwright teclado/focus + móvil/desktop.
- No cambios inesperados de CSS global.
- Bundle/dependency diff revisado.
- Lighthouse/a11y o herramienta equivalente si ya existe.

## Rollback

Revertir slice de componentes al implementation anterior. Como shadcn vive en source, eliminar solo primitives no usados; no desmontar Tailwind/config compartida si otros componentes ya dependen.

## Anti-slop: errores que Codex NO debe cometer

- Migrar todo el diseño en una PR.
- Añadir bloques de registries desconocidos sin revisar código.
- Convertir `components/ui` en componentes de negocio.
- Duplicar Button/Dialog de varias librerías.
- Migrar a React únicamente por shadcn.
- Hardcodear estilos por pantalla en vez de reutilizar tokens/variants.



## Documentación oficial investigada

Investigación preparada el **2026-09-12**. Antes de ejecutar, Codex debe comprobar que las páginas siguen vigentes y respetar la versión realmente instalada en el repositorio.

- https://ui.shadcn.com/docs/installation/vite
- https://ui.shadcn.com/docs/installation/manual
- https://ui.shadcn.com/docs/monorepo
- https://ui.shadcn.com/docs/official
- https://ui.shadcn.com/docs/new


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
