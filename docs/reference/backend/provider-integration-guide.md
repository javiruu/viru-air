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
  - `FLIGHT_PROVIDER_ORDER` (default: `ryanair,vueling`)
  - `FLIGHT_PROVIDER_<ID>_ENABLED` (default: true solo para `ryanair` y `vueling`; false para el resto)
  - `FLIGHT_PROVIDER_NON_CORE_ENABLED=false` por defecto bloquea providers fuera de `ryanair`/`vueling`, incluso si un `.env` antiguo conserva `FLIGHT_PROVIDER_<ID>_ENABLED=true`.
  - Providers fuera de `ryanair`/`vueling` quedan opt-in con `FLIGHT_PROVIDER_NON_CORE_ENABLED=true` hasta que vuelvan a ser operativos de forma estable.
  - Providers con credenciales propias pueden figurar en `FLIGHT_PROVIDER_ORDER` y no activarse si `is_enabled()` devuelve `false`.
  - Providers públicos como `ryanair`, `vueling`, `easyjet` e `iberia` no requieren API key privada, pero solo Ryanair/Vueling están activos por defecto.
- El `FlightSearchOrchestrator` se encarga de:
  - ejecutar providers habilitados;
  - consolidar vuelos;
  - deduplicar resultados;
  - normalizar warnings estructurados y legacy.

## Providers disponibles

- `ryanair`: provider público sin credenciales.
- `vueling`: provider público sin credenciales. Crea sesión anónima contra `asm/v1/Auth`, consulta `avy/v3/AvailabilityServices/allFlights` y soporta alias `vy`.
- `wizzair`: provider FareChart público/configurable; opt-in explícito.
- `easyjet`: provider público sin credenciales; opt-in explícito. Consulta `ejavailability/api/v16/availability/query` y usa `flightconnections.easyjet.com/api/graphql` como fallback para resultados Dohop/Flight Connections con escala. Soporta alias `easy_jet`/`easy-jet`/`ezj`/`ezy`/`u2` y genera deeplinks oficiales. Si Dohop/Datadome bloquea el backend, expone `provider_total_outage`; si existe token operativo, `EASYJET_FLIGHT_CONNECTIONS_BYPASS_SECRET` envía `X-Dohop-Bypass`.
- `iberia`: provider público sin credenciales privadas; opt-in explícito. Reutiliza el contrato de la web de booking (`/flights/` + `ibisservices.iberia.com/api/sse-avm/rs/v2/availability`), soporta aliases `ib`/`iberia_ndc` por compatibilidad y genera deeplinks oficiales. Si el edge público/Akamai bloquea la consulta backend, expone `iberia_provider_unavailable_total` + `provider_total_outage`.
- `duffel`: provider API con `DUFFEL_API_KEY`; opt-in explícito.

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
