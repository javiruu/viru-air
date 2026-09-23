# Auditoria Fase 21 - Cache Quick Search V2.1 e historico de precios

**Estado:** vivo  
**Fecha:** 2026-06-14  
**Fuente de verdad:** no; informe operativo para Fase 21 del roadmap Fare Memory  
**Area:** backend / quick-search / watchlist / pricing intelligence

## Objetivo

Auditar la cache compartida existente y el historico real antes de construir Viru Fare Memory, sin duplicar tablas ni semanticas.

## Archivos leidos

- `docs/prompts/codex-travel-roadmap-v2-fare-memory.md`
- `docs/reference/backend/quick-search-contract.md`
- `docs/plans/2026-06-10-quick-search-shared-cache-implementation.md`
- `docs/plans/2026-06-10-quick-search-shared-cache-review-plan.md`
- `backend/app/infrastructure/db/models.py`
- `backend/app/services/quick_search_cache_service.py`
- `backend/app/services/quick_search_execution.py`
- `backend/app/api/v1/search.py`
- `backend/app/api/v1/watchlist.py`
- `backend/tests/unit/test_quick_search_cache_models.py`
- `backend/tests/unit/test_quick_search_shared_cache.py`
- `backend/tests/unit/test_quick_search_execution.py`
- `backend/tests/unit/test_quick_search_e2e_regression.py`

## Respuestas directas a la Fase 21

### Que existe ya

- La cache compartida persistente de Quick Search ya existe en BD como `QuickSearchCacheEntry`.
- La cache guarda `payload_json` completo del resultado de provider por unidad exacta, `warnings_json`, `status`, `ttl_seconds`, `expires_at_utc`, `captured_at_utc`, `last_accessed_at_utc`, `source_hash` y latencia.
- Hay TTL real y configurado por categoria en `quick_search_cache_service.py`:
  - `ready`: 24h
  - `empty`: 2h
  - `degraded`: 30 min
- Hay capa L1 en memoria (`_CACHE`, 300s) y capa L2 persistente en BD.
- Hay reuse cross-user real para Quick Search y para refresh de Watchlist.

### Que no existe todavia

- No existe una cache de oferta separada de la cache de busqueda exacta.
- No existe una tabla de observaciones de precio por oferta.
- No existe negative cache dedicada con taxonomia (`no_route`, `provider_timeout`, `rate_limited`, etc.).
- No existe contrato de frescura canonicamente modelado por resultado de vuelo.
- El historico de precios actual sigue atado a `PriceSnapshot` por `watch_id`, no a una identidad de oferta reutilizable entre busquedas.

### Diferencias importantes detectadas

- Quick Search cachea por unidad exacta `(origin, destination, date, provider, source_hash)`, no por fingerprint global de busqueda.
- Watchlist historiza un solo vuelo canonico seleccionado en cada refresh; no conserva varias observaciones por oferta ni delta estructurado.
- `empty` y `degraded` ya diferencian parcialmente ausencia de vuelos frente a problemas del provider, pero esa semantica sigue siendo insuficiente para Fare Memory porque no distingue causas negativas mas finas.

## Inventario tecnico

| Pieza | Existe | Archivo | Riesgo | Decision |
|---|---|---|---|---|
| Cache persistente compartida de unidades exactas | Si | `backend/app/infrastructure/db/models.py`, `backend/app/services/quick_search_cache_service.py` | Duplicarla crearia drift y costes innecesarios | Extenderla; no crear una segunda cache paralela |
| Canonicalizacion de unidad exacta | Si | `backend/app/services/quick_search_execution.py` | Hoy solo cubre `origin/destination/date/provider`, no fingerprint de busqueda u oferta | Mantener para L2 actual y anadir fingerprints de Fare Memory aparte |
| TTL real por categoria | Si | `backend/app/services/quick_search_cache_service.py` | TTL fijo por categoria, sin frescura expuesta a UI ni dinamica por antelacion | Reutilizar como base y evolucionar despues a freshness + TTL dinamico |
| Cache negativa dedicada | No | N/A | `empty` mezcla varias causas y no hay `retry_after` por tipo de fallo | Crear negative cache real a partir de Fase 28, no antes |
| Offer cache reutilizable entre busquedas | No | N/A | El historico no reconoce la misma oferta entre busquedas distintas | Introducir fingerprint de oferta antes de modelar tablas nuevas |
| Observaciones de precio por oferta | No | N/A | El precio historico esta acoplado a watchlist y no captura deltas por oferta | Crear modelo aditivo en Fase 29 |
| Historico de watchlist | Si | `backend/app/infrastructure/db/models.py` (`PriceSnapshot`) | Sirve a watchlist pero no a Fare Memory global | Conservarlo y no migrarlo aun |
| Integracion cache con watchlist refresh | Si | `backend/app/api/v1/watchlist.py` | Reutiliza cache exacta, pero solo genera snapshot canonico o `no_flights` | Mantener y ampliar luego con observaciones |
| Contrato backend de Quick Search | Si | `docs/reference/backend/quick-search-contract.md` | Hoy documenta cache V2.1 pero no semantica de frescura por resultado | Ampliar contrato, no reescribirlo |
| Tests de cache compartida | Si | `backend/tests/unit/test_quick_search_cache_models.py`, `test_quick_search_shared_cache.py`, `test_quick_search_execution.py` | No cubren fingerprints Fare Memory ni contrato de frescura | Anadir tests focalizados en Fases 23-25 |

## Estado del plan de revision del 2026-06-10

`docs/plans/2026-06-10-quick-search-shared-cache-review-plan.md` sigue siendo util como checklist de auditoria profunda, pero no aparece cerrado como informe ejecutado. El codigo ya refleja varias de sus preocupaciones:

- acceso thread-safe a BD con `_DB_LOCK`;
- callables L2 que crean `SessionLocal()` por hilo en `search.py`;
- pruning async para no bloquear respuesta;
- hash de fuente que ya incluye `currency`.

Lo que sigue faltando no es otra auditoria del mismo feature, sino el salto conceptual de Fare Memory:

- frescura por resultado;
- fingerprints de busqueda y oferta;
- separacion entre identidad de oferta y observacion de precio.

## Gaps reales frente a Viru Fare Memory

1. El sistema sabe cachear resultados exactos, pero aun no sabe nombrar ni reusar la misma oferta entre busquedas.
2. El historico actual sirve a watchlist, no a inteligencia de volatilidad cross-search.
3. La frescura vive implita en `expires_at_utc`, no en un contrato explicito para frontend/API.
4. `empty` y `degraded` son un comienzo de negative cache, pero no sustituyen una negative cache con causas canonicas.

## Decision recomendada para Fases 22-26

1. Fase 22: escribir una spec viva que declare a `QuickSearchCacheEntry` como base existente y que prohiba una cache duplicada.
2. Fase 23: definir un envelope canonico de frescura sin prometer aun que toda la API lo expone.
3. Fase 24: implementar fingerprint de busqueda sobre request canonica; no usar `query_signature` actual como sustituto.
4. Fase 25: implementar fingerprint de oferta sin meter precio en la identidad.
5. Fase 26: solo despues decidir si se extiende `QuickSearchCacheEntry` o se anaden tablas aditivas de `offer` y `price_observation`.

## Veredicto de Fase 21

- La cache V2.1 existe y es la base correcta.
- El historico actual existe, pero es insuficiente para Fare Memory global.
- El mayor riesgo ahora no es falta de cache; es duplicar semanticas y tablas antes de separar correctamente:
  - busqueda
  - oferta
  - observacion de precio
