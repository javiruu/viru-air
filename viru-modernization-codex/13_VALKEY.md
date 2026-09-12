# Valkey — cache/locks/ephemeral state

**Prioridad:** OPCIONAL  
**Cuándo ejecutarlo:** Solo después de profiling que demuestre repetición/latencia/coste.

## Objetivo para Viru

Reducir llamadas caras y coordinar workers cuando PostgreSQL/in-memory ya no sea suficiente. Valkey es in-memory y ofrece TTL, eviction, persistence opcional, pub/sub/streams, etc. Para Viru, el primer caso debería ser cache con TTL y/o lock de deduplicación, no convertirse en una segunda base de datos.


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

Decision gate con datos: requests repetidas por clave, coste provider, p95, volumen, tamaño estimado, tolerancia a stale data, necesidad de locks. Si no hay números, DEFER.
Además detecta si Redis/Valkey ya existe indirectamente mediante plataforma/queues.

## Plan de implementación

1. Define para cada key: propósito, formato/version, TTL, máximo tamaño y qué ocurre en cache miss.
2. Usa prefijo versionado (`viru:v1:...`) y hash canonical de parámetros; no uses strings gigantes/raw URLs con tokens.
3. Cache-aside: DB/provider sigue siendo source of truth. Nunca dependas de cache para datos que no pueden reconstruirse.
4. Prevén stampede con lock/dedupe solo si medido; locks necesitan timeout y owner token seguro.
5. Configura `maxmemory` y eviction policy explícita. Para cache puro, persistence puede no ser necesaria; decide conscientemente.
6. Si se usa persistence/Streams, documenta por qué y recovery semantics.
7. Red/seguridad: Valkey no debe exponerse a Internet. Usa private network/firewall, ACL y TLS según despliegue.
8. Clientes con pooling razonable y timeouts. Degradación: si Valkey falla, la app debe poder volver a source of truth donde sea seguro.
9. Instrumenta hit/miss, latency, evictions, memory y errors.
10. Pipelining solo para lotes medidos; la documentación advierte que las respuestas en pipeline consumen memoria, así que batch razonable.

## Validación y pruebas obligatorias

- Unit tests de canonical cache key.
- Cache hit/miss produce mismo resultado semántico.
- TTL/invalidación probados.
- Simular caída de Valkey.
- Load test para demostrar mejora real.
- Verificar no hay secretos/PII en keys/values innecesariamente.
- Monitorizar hit ratio y evictions tras rollout.

## Rollback

Feature flag para bypass cache. En incidente, desviar a source of truth y flush de namespace versionado si hace falta. Nunca hacer `FLUSHALL` en infraestructura compartida como rollback normal.

## Anti-slop: errores que Codex NO debe cometer

- Usarlo como primary DB por accidente.
- TTL infinito para precios dinámicos.
- No configurar maxmemory/eviction.
- Exponer 6379 a Internet.
- Lock sin expiry.
- Cache key incompleta que mezcla usuarios/fechas.
- Añadir Redis y Valkey simultáneamente.



## Documentación oficial investigada

Investigación preparada el **2026-09-12**. Antes de ejecutar, Codex debe comprobar que las páginas siguen vigentes y respetar la versión realmente instalada en el repositorio.

- https://valkey.io/topics/introduction/
- https://valkey.io/topics/persistence/
- https://valkey.io/topics/lru-cache/
- https://valkey.io/topics/security/
- https://valkey.io/topics/acl/
- https://valkey.io/topics/encryption/
- https://valkey.io/topics/pipelining/
- https://valkey.io/topics/streams-intro/


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
