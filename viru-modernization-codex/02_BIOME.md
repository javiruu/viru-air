# Biome — formatter/linter y gate automático

**Prioridad:** CRÍTICA / inmediata  
**Cuándo ejecutarlo:** Después del baseline E2E; antes de refactors grandes.

## Objetivo para Viru

Unificar formatting y gran parte del linting JS/TS para reducir diffs ruidosos y errores triviales generados por agentes. La migración debe preservar reglas importantes que Biome no cubra; no se elimina ESLint a ciegas.


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

- Detecta si existen ESLint, Prettier, Rome/Biome, stylelint u otros linters.
- Lee todas sus configs, plugins, overrides e ignores.
- Identifica reglas con significado de seguridad/React/framework que no tengan equivalente.
- Determina si el repo es monorepo y dónde debe vivir la config raíz.

## Plan de implementación

1. Añade `@biomejs/biome` como dev dependency en la versión compatible elegida.
2. Genera/configura `biome.json` o `biome.jsonc`, con `$schema` correspondiente a la versión instalada.
3. Si hay ESLint/Prettier, ejecuta primero migraciones en rama y REVISA el resultado: `biome migrate eslint --write` y `biome migrate prettier --write`. Considera `--include-inspired` solo tras revisar equivalencias.
4. Activa integración VCS/ignores para no procesar generated/vendor/build.
5. Ejecuta Biome sin `--write` para obtener inventario. Separa fixes mecánicos de cambios semánticos.
6. Aplica formatting en commit dedicado. Después corrige lint violations por categorías.
7. Mantén ESLint temporalmente si existen plugins/reglas imprescindibles no cubiertos. Documenta qué queda y por qué.
8. Añade scripts estables (`format`, `lint`, `check` según convenciones actuales) y CI en modo check, nunca autofix sobre main.
9. Excluye explícitamente output generado (Orval, builds, coverage) si corresponde.
10. Solo retira Prettier/ESLint y configs cuando la matriz de reglas demuestre paridad suficiente.

## Validación y pruebas obligatorias

- `biome check` verde en source relevante.
- Build y tests idénticos tras commit de formatting.
- Revisar diff para asegurar que no se reformatearon blobs/generated irrelevantes.
- Comparar warnings/errors clave antes/después de retirar ESLint.
- Verificar editor/CI usan la misma versión fijada por lockfile.

## Rollback

Reinstaurar configs y scripts previos desde git. Como formatting puede producir un diff enorme, mantenerlo en commit aislado permite revertir sin tocar lógica.

## Anti-slop: errores que Codex NO debe cometer

- Borrar ESLint porque “Biome lo reemplaza todo”.
- Ignorar reglas de framework/a11y/security no migradas.
- Mezclar formatting masivo con un refactor funcional.
- Usar nursery rules agresivas sin discusión.
- Cambiar estilo de imports/generated causando conflictos permanentes.
- Tener CI y editor con versiones diferentes.



## Documentación oficial investigada

Investigación preparada el **2026-09-12**. Antes de ejecutar, Codex debe comprobar que las páginas siguen vigentes y respetar la versión realmente instalada en el repositorio.

- https://biomejs.dev/guides/migrate-eslint-prettier/
- https://biomejs.dev/reference/cli/
- https://biomejs.dev/reference/configuration/


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
