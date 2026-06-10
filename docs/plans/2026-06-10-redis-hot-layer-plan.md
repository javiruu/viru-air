# Redis Hot Layer — Design Plan

> **Estado:** plan  
> **Fecha:** 2026-06-10  
> **Área:** backend  
> **Dependencia:** Cache compartida persistente (Fases 1–15, ya completada ✅)

## Resumen ejecutivo

La cache compartida actual tiene dos capas:

| Capa | Backend | TTL | Scope |
|------|---------|-----|-------|
| L1 | `dict` en memoria (`_CACHE`) | 300s | Por proceso, no compartida |
| L2 | `quick_search_cache_entry` (DB) | 24h/2h/30min | Cross-user, cross-request |

Este plan añade una **capa Redis opcional entre L1 y L2**, reemplazando el `dict` en memoria con una cache distribuida que sobrevive reinicios de worker y se comparte entre múltiples procesos (útil con `uvicorn --workers N`).

## Objetivo

- Reemplazar L1 (`dict` en memoria) con Redis cuando esté disponible
- Mantener el fallback a `dict` local si Redis no está configurado (cero cambios en producción sin Redis)
- La capa Redis usa los mismos TTLs cortos (300s) y claves canónicas que L1 actual
- No cambia el contrato de L2 (DB) — Redis es solo una optimización de velocidad
- No introduce nueva dependencia obligatoria

## Arquitectura propuesta

```
Request → _fetch_with_cache()
              │
              ├─ L1: Redis GET (si REDIS_URL configurada)
              │      └─ HIT → return (cache_hit_type="L1")
              │
              ├─ L1-fallback: dict en memoria (si Redis no disponible)
              │      └─ HIT → return (cache_hit_type="L1")
              │
              ├─ L2: DB (get_fresh_entry via SessionLocal)
              │      └─ HIT → Redis SET + dict SET → return (cache_hit_type="L2")
              │
              └─ MISS: provider → Redis SET + dict SET + DB SET → return ("MISS")
```

## Fase R1. Cliente Redis y feature flag

**Objetivo:** añadir `redis` como dependencia opcional con conexión lazy.

**Archivos:**
- `backend/requirements.txt` o `pyproject.toml` — añadir `redis>=5.0` (opcional)
- `backend/app/infrastructure/redis_client.py` — nuevo: singleton lazy, `get_redis()` devuelve `Redis | None`
- `backend/.env.example` — añadir `REDIS_URL=redis://localhost:6379/0` (comentado)

**Implementación:**
```python
# redis_client.py
import os
import redis

_redis_client: redis.Redis | None = None
_redis_checked: bool = False

def get_redis() -> redis.Redis | None:
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True
    url = os.getenv("REDIS_URL", "").strip()
    if not url:
        return None
    try:
        _redis_client = redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
        _redis_client.ping()
        return _redis_client
    except Exception:
        return None
```

**Verify:**
- Sin `REDIS_URL` → `get_redis()` devuelve `None`, el sistema usa `dict` local (sin cambios)
- Con `REDIS_URL` inválida → `get_redis()` devuelve `None` tras intento fallido (graceful degradation)
- Con `REDIS_URL` válida → `get_redis()` devuelve cliente funcional

## Fase R2. Adaptador de serialización para Redis

**Objetivo:** serializar/deserializar `ProviderFetchResult` a/desde Redis (JSON).

**Archivos:**
- `backend/app/services/quick_search_cache_service.py` — reutilizar `serialize_fetch_result` / `deserialize_fetch_result` existentes

**Implementación:**
Las funciones de serialización ya existen en `cache_service.py`:
- `serialize_fetch_result(result) → (payload_json, warnings_json)` 
- `deserialize_fetch_result(payload_json, warnings_json) → ProviderFetchResult`

Para Redis, basta con serializar el par `(payload_json, warnings_json)` como un JSON wrapper:
```python
def redis_serialize(result: ProviderFetchResult) -> str:
    payload, warnings = serialize_fetch_result(result)
    return json.dumps({"p": payload, "w": warnings})

def redis_deserialize(raw: str) -> ProviderFetchResult:
    data = json.loads(raw)
    return deserialize_fetch_result(data["p"], data["w"])
```

**Verify:** roundtrip sin pérdida de datos.

## Fase R3. Integración en `_fetch_with_cache`

**Objetivo:** insertar la capa Redis entre L1 (`dict`) y L2 (DB).

**Archivos:**
- `backend/app/services/quick_search_execution.py` — modificar `_fetch_with_cache`

**Implementación:**
```python
def _fetch_with_cache(unit, timeout_ms, fetch_flights, shared_cache_get, shared_cache_set):
    key = (unit.origin_iata, unit.destination_iata, str(unit.travel_date))
    redis_key = f"qs:{key[0]}:{key[1]}:{key[2]}"  # e.g. qs:AGP:TSF:2026-12-25
    now = time.time()

    # L1-Redis: hot cache (if Redis available)
    r = get_redis()
    if r is not None:
        try:
            raw = r.get(redis_key)
            if raw:
                return redis_deserialize(raw), "L1"
        except Exception:
            pass  # Redis failure → fall through to L1-dict

    # L1-dict: in-memory hot cache (fallback, always available)
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
        if cached and now - cached[0] <= _CACHE_TTL_SECONDS:
            return cached[1], "L1"

    # L2: DB (unchanged)
    ...

    # On MISS: populate Redis + dict + DB
    if r is not None:
        try:
            r.setex(redis_key, _CACHE_TTL_SECONDS, redis_serialize(fetch_result))
        except Exception:
            pass
```

**Verify:**
- Con Redis: `l1_cache_hits` suben, latencia de L1 ~1ms (Redis local)
- Sin Redis: comportamiento idéntico al actual
- Redis caído a mitad de request: el sistema sigue funcionando con L1-dict

## Fase R4. Clave de Redis y TTL

**Objetivo:** definir el formato de clave y política de TTL en Redis.

**Formato de clave:**
```
qs:{origin_iata}:{destination_iata}:{travel_date}
```
Ejemplo: `qs:AGP:TSF:2026-12-25`

**TTL:** 300s (mismo que `_CACHE_TTL_SECONDS` actual). Configurable vía:
```
QUICK_SEARCH_REDIS_TTL_SECONDS=300
```

**Nota importante:** la clave Redis NO incluye `currency` ni `source_hash`. Es una cache caliente de corta duración (5 min), diseñada para absorber picos de tráfico dentro del mismo proceso o entre workers. La diferenciación por currency ocurre en L2 (DB) donde importa para la persistencia de 24h.

**Verify:**
- Dos requests con distinta currency pero misma ruta comparten L1-Redis (5min TTL) pero NO comparten L2-DB
- Tras 5 minutos, la entrada Redis expira y se refresca desde L2 o provider

## Fase R5. Observabilidad Redis

**Objetivo:** añadir contadores de Redis a las métricas existentes.

**Archivos:**
- `backend/app/services/quick_search_execution.py` — añadir `redis_hits` al meta

**Métricas nuevas:**
- `redis_hits`: número de hits en Redis (subconjunto de `l1_cache_hits`)
- `redis_misses`: fallos de Redis (llamada Redis que no encontró clave)
- `redis_errors`: errores de conexión Redis (se degrada gracefulmente)

**Logs:**
```
logger.debug("quick_search_redis hit=%d miss=%d errors=%d", redis_hits, redis_misses, redis_errors)
```

**Verify:** con Redis activo, los logs muestran `redis_hits > 0`.

## Fase R6. Tests

**Objetivo:** cubrir el comportamiento con y sin Redis.

**Archivos:**
- `backend/tests/unit/test_quick_search_redis.py` — nuevo

**Tests:**
1. `test_redis_hit_returns_cached_result` — mock Redis, verifica L1 hit
2. `test_redis_miss_falls_through_to_l2` — mock Redis miss, verifica L2 hit
3. `test_redis_unavailable_falls_back_to_dict` — Redis caído, verifica dict local
4. `test_redis_populated_on_provider_fetch` — tras provider call, Redis tiene entrada
5. `test_redis_key_format` — verifica formato `qs:AGP:TSF:2026-12-25`
6. `test_without_redis_url_uses_dict_only` — sin `REDIS_URL`, comportamiento original

**Verify:** tests pasan con y sin Redis.

## Fase R7. Docker Compose y documentación

**Objetivo:** facilitar el desarrollo local con Redis.

**Archivos:**
- `infra/docker-compose.yml` — añadir servicio `redis` (opcional, comentado):
  ```yaml
  # redis:
  #   image: redis:7-alpine
  #   ports:
  #     - "6379:6379"
  ```
- `backend/.env.example` — documentar `REDIS_URL` y `QUICK_SEARCH_REDIS_TTL_SECONDS`
- `docs/engineering/backend.md` — añadir sección "Redis hot layer"

**Verify:** `docker compose up redis` + `REDIS_URL=redis://localhost:6379/0` → cache funcional.

## Riesgos

- **Nueva dependencia:** `redis-py` añade una dependencia Python. Se maneja como opcional (el código funciona sin ella).
- **Memoria Redis:** sin políticas de evicción, Redis podría crecer. La solución: TTL de 300s + `maxmemory-policy volatile-lru`.
- **Latencia de red:** Redis local es <1ms, pero Redis remoto podría añadir 5-20ms. El fallback a dict local mitiga esto.
- **Serialización:** JSON es más lento que pickle/msgpack, pero para objetos pequeños (<10KB) es aceptable y portable.

## Criterio de done

- [ ] `REDIS_URL` configurada → Redis se usa como L1
- [ ] `REDIS_URL` no configurada → mismo comportamiento actual (dict local)
- [ ] Redis caído → degradación graceful a dict local, sin errores visibles al usuario
- [ ] Tests pasan con y sin Redis
- [ ] Documentación actualizada

## Orden de ejecución

1. R1 (cliente Redis + feature flag)
2. R2 (serialización)
3. R3 (integración en `_fetch_with_cache`)
4. R4 (clave y TTL)
5. R5 (observabilidad)
6. R6 (tests)
7. R7 (docker + docs)

## Handoff

Plan completo. La implementación es incremental: cada fase añade una pieza pequeña y verificable. El objetivo es que Redis sea una optimización transparente, no un requisito.
