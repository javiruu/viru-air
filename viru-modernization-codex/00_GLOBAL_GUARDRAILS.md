# Guardrails globales de migración

## 1. No adivinar el stack

Codex debe inspeccionar el repositorio y registrar: lenguaje(s), frameworks, package manager, runtime, backend entrypoint, frontend entrypoint, DB real, ORM/driver, sistema de auth, sistema de jobs, caché, CI, despliegue, observabilidad, tests, variables de entorno y servicios externos.

## 2. No introducir una segunda arquitectura permanente

Los adapters temporales durante una migración son válidos. Lo que no es válido es terminar con `OldWatchlistService`, `WatchlistServiceV2`, `SupabaseWatchlistRepository` y `WatchlistManager` resolviendo lo mismo. Cada puente temporal debe tener owner, motivo y condición de retirada.

## 3. Source of truth explícito

Para cada dominio indica exactamente cuál es la fuente de verdad: DB, API, cache, proveedor externo o frontend. Nunca hagas dual-write sin estrategia de reconciliación, métricas y rollback.

## 4. Migraciones de datos

Antes de cualquier migración destructiva:
- backup/restorable snapshot;
- conteos y checksums o validaciones equivalentes;
- script de backfill idempotente;
- dry-run cuando sea viable;
- estrategia expand/contract para cambios incompatibles;
- no `DROP COLUMN`, `DROP TABLE` o cambio destructivo hasta haber retirado lectores/escritores antiguos;
- transacciones donde sean seguras;
- cuidado con locks en tablas grandes;
- verificar tiempos de migración sobre una copia de datos representativa.

## 5. Seguridad

Nunca confíes en el frontend para autorización. Las claves privilegiadas son server-only. Valida input no confiable en los límites. Para Supabase, RLS no es opcional en tablas expuestas. Para Typesense, nunca expongas una key administrativa al navegador. Para Valkey, nunca lo expongas directamente a Internet.

## 6. Generated code

Directorios generados deben llevar comentario/README indicando generador y comando. No editar manualmente output de Orval o tipos generados de Supabase salvo que la herramienta lo contemple explícitamente. Si hace falta personalizar, usa mutators/adapters configurados fuera del output.

## 7. Observabilidad antes de optimizar

No añadas Valkey, colas, índices de búsqueda o complejidad distribuida sin evidencia. Mide p50/p95/p99 o métricas equivalentes, volumen, frecuencia de llamadas, hit-rate esperado y coste operativo.

## 8. Dependency hygiene

Antes de instalar una dependencia:
- comprobar si ya existe una equivalente;
- evitar dos librerías para el mismo cometido;
- pin coherente con lockfile;
- leer breaking changes de la versión elegida;
- verificar licencia y mantenimiento;
- no ejecutar automáticamente scripts desconocidos de registries de terceros.

## 9. CI como autoridad

Los gates deben estar automatizados. Un agente no puede declarar una etapa terminada solo porque ejecutó un comando local una vez.

## 10. Prohibiciones

- No reescribir el proyecto “para limpiarlo”.
- No convertir a monorepo o cambiar bundler salvo necesidad documentada.
- No migrar a React solo por shadcn/ui.
- No reemplazar una DB funcional por Supabase en una única PR.
- No introducir Temporal si Trigger.dev o workers actuales resuelven el problema.
- No usar `drizzle-kit push` contra producción como sustituto de migraciones revisables.
- No usar `any`, `@ts-ignore`, catches vacíos o retries infinitos para “hacer pasar” los gates.
