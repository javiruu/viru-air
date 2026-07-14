# Quick-Search Shared Cache — Plan de Revisión Exhaustiva

> **Para la IA revisora:** ejecuta cada fase en orden. Lee los archivos indicados, aplica los checks descritos, ejecuta los comandos de verificación, y reporta hallazgos con evidencia concreta (rutas de archivo, números de línea, outputs de tests).

**Estado:** activo  
**Fecha:** 2026-06-10  
**Objetivo:** auditar la implementación completa de la cache compartida persistente (commits `5f10a25` y `0113e4d`) antes de activarla en producción.

---

## Fase R1. Baseline: leer toda la implementación

**Objetivo:** entender el sistema completo antes de auditar.

**Archivos a leer (en orden):**

1. `docs/plans/2026-06-10-quick-search-shared-cache-implementation.md` — el plan original de 15 fases
2. `docs/reference/backend/quick-search-contract.md` — sección "Shared cache (V2.1)" + "Implementation status"
3. `backend/app/infrastructure/db/models.py` — modelo `QuickSearchCacheEntry`
4. `backend/alembic/versions/0030_add_quick_search_shared_cache.py` — migración
5. `backend/app/services/quick_search_cache_service.py` — servicio de cache (archivo completo)
6. `backend/app/services/quick_search_execution.py` — funciones `build_unit_cache_key`, `build_cache_source_hash`, `classify_cache_result`, `_fetch_with_cache`, `execute_plan`
7. `backend/app/api/v1/search.py` — función `quick_search` (buscar `shared_cache_get`, `shared_cache_set`, `prune_expired_entries`)
8. `backend/app/api/v1/watchlist.py` — función `_refresh_watch_now` (buscar `WATCH_SHARED_CACHE_ENABLED`, `get_fresh_entry`, `set_cache_entry`)
9. `backend/.env.example` — variables `QUICK_SEARCH_SHARED_CACHE_*`
10. `backend/tests/unit/test_quick_search_cache_models.py` — 17 tests
11. `backend/tests/unit/test_quick_search_shared_cache.py` — 13 tests

**Verificación:**
```bash
cd backend && python -m pytest tests/unit/test_quick_search_cache_models.py tests/unit/test_quick_search_shared_cache.py tests/unit/test_quick_search_execution.py -v
```

---

## Fase R2. Auditoría de thread-safety

**Objetivo:** confirmar que no hay race conditions en el acceso concurrente a la cache.

**Checks concretos:**

### R2.1 — `_DB_LOCK` en cache service
- Revisar `quick_search_cache_service.py`: ¿todas las operaciones de escritura/lectura en BD pasan por `_DB_LOCK`?
- Items a verificar:
  - `get_fresh_entry`: ¿el `db.scalar()` y el `db.commit()` están dentro del lock?
  - `set_cache_entry`: ¿el `delete` + `insert` + `commit` están dentro del lock?
  - `prune_expired_entries`: ¿el `delete` + `commit` están dentro del lock?
  - `get_cache_stats`: ¿las queries están dentro del lock?

### R2.2 — `_FETCH_LOCKS` en execution layer
- Revisar `quick_search_execution.py` — bloque anti-stampede:
  - ¿`_FETCH_LOCKS_LOCK` protege correctamente el acceso al dict `_FETCH_LOCKS`?
  - ¿La re-verificación de L1 dentro del `key_lock` está correcta?
  - ¿El cleanup (`del _FETCH_LOCKS[key]`) está dentro de `_FETCH_LOCKS_LOCK`?
  - ¿Hay riesgo de memory leak si una excepción salta antes del cleanup?

### R2.3 — Llamadas a L2 desde múltiples threads
- `_fetch_with_cache` recibe `shared_cache_get` y `shared_cache_set` como callables. Estos callables capturan `db: Session` desde `Depends(get_db)` en `search.py`.
- **Pregunta crítica:** ¿SQLAlchemy Session es thread-safe? Si `_fetch_with_cache` se ejecuta en un `ThreadPoolExecutor`, ¿varios threads pueden llamar a `shared_cache_get`/`shared_cache_set` simultáneamente con la misma sesión `db`?
- Revisar si `get_fresh_entry` y `set_cache_entry` usan `_DB_LOCK` para serializar el acceso. Si `_DB_LOCK` serializa, ¿es suficiente?

### R2.4 — `_CACHE` (L1) thread-safety
- Revisar `_CACHE_LOCK` en `quick_search_execution.py`:
  - ¿Todas las lecturas y escrituras de `_CACHE` pasan por `_CACHE_LOCK`?
  - ¿La entrada en L1 (`_CACHE[key] = (now, fetch_result)`) dentro del `key_lock` también está protegida por `_CACHE_LOCK`?

**Verificación:**
```bash
cd backend && python -m pytest tests/unit/test_quick_search_shared_cache.py -v -k "stampede"
```

---

## Fase R3. Auditoría de seguridad de datos

**Objetivo:** prevenir cache poisoning, inyección SQL, y fugas de datos entre usuarios.

### R3.1 — Validación de inputs en claves de cache
- `build_unit_cache_key`: ¿se sanitizan los inputs? (strip, upper, validación IATA)
- ¿Qué pasa si alguien pasa `origin_iata="'; DROP TABLE--"` ? ¿Llega a la BD?

### R3.2 — ¿La cache cross-user es realmente cross-user?
- Revisar `QuickSearchCacheEntry`: ¿hay alguna FK a `users` o `user_id`?
- Revisar `get_fresh_entry`: ¿filtra por `user_id`? (no debe)
- Confirmar que la unidad de cache es `(origin, destination, date, provider)` — sin identidad de usuario.

### R3.3 — ¿Los payloads JSON se escapan correctamente?
- Revisar `serialize_fetch_result` y `deserialize_fetch_result`:
  - ¿Los precios se convierten a `float`?
  - ¿Las fechas se serializan con `.isoformat()`?
  - ¿Hay riesgo de inyección de objetos maliciosos vía `warnings_json`?

### R3.4 — ¿El `source_hash` previene colisiones?
- `build_cache_source_hash`: ¿usa SHA-256? ¿el prefijo `qs_` + 16 chars hex es suficiente?
- ¿Qué pasa si dos consultas con diferentes `currency` generan el mismo hash? (El hash actual no incluye currency — ¿es esto un bug?)

**Verificación:**
```bash
cd backend && python -m pytest tests/unit/test_quick_search_cache_models.py -v -k "hash"
```

---

## Fase R4. Auditoría de integridad funcional

**Objetivo:** verificar que la cache no rompe la semántica de quick-search ni watchlist.

### R4.1 — ¿La cache respeta los TTL correctamente?
- Revisar `_TTL_BY_CATEGORY` en `quick_search_cache_service.py`:
  - `ready`: 86400s (24h)
  - `empty`: 7200s (2h)
  - `degraded`: 1800s (30min)
- Revisar `_ttl_for_category`: ¿tiene un mínimo de 60s?
- Revisar `get_fresh_entry`: ¿filtra por `expires_at_utc > now`?
- Revisar `set_cache_entry`: ¿calcula `expires_at = now + ttl`?

### R4.2 — ¿La clasificación de resultados es correcta?
- Revisar `classify_cache_result`:
  - ¿`degradation_codes` incluye todos los códigos relevantes? (`provider_error_partial`, `provider_timeout_partial`, `provider_partial_results_served`, `ryanair_availability_failed_partial`, `ryanair_fares_failed_partial`, `ryanair_unavailable_partial`)
  - ¿Falta algún código? Sugerencia: buscar todos los warnings que usa `_normalize_warning_codes` en `search.py` y ver si alguno más debería marcar `degraded`.
  - ¿`flights` vacío + warnings = `empty` (no `degraded`)? Verificar intencionalidad.

### R4.3 — ¿La cache de watchlist es consistente?
- Revisar `_refresh_watch_now` en `watchlist.py`:
  - ¿El cache hit crea un `PriceSnapshot` correctamente? (usa `utc_now_naive().replace(microsecond=0)`)
  - ¿El cache miss persiste el resultado con las warnings correctas? (Ver R4.4)
  - ¿`WATCH_SHARED_CACHE_ENABLED` usa la misma env var que quick-search? (`QUICK_SEARCH_SHARED_CACHE_ENABLED`)
  - ¿Hay riesgo de que watchlist lea una entrada `empty`/`degraded` y cree un snapshot sin vuelos?

### R4.4 — ¿Las warnings del provider se preservan en la cache?
- **Cache SET desde quick-search:** `_fetch_with_cache` → `shared_cache_set` → `set_cache_entry`. ¿Las warnings viajan correctamente?
- **Cache SET desde watchlist:** `_refresh_watch_now` → `serialize_fetch_result(ProviderFetchResult(flights=flights, warnings=provider_warnings))`. Verificar que `provider_warnings` NO sea `[]` cuando el provider original tenía warnings (esto se arregló en la revisión — confirmar que el fix está presente).

### R4.5 — ¿Pruning no rompe nada?
- Revisar el pruning en `search.py`: `hash(query_trace_id) % 10 == 0`
  - ¿`hash()` es determinista dentro de un proceso Python? (sí, con PYTHONHASHSEED)
  - ¿El `batch_size=200` es adecuado?
  - ¿La excepción se traga silenciosamente? (sí — `except Exception: pass`. ¿Es aceptable?)

**Verificación:**
```bash
cd backend && python -m pytest tests/unit/test_quick_search_cache_models.py tests/unit/test_quick_search_shared_cache.py -v
```

---

## Fase R5. Auditoría de edge cases

**Objetivo:** encontrar bugs que solo aparecen en condiciones límite.

### R5.1 — Cache vacía
- ¿Qué pasa cuando la tabla `quick_search_cache_entry` está vacía?
- ¿`get_fresh_entry` devuelve `None` limpiamente?
- ¿El sistema degrada gracefulmente a provider-only?

### R5.2 — Proveedor caído + cache fresca
- Si el provider está caído pero hay una entrada `ready` en cache, ¿quick-search devuelve resultados cacheados?
- Si la entrada está `degraded` (30min TTL), ¿se sigue devolviendo o se intenta fetch?

### R5.3 — Fechas en el pasado
- ¿Qué pasa si se cachea `travel_date` en el pasado (ej. ayer)?
- ¿La entrada se considera fresca mientras `expires_at_utc > now`?
- ¿Es esto deseable para watchlist (que puede consultar fechas pasadas)?

### R5.4 — Collisión de source_hash
- Dos consultas idénticas generan el mismo `source_hash`. ¿Qué pasa si el hash colisiona con una consulta diferente?
- Con 16 chars hex = 64 bits, probabilidad de colisión con 10K entradas ≈ 2.7e-12 (despreciable).

### R5.5 — Provider `"multi"` como clave
- Todas las entradas de cache usan `provider="multi"`. ¿Qué implicaciones tiene?
- Si en el futuro se añade otro provider (Duffel), ¿los resultados de Ryanair y Duffel se mezclarían bajo `"multi"`?
- **Recomendación:** verificar si el `source_hash` distingue correctamente entre providers.

**Verificación:** revisar manualmente los archivos; no hay tests automatizados para estos edge cases.

---

## Fase R6. Auditoría de coverage de tests

**Objetivo:** identificar qué no está cubierto por tests.

### R6.1 — Inventario de tests existentes
Ejecutar y revisar:

```bash
cd backend
python -m pytest tests/unit/test_quick_search_cache_models.py -v  # 17 tests
python -m pytest tests/unit/test_quick_search_shared_cache.py -v   # 13 tests
python -m pytest tests/unit/test_quick_search_execution.py -v      # 5 tests
```

### R6.2 — ¿Qué NO está cubierto?

Marcar como ❌ lo que falte:

- [ ] ❓ `get_fresh_entry` con entrada expirada (devuelve None)
- [ ] ❓ `set_cache_entry` con clave duplicada (upsert semántica)
- [ ] ❓ `prune_expired_entries` elimina solo expirados
- [ ] ❓ `serialize_fetch_result` + `deserialize_fetch_result` roundtrip con warnings
- [ ] ❓ `classify_cache_result` con todos los degradation_codes conocidos
- [ ] ❓ `_fetch_with_cache` con L2 fallando (DB caída)
- [ ] ❓ `_refresh_watch_now` con cache `empty` (sin vuelos)
- [ ] ❓ `_refresh_watch_now` con cache `degraded` (vuelos parciales)
- [ ] ❓ Dos requests concurrentes con el mismo `origin+destination+date` (cross-request stampede)
- [ ] ❓ Pruning no se ejecuta si `QUICK_SEARCH_SHARED_CACHE_ENABLED=false`
- [ ] ❓ Feature flag OFF: el sistema funciona exactamente como antes (sin tocar BD)

**Verificación:**
```bash
cd backend && python -m pytest tests/unit/ -v --tb=short 2>&1 | grep -E "PASSED|FAILED|ERROR" | wc -l
```

---

## Fase R7. Auditoría de performance y operabilidad

**Objetivo:** asegurar que la cache no degrada el rendimiento.

### R7.1 — Análisis de overhead
- Cada `_fetch_with_cache`:
  1. L1 check (dict lookup + timestamp) → ~1μs
  2. L2 check (`get_fresh_entry` → DB query + posible commit) → ~1-5ms
  3. Provider fetch → ~500-5000ms
- Con feature flag OFF, el overhead es ~0 (los callables son `None`).
- Con feature flag ON, el overhead del L2 check es aceptable comparado con el provider fetch.

### R7.2 — Pruning probabilístico
- `hash(query_trace_id) % 10 == 0` → ~10% de requests ejecutan pruning.
- `prune_expired_entries` con `batch_size=200` + `_DB_LOCK` → podría bloquear otras operaciones de cache brevemente.
- **Recomendación:** considerar fire-and-forget (`threading.Thread(target=..., daemon=True).start()`) para no bloquear la respuesta HTTP.

### R7.3 — Crecimiento de la tabla
- Con TTL máximo de 24h y ~1000 búsquedas únicas/día, la tabla crecería ~1000 filas/día.
- Sin pruning, en 30 días = 30K filas. Con pruning activo, se mantiene estable.
- Verificar que el índice `ix_quick_search_cache_entry_expires_at_utc` existe en la migración.

### R7.4 — Feature flags y rollback
- `QUICK_SEARCH_SHARED_CACHE_ENABLED=false` → vuelta inmediata al comportamiento anterior.
- ¿Hay riesgo de inconsistencia si se activa/desactiva el flag durante el runtime? (No — los callables se reconstruyen en cada request.)
- ¿Las entradas en BD quedan huérfanas si se desactiva el flag? (Sí, pero no afectan — simplemente no se leen.)

**Verificación:**
```bash
cd backend && python -c "
from app.infrastructure.db.models import QuickSearchCacheEntry
print('Columns:', [c.name for c in QuickSearchCacheEntry.__table__.columns])
print('Indexes:', [i.name for i in QuickSearchCacheEntry.__table__.indexes])
"
```

---

## Fase R8. Auditoría documental

**Objetivo:** verificar que código y documentación están alineados.

### R8.1 — Contrato vs código
- `docs/reference/backend/quick-search-contract.md` dice que los TTL son ready=24h, empty=2h, degraded=30min.
- Verificar en `quick_search_cache_service.py` que `_TTL_BY_CATEGORY` coincide.

### R8.2 — Feature flags documentados
- `backend/.env.example` debe listar las 5 variables con comentarios explicativos.
- El contrato debe mencionar los flags y su efecto.

### R8.3 — Tabla de implementación
- La sección "Implementation status" en el contrato debe listar TODOS los archivos modificados/creados.
- Verificar que no falte ninguno.

### R8.4 — DOCS_INVENTORY.md
- La entrada "Actualizacion manual 2026-06-10 (quick-search shared cache implementation complete)" debe listar todos los archivos nuevos y modificados.
- Verificar que coincide con `git diff --stat 5f10a25~1..5f10a25`.

---

## Fase R9. Reporte final

**Objetivo:** producir un informe estructurado con hallazgos, severidad y recomendaciones.

### Formato del reporte

```markdown
# Quick-Search Shared Cache — Informe de Revisión

**Fecha:** [fecha]
**Commits auditados:** 5f10a25, 0113e4d
**Revisor:** [nombre de la IA]

## Resumen ejecutivo
[2-3 frases sobre el estado general]

## Hallazgos críticos (bloqueantes para producción)
- [ ] **H1:** [descripción] — Archivo: línea — Severidad: crítica
- [ ] **H2:** ...

## Hallazgos importantes (no bloqueantes, requiere acción)
- [ ] **H3:** [descripción] — Archivo: línea — Severidad: alta
- [ ] **H4:** ...

## Hallazgos menores (mejoras deseables)
- [ ] **H5:** [descripción] — Severidad: baja
- [ ] **H6:** ...

## Cobertura de tests
- Tests existentes: [N]
- Issues de coverage: [lista de gaps]

## Veredicto
- [ ] ✅ Listo para activar en local
- [ ] ✅ Listo para staging (con QUICK_SEARCH_SHARED_CACHE_ENABLED=true)
- [ ] ⚠️ Listo para prod con condiciones: [lista]
- [ ] ❌ No listo para prod — razones: [lista]

## Recomendaciones para Redis
[Notas sobre la migración futura a Redis como hot layer]
```

---

## Comandos de verificación (ejecutar todos al final)

```bash
# 1. Tests unitarios de cache
cd C:\Users\javiru\Desktop\viru-air\backend
python -m pytest tests/unit/test_quick_search_cache_models.py tests/unit/test_quick_search_shared_cache.py tests/unit/test_quick_search_execution.py -v

# 2. Tests de regresión e2e
python -m pytest tests/unit/test_quick_search_e2e_regression.py -v

# 3. Imports sanity check
python -c "from app.services.quick_search_cache_service import *; from app.services.quick_search_execution import *; print('OK')"

# 4. Modelo DB
python -c "from app.infrastructure.db.models import QuickSearchCacheEntry; print([c.name for c in QuickSearchCacheEntry.__table__.columns])"

# 5. Migración
python -m alembic check

# 6. Git diff del feature
git log --oneline 5f10a25~1..0113e4d
git diff --stat 5f10a25~1..5f10a25
```

---

## Handoff

Este plan está diseñado para ser ejecutado por otra IA. Cada fase es independiente y puede ejecutarse en paralelo con las demás (excepto R1 que debe ir primero). El reporte final (R9) debe consolidar todos los hallazgos.

**Tiempo estimado de ejecución:** 15-30 minutos para una IA con acceso a herramientas de lectura de archivos y terminal.
