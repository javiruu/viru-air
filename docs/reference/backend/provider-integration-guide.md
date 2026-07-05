Status: reference
Scope: backend provider architecture and onboarding
Last reviewed: 2026-07-02
Canonical source: docs/reference/backend/provider-integration-guide.md
Related: docs/engineering/backend.md, docs/reference/backend/quick-search-contract.md

---
# Flight Provider Integration Guide

## Objetivo

Añadir nuevos providers sin tocar lógica de negocio de:

- `POST /api/v1/search/quick`
- `POST /api/v1/watchlist/*`
- `POST /api/v1/recommendations`

## Contrato mínimo

Implementar `FlightProvider` con:

- `provider_id` estable (ej: `ryanair`, `duffel`, `kiwi`).
- `is_enabled() -> bool`.
- `get_flights(origin, destination, travel_date, timeout_ms, currency) -> ProviderFetchResult`.

`ProviderFetchResult` mantiene:

- `flights: list[ProviderFlight]`
- `warnings: list[str]` (compat legacy)
- `warnings_structured: list[ProviderWarning] | None` (canónico)

## Registro y orquestación

- Registrar la clase en `FlightProviderRegistry`.
- Controlar habilitación por env:
  - `FLIGHT_PROVIDER_ORDER` (default: `ryanair,vueling,wizzair,easyjet,iberia,duffel`)
  - `FLIGHT_PROVIDER_<ID>_ENABLED` (default: true)
  - Providers con credenciales propias pueden estar en el orden por defecto y no activarse si `is_enabled()` devuelve `false`.
  - Providers públicos como `ryanair` y `vueling` no requieren API key.
- El `FlightSearchOrchestrator` se encarga de:
  - ejecutar providers habilitados;
  - consolidar vuelos;
  - deduplicar resultados;
  - normalizar warnings estructurados y legacy.

## Providers activos

- `ryanair`: provider público sin credenciales.
- `vueling`: provider público sin credenciales. Crea sesión anónima contra `asm/v1/Auth`, consulta `avy/v3/AvailabilityServices/allFlights` y soporta alias `vy`.
- `wizzair`: provider FareChart público/configurable.
- `easyjet`: provider público sin credenciales. Consulta `ejavailability/api/v16/availability/query` y usa `flightconnections.easyjet.com/api/graphql` como fallback para resultados Dohop/Flight Connections con escala. Soporta alias `easy_jet`/`easy-jet`/`ezj`/`ezy`/`u2` y genera deeplinks oficiales. Si Dohop/Datadome bloquea el backend, expone `provider_total_outage`; si existe token operativo, `EASYJET_FLIGHT_CONNECTIONS_BYPASS_SECRET` envía `X-Dohop-Bypass`.
- `iberia`: provider NDC oficial/configurable. Requiere `IBERIA_NDC_BASE_URL` + `IBERIA_NDC_API_KEY`, soporta aliases `ib`/`iberia_ndc`, consulta AirShopping y queda desactivado si faltan credenciales.
- `duffel`: provider API con `DUFFEL_API_KEY`.

## Warnings canónicos recomendados

- `provider_error_partial`
- `provider_timeout_partial`
- `provider_total_outage`
- `provider_partial_results_served`
- `provider_empty_result` (info)

Los códigos legacy específicos (ej: `ryanair_*`) pueden coexistir durante transición.

## Testing mínimo para un provider nuevo

1. Mapea respuesta externa a `ProviderFlight`.
2. Timeout y HTTP error -> warning canónico estructurado.
3. Caso vacío sin excepción.
4. Integración con `FlightSearchOrchestrator` (merge/dedupe/status).
