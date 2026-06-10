# Quick Search Shared Cache Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** implementar una cache compartida y persistente para `quick-search` que reutilice resultados de tracking de vuelos entre usuarios durante 24 horas, recomponga busquedas ampliadas (`nearby` + `flex`) desde unidades exactas cacheadas y reduzca llamadas innecesarias a providers.

**Architecture:** la fuente de verdad sera una cache persistente en base de datos para unidades exactas `origin_iata + destination_iata + travel_date + provider`. La respuesta final de `quick-search` no se cacheara como payload bruto canonico, sino que se reconstruira desde esas unidades exactas, permitiendo reutilizacion cross-user, control por TTL y evolucion futura hacia una capa caliente en Redis sin rehacer el contrato principal.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, SQLite/DB actual del repo, servicios `quick_search_*`, provider orchestrator, tests unitarios e integracion del backend.

---

**Estado:** completado ✅  
**Fecha:** 2026-06-10  
**Fecha de cierre:** 2026-06-10  
**Commits:** 5f10a25, 0113e4d, 148cd0c, dbb5de4, dc1aaf3, 37ddc00  
**Autor:** Codex  
**Area:** plan  
**Fuente de verdad:** no; plan operativo de implementacion apoyado en codigo, docs vivas y estado real del backend

## Resumen ejecutivo

Hoy `quick-search` ya reutiliza parcialmente resultados, pero solo con una cache en memoria, de TTL corto y sin persistencia:

- la cache actual vive en [backend/app/services/quick_search_execution.py](C:/Users/javiru/Desktop/viru-tracker/backend/app/services/quick_search_execution.py)
- usa una clave minima `(origin_iata, destination_iata, travel_date)`
- tiene TTL de `300s`
- no sobrevive reinicios
- no es una base fiable para reutilizacion cross-user a 24h

El objetivo de este plan es sustituir esa limitacion por una arquitectura multicapa pero aterrizada:

1. cache persistente compartida en BD como fuente de verdad
2. recomposicion de busquedas amplias desde unidades exactas
3. observabilidad y controles de expiracion
4. evolucion posterior a Redis como optimizacion, no como requisito inicial

## Decisiones cerradas para este plan

- La cache compartida se reutiliza tanto para busquedas exactas como para busquedas ampliadas con `nearby` y `flex`.
- La primera implementacion persistente usa la base de datos actual como fuente de verdad.
- Los resultados con vuelos se cachean `24h`.
- Los resultados vacios se cachean `2h`.
- Las degradaciones o errores parciales de provider se cachean `15-30 min`; para la primera version se recomienda `30 min`.
- La unidad canonica de reutilizacion es `origin + destination + date`, no el payload entero del usuario.
- La respuesta final del endpoint se recompone desde unidades exactas y filtros efectivos.

## Objetivo funcional exacto

Caso de negocio principal:

- si la maquina ya ha trackeado `AGP -> TSF` para `2026-03-11` y otro usuario pregunta despues por esa misma unidad exacta, el sistema debe reutilizar el resultado fresco sin volver a pegar al provider
- si un usuario lanza una busqueda ampliada con `nearby` o `flex`, el backend debe resolver cada unidad exacta, leer de cache lo que ya exista y solo llamar a provider para las piezas faltantes o expiradas
- watchlist y quick-search deben poder apoyarse en la misma capa compartida cuando consulten la misma unidad exacta

## Alcance incluido

- cache persistente compartida de quick-search
- TTL por tipo de resultado
- canonicalizacion y firma de unidades
- bloqueo anti-duplicacion concurrente
- observabilidad y metricas basicas
- integracion con quick-search y refresh de watchlist
- actualizacion de contratos y runbooks si cambian envs o semantica operativa

## Alcance excluido de esta iteracion

- Redis obligatorio desde el primer despliegue
- invalidacion manual avanzada por panel admin
- precalculo masivo de rutas futuras
- cache distribuida multi-region
- optimizacion economica avanzada por proveedor o tarifa de mercado
- cambios de UX grandes en frontend fuera de indicadores de cache/frescura si hicieran falta

## Fase 1. Baseline tecnico y contrato de cache compartida

**Objetivo:** congelar la semantica del sistema antes de tocar codigo para que la implementacion no derive en caches incompatibles entre quick-search y watchlist.

**Files:**
- Read: `docs/reference/backend/quick-search-contract.md`
- Read: `backend/app/api/v1/search.py`
- Read: `backend/app/services/quick_search_execution.py`
- Read: `backend/app/api/v1/watchlist.py`
- Output doc delta if needed: `docs/reference/backend/quick-search-contract.md`

**Implementation focus:**
- documentar internamente la diferencia entre:
  - unidad exacta cacheable
  - respuesta final recompuesta
  - snapshots de watchlist
- fijar TTL por categoria de resultado
- fijar que la cache compartida es cross-user pero no almacena identidad de usuario

**Verify:**
- checklist de decisiones cerradas incorporada a este plan
- no quedan dudas sobre si la cache vive por ruta exacta o por payload total

## Fase 2. Canonicalizacion de claves y firma estable de consulta

**Objetivo:** evitar misses artificiales cuando dos peticiones equivalentes cambian orden, formato o combinacion de payload.

**Files:**
- Modify: `backend/app/services/quick_search_execution.py`
- Modify: `backend/app/api/v1/search.py`
- Test: `backend/tests/unit/test_quick_search_execution.py`
- Test: `backend/tests/integration/test_quick_search_country_scope_multi_seed.py`

**Implementation focus:**
- extraer funciones de canonicalizacion para:
  - `origin_iata`
  - `destination_iata`
  - `travel_date`
  - `provider`
  - categoria de resultado
- diferenciar entre:
  - `unit_cache_key`
  - `query_signature`
- mantener el comportamiento actual de `query_signature` visible al cliente cuando siga aportando valor de observabilidad

**Verify:**
- tests que prueben que dos entradas equivalentes generan la misma clave
- tests que prueben que invertir `origin/destination` sigue cambiando la firma

## Fase 3. Modelo persistente de cache compartida

**Objetivo:** crear la estructura de base de datos que actuara como fuente de verdad de la cache de 24h.

**Files:**
- Modify: `backend/app/infrastructure/db/models.py`
- Create: `backend/alembic/versions/<timestamp>_quick_search_shared_cache.py`
- Test: `backend/tests/unit/test_quick_search_cache_models.py`

**Implementation focus:**
- crear una tabla tipo `quick_search_cache_entry`
- campos recomendados:
  - `id`
  - `origin_iata`
  - `destination_iata`
  - `travel_date`
  - `provider`
  - `status` (`ready|empty|degraded|pending|error`)
  - `ttl_seconds`
  - `expires_at_utc`
  - `captured_at_utc`
  - `last_accessed_at_utc`
  - `payload_json`
  - `warnings_json`
  - `source_hash`
  - `provider_latency_ms`
- unique key recomendada:
  - `(origin_iata, destination_iata, travel_date, provider, source_hash)`

**Verify:**
- migracion aplica correctamente
- constraints e indices permiten buscar rapido por unidad exacta y expiracion

## Fase 4. Repositorio/servicio de cache persistente

**Objetivo:** encapsular el acceso a la tabla para no mezclar SQL y logica de negocio en el endpoint.

**Files:**
- Create: `backend/app/services/quick_search_cache_service.py`
- Modify: `backend/app/services/__init__.py` if needed
- Test: `backend/tests/unit/test_quick_search_cache_service.py`

**Implementation focus:**
- operaciones minimas:
  - `get_fresh_entry`
  - `set_ready_entry`
  - `set_empty_entry`
  - `set_degraded_entry`
  - `mark_pending`
  - `touch_last_accessed`
  - `delete_expired` or `prune_expired`
- separar TTL por categoria:
  - `ready = 86400`
  - `empty = 7200`
  - `degraded = 1800`

**Verify:**
- tests de hit fresco
- tests de expiracion
- tests de categoria y TTL correctos

## Fase 5. Adaptador de serializacion de resultados de provider

**Objetivo:** persistir resultados sin acoplar la BD al shape interno de Python de forma fragil.

**Files:**
- Modify: `backend/app/domain/entities.py`
- Modify: `backend/app/services/quick_search_cache_service.py`
- Test: `backend/tests/unit/test_quick_search_cache_serialization.py`

**Implementation focus:**
- definir serializacion segura de `ProviderFlight` y `ProviderFetchResult`
- preservar:
  - precio
  - moneda
  - hora local de salida
  - `captured_at`
  - `source`
  - warnings estructurados si existen
- garantizar reconstruccion fiel del objeto cacheado para el pipeline de ranking/dedupe

**Verify:**
- roundtrip `ProviderFetchResult -> payload_json -> ProviderFetchResult`
- sin perdida de moneda, source, warnings o horarios

## Fase 6. Integracion read-through/write-through en execution

**Objetivo:** sustituir la cache volatile actual por lectura/escritura contra el nuevo servicio persistente.

**Files:**
- Modify: `backend/app/services/quick_search_execution.py`
- Test: `backend/tests/unit/test_quick_search_execution.py`
- Test: `backend/tests/unit/test_quick_search_e2e_regression.py`

**Implementation focus:**
- mantener temporalmente la cache en memoria actual solo como capa caliente opcional
- antes de llamar a `fetch_flights`, consultar cache persistente
- despues del fetch, persistir el resultado con su categoria y TTL
- devolver `cache_hits` y `cache_misses` reales, no solo de memoria local

**Verify:**
- segunda busqueda identica reutiliza cache persistente
- reiniciar proceso no rompe la reutilizacion si la BD sigue viva

## Fase 7. Reutilizacion para busquedas ampliadas con nearby y flex

**Objetivo:** recomponer resultados amplios desde multiples unidades exactas cacheadas sin duplicar fetches.

**Files:**
- Modify: `backend/app/api/v1/search.py`
- Modify: `backend/app/services/quick_search_execution.py`
- Test: `backend/tests/integration/test_quick_search_country_scope_multi_seed.py`
- Test: `backend/tests/integration/test_quick_search_rescue_flow.py`

**Implementation focus:**
- cada combinacion O-D-fecha del execution plan debe resolverse de forma independiente
- nearby y flex no comparten payload final, comparten unidades base
- el ranking, dedupe y rescue siguen ocurriendo despues de recomponer unidades

**Verify:**
- una segunda busqueda ampliada reutiliza parcialmente piezas ya resueltas
- los `provider_calls` bajan aunque la respuesta final sea distinta

## Fase 8. Anti-stampede y deduplicacion concurrente

**Objetivo:** impedir que varias peticiones simultaneas disparen el mismo tracking exacto a la vez.

**Files:**
- Modify: `backend/app/services/quick_search_cache_service.py`
- Modify: `backend/app/services/quick_search_execution.py`
- Test: `backend/tests/unit/test_quick_search_cache_concurrency.py`

**Implementation focus:**
- usar estado `pending` con timeout corto de trabajo
- si una unidad esta en progreso, otra peticion:
  - espera de forma acotada, o
  - reutiliza el resultado cuando quede `ready`, o
  - cae a fetch controlado solo si el lock expira
- no bloquear indefinidamente el request path

**Verify:**
- dos peticiones concurrentes para la misma unidad hacen una sola llamada efectiva al provider
- no quedan entradas `pending` zombis indefinidas

## Fase 9. Politica de vacios y degradacion

**Objetivo:** no repetir busquedas inutiles cuando no hay vuelos, sin congelar demasiado los fallos de proveedores.

**Files:**
- Modify: `backend/app/services/quick_search_cache_service.py`
- Modify: `backend/app/services/quick_search_execution.py`
- Test: `backend/tests/integration/test_quick_search_provider_degradation.py`
- Test: `backend/tests/unit/test_quick_search_execution.py`

**Implementation focus:**
- resultados con vuelos: `24h`
- resultados vacios: `2h`
- resultados degradados: `30 min`
- si un provider devuelve parcial pero con vuelos validos, guardar como `degraded` reutilizable con semantica explicita

**Verify:**
- empty result no repite fetch inmediato
- degraded result expira antes que un `ready`
- warnings y `provider_status` siguen coherentes

## Fase 10. Integracion con watchlist refresh y snapshots

**Objetivo:** conectar quick-search y watchlist a la misma inteligencia de reutilizacion para unidades exactas.

**Files:**
- Modify: `backend/app/api/v1/watchlist.py`
- Read/Align: `backend/app/services/watchlist_snapshots.py`
- Test: `backend/tests/integration/test_watchlist_flow.py`
- Test: `backend/tests/integration/test_search_alerts_flow.py`

**Implementation focus:**
- `_refresh_watch_now` debe consultar primero la cache compartida exacta si existe y esta fresca
- si la watchlist provoca un fetch real, el resultado debe poblar la cache compartida
- seguir persistiendo `PriceSnapshot` como capa de historico propia del watch

**Verify:**
- refresh de watchlist reutiliza entrada fresca de quick-search
- quick-search posterior reutiliza unidad calentada por watchlist
- snapshots siguen guardandose correctamente

## Fase 11. Configuracion y feature flags de rollout

**Objetivo:** poder activar la nueva capa con seguridad y rollback rapido.

**Files:**
- Modify: `backend/.env.example`
- Modify: `backend/app/api/v1/search.py`
- Modify: `backend/app/api/v1/watchlist.py`
- If needed: `docs/runbooks/runbook-watchlist-quick-search-stabilization.md`

**Implementation focus:**
- envs sugeridas:
  - `QUICK_SEARCH_SHARED_CACHE_ENABLED=true`
  - `QUICK_SEARCH_SHARED_CACHE_READY_TTL_SECONDS=86400`
  - `QUICK_SEARCH_SHARED_CACHE_EMPTY_TTL_SECONDS=7200`
  - `QUICK_SEARCH_SHARED_CACHE_DEGRADED_TTL_SECONDS=1800`
  - `QUICK_SEARCH_SHARED_CACHE_USE_MEMORY_HOT_LAYER=true`
- fallback claro a comportamiento anterior si el flag esta off

**Verify:**
- con flag off el flujo sigue operativo
- con flag on los contadores y persistencia cambian como se espera

## Fase 12. Observabilidad y trazabilidad

**Objetivo:** hacer visible si la cache mejora de verdad el sistema y donde falla.

**Files:**
- Modify: `backend/app/api/v1/search.py`
- Modify: `backend/app/api/v1/admin.py` if metrics are surfaced there
- Test: `backend/tests/unit/test_quick_search_observability.py`

**Implementation focus:**
- ampliar logs estructurados con:
  - `shared_cache_hit_count`
  - `shared_cache_miss_count`
  - `shared_cache_stale_count`
  - `provider_calls_avoided`
  - `cache_status_mix`
- si cabe en contrato sin romper clientes, enriquecer `meta.execution`

**Verify:**
- logs permiten distinguir hit de memoria vs hit persistente
- respuesta debug muestra counters consistentes

## Fase 13. Limpieza y mantenimiento de expirados

**Objetivo:** evitar crecimiento sin control de la tabla de cache.

**Files:**
- Create or Modify: `backend/app/worker/<cache_cleanup_job>.py`
- Modify: `backend/app/main.py` or worker wiring if needed
- Doc: `docs/runbooks/<new_or_existing_runbook>.md`
- Test: `backend/tests/unit/test_quick_search_cache_cleanup.py`

**Implementation focus:**
- definir estrategia de limpieza:
  - opportunistic prune en lectura/escritura ligera
  - sweep periodico opcional por worker o comando
- no bloquear requests con borrados masivos

**Verify:**
- las entradas expiradas se eliminan o dejan de computar como frescas
- el cleanup es idempotente

## Fase 14. QA de regresion y prueba end-to-end

**Objetivo:** demostrar que el nuevo sistema no rompe quick-search, rescue mode ni watchlist.

**Files:**
- Modify/Add tests in:
  - `backend/tests/unit/test_quick_search_execution.py`
  - `backend/tests/unit/test_quick_search_e2e_regression.py`
  - `backend/tests/integration/test_quick_search_provider_degradation.py`
  - `backend/tests/integration/test_quick_search_country_scope_multi_seed.py`
  - `backend/tests/integration/test_watchlist_flow.py`

**Implementation focus:**
- cubrir:
  - exact search reused cross-user
  - nearby/flex partial reuse
  - empty/degraded TTL
  - process restart survivability at DB layer
  - watchlist integration

**Verify:**
- suite objetivo pasa
- pruebas nuevas fallan si se rompe la semantica de cache compartida

## Fase 15. Documentacion final, rollout gradual y fase Redis

**Objetivo:** cerrar la primera version util y dejar preparada la evolucion a una capa caliente adicional.

**Files:**
- Modify: `docs/reference/backend/quick-search-contract.md`
- Modify: `docs/engineering/backend.md`
- Modify: `docs/DOCS_INVENTORY.md`
- Optional: `docs/runbooks/runbook-watchlist-quick-search-stabilization.md`
- Optional future plan link: `docs/plans/`

**Implementation focus:**
- documentar:
  - semantica de cache compartida
  - TTL por categoria
  - flags/env
  - limites conocidos
  - siguiente paso: Redis como hot layer, no como nueva fuente de verdad
- dejar checklist de adopcion para rollout por entorno

**Verify:**
- docs y codigo dicen lo mismo
- existe plan claro para:
  - local
  - staging
  - prod gradual

## Riesgos principales

- confundir cache de unidad exacta con cache de respuesta final y romper filtros
- introducir stale results demasiado agresivos para rutas sensibles
- mezclar logica de watchlist historica con cache operativa compartida
- crear locks `pending` que generen bloqueos o carreras
- crecer demasiado la tabla sin politica clara de limpieza

## Orden de ejecucion recomendado

1. Fases 1-3 para fijar contrato, clave y persistencia
2. Fases 4-6 para habilitar el camino feliz exacto
3. Fases 7-10 para integracion real con nearby/flex/watchlist
4. Fases 11-15 para rollout seguro, observabilidad, limpieza y documentacion

## Criterio de done global

El trabajo se considera realmente terminado cuando:

- una segunda busqueda exacta cross-user reutiliza la unidad cacheada sin nuevo fetch
- una busqueda ampliada reutiliza parcialmente unidades ya resueltas
- watchlist puede aprovechar y poblar la misma cache
- el TTL se comporta distinto para `ready`, `empty` y `degraded`
- hay evidencia de tests y contadores que demuestran reduccion real de llamadas a provider
- la arquitectura queda lista para anadir Redis como optimizacion futura sin redisenar la fuente de verdad

## Comandos de verificacion esperados durante la implementacion

```powershell
cd C:\Users\javiru\Desktop\viru-tracker\backend
pytest tests/unit/test_quick_search_execution.py -v
pytest tests/unit/test_quick_search_e2e_regression.py -v
pytest tests/integration/test_quick_search_provider_degradation.py -v
pytest tests/integration/test_quick_search_country_scope_multi_seed.py -v
pytest tests/integration/test_watchlist_flow.py -v
```

```powershell
cd C:\Users\javiru\Desktop\viru-tracker\backend
python -m alembic upgrade head
```

## Handoff

Plan completo y guardado en `docs/plans/2026-06-10-quick-search-shared-cache-implementation.md`.

La implementacion deberia ejecutarse en fases pequenas, con regresion continua sobre `quick-search` y `watchlist`, evitando mezclar en la misma tanda:

- migracion
- integracion concurrente
- observabilidad
- limpieza

porque ese acoplamiento haria mas dificil detectar donde se rompe la semantica real de cache compartida.
