# PostHog — analytics, replay y feature flags con privacidad

**Prioridad:** MEDIA  
**Cuándo ejecutarlo:** Cuando journeys estén estables y exista una pregunta de producto/rollout concreta.

## Objetivo para Viru

Observar qué usa la gente, reproducir problemas y usar feature flags para rollouts reversibles. Instrumentar un esquema de eventos pequeño y gobernado; no enviar PII o contenido sensible por defecto. Self-hosting es posible, pero la documentación actual lo declara unsupported en garantías y sin tagged releases normales, por lo que Cloud suele reducir carga operativa.


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

- Identifica jurisdicción/privacidad aplicable y política de consentimiento.
- Inventaria PII potencial en URLs, query params, inputs, DOM, logs y propiedades de eventos.
- Define 5–15 eventos de producto realmente útiles; no autocapturar como sustituto de pensar.
- Decide Cloud region/self-host basándote en necesidad, no ideología OSS.

## Plan de implementación

1. Instala SDK recomendado para framework actual siguiendo docs vigentes.
2. Separa public project key de secretos server-side.
3. Configura identity solo tras login; define reset/logout para evitar mezclar usuarios en dispositivo compartido.
4. Diseña naming estable (`search_started`, `search_completed`, `watchlist_created`, etc.) y propiedades limitadas/controladas.
5. Para Session Replay, empieza con masking fuerte. Revisa inputs, texto, network/console capture antes de activar más detalle.
6. Excluye tokens, emails/identificadores innecesarios, búsquedas sensibles y payloads de proveedores si no son necesarios.
7. Introduce feature flags primero como kill switches/canary de migraciones arriesgadas. Mantén defaults seguros si PostHog no responde.
8. Cada flag debe tener owner, propósito y condición/fecha de limpieza. Flag debt es deuda real.
9. No acoples lógica crítica irreversible a analytics delivery; fallos de PostHog no deben romper Viru.
10. Define dashboards/funnels concretos después de verificar que los eventos llegan con cardinalidad razonable.

## Validación y pruebas obligatorias

- Verificar eventos en dev/test project separado.
- Probar login/logout identity.
- Inspeccionar replay real buscando PII antes de producción.
- Probar app con PostHog bloqueado/offline.
- Feature flag kill switch funciona y conserva UX segura.
- Playwright puede desactivar tracking o usar proyecto test para no contaminar analytics.

## Rollback

Desactivar SDK/feature por env flag. Feature flags críticas deben tener fallback local seguro. No dependas de borrar datos como rollback técnico inmediato; conoce retención/privacy tooling antes de habilitar captura.

## Anti-slop: errores que Codex NO debe cometer

- `capture` en cada click sin taxonomía.
- Mandar objetos enteros de usuario/booking/search.
- Replay sin masking review.
- Poner secret server key en bundle.
- Feature flags eternas.
- Self-host PostHog sin asumir mantenimiento continuo; la documentación actual señala self-host como responsabilidad propia y sin releases versionadas tradicionales.



## Documentación oficial investigada

Investigación preparada el **2026-09-12**. Antes de ejecutar, Codex debe comprobar que las páginas siguen vigentes y respetar la versión realmente instalada en el repositorio.

- https://posthog.com/docs/product-analytics
- https://posthog.com/docs/session-replay
- https://posthog.com/docs/feature-flags
- https://posthog.com/docs/self-host


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
