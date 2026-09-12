# OpenTelemetry — tracing/métricas vendor-neutral

**Prioridad:** MEDIA/ALTA en backend  
**Cuándo ejecutarlo:** Después de estabilizar API; antes de optimizaciones distribuidas.

## Objetivo para Viru

Poder seguir una búsqueda de Viru a través de API, providers, DB y workers con trace IDs y latencias. OpenTelemetry JavaScript y Python tienen traces/metrics estables; la documentación actual marca logs como development y browser instrumentation JS como experimental, así que prioriza backend.


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

- Detecta lenguaje backend y framework.
- Inventaria logger/APM existente para no duplicar spans.
- Identifica límites: HTTP inbound, provider calls, DB, scraping, jobs, queues.
- Decide backend de visualización existente o local; OTel no es por sí mismo una UI.

## Plan de implementación

1. Empieza con backend. Instala API/SDK e instrumentación oficial/contrib compatible.
2. Define `service.name`, environment y versión de servicio con baja cardinalidad.
3. Preferir auto-instrumentation para HTTP/framework/DB; añade spans manuales solo alrededor de operaciones de dominio que realmente ayudan (`search.providers`, `pricing.rank`, `watchlist.refresh`).
4. Propaga contexto a workers/requests cuando el protocolo lo soporte.
5. Nunca pongas URL completa con tokens, payloads, emails ni IDs de alta sensibilidad en atributos.
6. Sigue semantic conventions actuales; no inventes nombres que compitan con convenciones HTTP/DB.
7. Configura sampling conscientemente; 100% puede ser correcto en dev y caro en prod.
8. Preferencia producción: export OTLP a Collector para batching/retries/filtering. La documentación recomienda Collector en general, aunque direct export es válido para empezar.
9. Añade processors para redacción y límites de cardinalidad/atributos.
10. Frontend/browser tracing solo después y como experimento aislado, porque la documentación JS actual lo marca experimental.

## Validación y pruebas obligatorias

- Un request de búsqueda produce trace coherente con spans provider/DB relevantes.
- Fallo de proveedor queda marcado sin exponer payload sensible.
- App sigue funcionando si collector/backend está caído.
- Medir overhead con y sin instrumentation.
- Validar cardinalidad: no usar destination/user/search IDs como metric labels si explotan series.
- Cross-service trace propagation si hay workers separados.

## Rollback

Desactivar exporters/instrumentation por configuración y mantener app operativa. Eliminar spans manuales no debe cambiar lógica de negocio. Si Collector falla, SDK debe estar configurado para no bloquear requests.

## Anti-slop: errores que Codex NO debe cometer

- Convertir cada función en span.
- Labels de alta cardinalidad.
- Export síncrono en request path.
- Instrumentar browser como primera etapa pese a status experimental.
- Logs/traces con secretos.
- Usar atributos custom donde existe semantic convention oficial.
- Añadir OTel además de APM existente sin plan de deduplicación.



## Documentación oficial investigada

Investigación preparada el **2026-09-12**. Antes de ejecutar, Codex debe comprobar que las páginas siguen vigentes y respetar la versión realmente instalada en el repositorio.

- https://opentelemetry.io/docs/languages/python/
- https://opentelemetry.io/docs/languages/python/instrumentation/
- https://opentelemetry.io/docs/languages/js/
- https://opentelemetry.io/docs/languages/js/getting-started/browser/
- https://opentelemetry.io/docs/collector/
- https://opentelemetry.io/docs/collector/quick-start/
- https://opentelemetry.io/docs/specs/semconv/http/
- https://opentelemetry.io/docs/specs/semconv/db/


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
