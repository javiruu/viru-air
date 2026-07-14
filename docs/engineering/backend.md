# Backend

**Estado:** vivo  
**Última revisión:** 2026-05-11  
**Fuente de verdad:** sí  
**Área:** engineering

## Resumen

El backend de Viru Air está implementado con FastAPI y organiza API, dominio, infraestructura y servicios bajo `backend/app/`.

Desde 2026-05-26, la capa de vuelos usa arquitectura **provider-driven**:

- contrato común `FlightProvider` para integraciones;
- `FlightProviderRegistry` para activar/ordenar providers por configuración;
- `FlightSearchOrchestrator` para merge, dedupe y normalización de warnings.

Esto evita acoplar `quick-search`, `watchlist` y `recommendations` a un provider concreto.

## Cuándo usar este documento

Úsalo como punto de entrada antes de abrir contratos más específicos o tests del backend.

## Contenido principal

- Stack base verificado: Python 3.12+, FastAPI, SQLAlchemy, Alembic.
- Punto de entrada: `backend/app/main.py`.
- **Cache compartida persistente (V2.1):** `quick_search_cache_service.py` + `QuickSearchCacheEntry` en BD. Reutiliza resultados de provider entre usuarios con TTL por categoría (ready=24h, empty=2h, degraded=30min). Activada con `QUICK_SEARCH_SHARED_CACHE_ENABLED=true`. Ver contrato en [Quick Search contract](../reference/backend/quick-search-contract.md).
- Endpoints operativos visibles:
  - `/health`
  - `/ready`
- Contrato watchlist batch activo:
  - `POST /api/v1/watchlist/refresh-bulk`
  - `POST /api/v1/watchlist/status-bulk`
  - `POST /api/v1/watchlist/delete-bulk`
- Refresh manual de watchlist:
  - `POST /api/v1/watchlist/{watch_id}/refresh-now`
  - desde 2026-06-16 usa `RevalidationJob` para deduplicar revalidaciones activas por ruta y evitar dobles llamadas al provider.
  - si ya hay una revalidacion manual activa para la misma ruta, responde `429` con `code=revalidation_already_in_progress` y `Retry-After`.
  - desde 2026-06-21, la revalidacion se ejecuta por ruta compartida y persiste snapshots nuevos para todos los `FlightWatch` activos de esa misma ruta.
- Startup refresh automatico de watchlist:
  - `WATCHLIST_STARTUP_REFRESH_ENABLED=true` por defecto.
  - en startup, el backend encola `RevalidationJob` de tipo `startup_refresh` para cada ruta activa compartida.
  - `WATCHLIST_STARTUP_REFRESH_MAX_AGE_SECONDS=14400` define cuando una ruta activa se considera vencida al arrancar; el umbral se usa para prioridad y observabilidad, no para saltarse rutas activas.
  - el arranque no bloquea `ready`: un worker background drena jobs due de tipo `startup_refresh`, `boot_warmup` y `manual` con `target_type=route`.
  - una sola revalidacion por ruta comprueba todos los watches activos de esa ruta y persiste snapshots por usuario solo cuando falta dato, el dato previo era stale o el precio/currency cambio; asi se evita llenar el historico con puntos repetidos al abrir el servidor varias veces.
- Boot warmup de Fare Memory:
  - `FARE_MEMORY_BOOT_WARMUP_ENABLED=false` por defecto.
  - `FARE_MEMORY_BOOT_WARMUP_JITTER_SECONDS=30` define el retraso aleatorio maximo por job al arrancar.
  - cuando se activa, el backend agenda `RevalidationJob` de tipo `boot_warmup` solo para watchlists activas y emite el evento estructurado `fare_memory_boot_warmup_scheduled`.
  - el scheduler respeta `FARE_MEMORY_MAX_BOOT_JOBS`, recorta por `FARE_MEMORY_PROVIDER_RATE_LIMIT_PER_MINUTE` y evita duplicados si ya existe una revalidacion activa de la misma ruta/provider.
  - en startup no llama al provider directamente; solo deja jobs en cola con `scheduled_at` jitterizado para evitar estampidas.
- Volatilidad basica de Fare Memory:
  - servicio: `backend/app/services/fare_memory_volatility.py`.
  - calcula `changes_per_day`, `average_delta_abs`, `max_delta_abs`, `average_time_between_changes_seconds`, `dominant_direction_recent` y `volatility_score`.
  - soporta historico por oferta (`FlightPriceObservation`) y por ruta (`PriceSnapshot` agrupado por origen/destino/fecha).
  - si hay menos de 3 observaciones devuelve `status=insufficient_data` y no finge score predictivo.
  - desde 2026-06-16 el boot warmup usa esa señal para adelantar rutas que han cambiado varias veces recientemente, pero solo como prioridad tecnica de refresco.
- Observabilidad tecnica de Fare Memory:
  - endpoint admin: `GET /api/v1/admin/fare-memory-health`.
  - devuelve contadores agregados de `search_cache`, `negative_cache`, `offer_memory` y `revalidation_jobs`.
  - no expone payloads cacheados, fingerprints completos de requests ni datos por usuario.
- Flight Tracking Hub:
  - decision vigente: [ADR-004 Flight Tracking Hub](../adr/ADR-004-flight-tracking-hub.md).
  - `execute_plan` centraliza tracking de unidades exactas para Quick Search y calendar hints.
  - Fare Memory conserva memoria operativa compartida; `PriceSnapshot` conserva historico visible por usuario.
  - guardar en watchlist siembra snapshot solo con resultados `fresh`; resultados `warm`, `stale`, `expired`, negativos o errores encolan `RevalidationJob` de ruta.
- Dominio documentado con mayor detalle en:
  - [Quick Search contract](../reference/backend/quick-search-contract.md)
  - [Quick Search acceptance checklist](../reference/backend/quick-search-acceptance-checklist.md)
  - [Provider integration guide](../reference/backend/provider-integration-guide.md)

## Relacionado

- [Estado actual](../overview/current-state.md)
- [Referencia backend](../reference/README.md)
- [Runbooks](../runbooks/)
