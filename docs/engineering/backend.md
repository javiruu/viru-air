# Backend

**Estado:** vivo  
**Última revisión:** 2026-05-11  
**Fuente de verdad:** sí  
**Área:** engineering

## Resumen

El backend de Viru Tracker está implementado con FastAPI y organiza API, dominio, infraestructura y servicios bajo `backend/app/`.

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
- Dominio documentado con mayor detalle en:
  - [Quick Search contract](../reference/backend/quick-search-contract.md)
  - [Quick Search acceptance checklist](../reference/backend/quick-search-acceptance-checklist.md)
  - [Provider integration guide](../reference/backend/provider-integration-guide.md)

## Relacionado

- [Estado actual](../overview/current-state.md)
- [Referencia backend](../reference/README.md)
- [Runbooks](../runbooks/)
