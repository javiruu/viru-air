# Feature flags y activacion por entorno

**Estado:** vivo
**Ultima revision:** 2026-07-11
**Fuente de verdad:** si
**Area:** referencia / configuracion

## Resumen

Viru Tracker no usa hoy un sistema centralizado unico de feature flags. Las activaciones vigentes se controlan con variables de entorno por dominio y con runbooks especificos cuando el rollout necesita perfiles operativos.

Fuentes actuales:

- defaults ejecutables: `backend/.env.example`;
- Fare Memory y Quick Search shared cache: `docs/specs/viru-fare-memory.md`;
- perfiles `/puerta-a-puerta`: `docs/runbooks/runbook-activation-profiles.md`;
- flags de providers de vuelo: `docs/reference/backend/provider-integration-guide.md`.

Si hay conflicto, el orden de lectura es:

1. codigo/config que realmente lee la variable;
2. `backend/.env.example`;
3. spec o runbook vivo del dominio;
4. docs historicas o planes.

## Fare Memory y Quick Search

Las flags de Fare Memory permanecen apagadas por defecto cuando pueden aumentar coste, borrar datos o disparar trabajo en background. La memoria durable y las subcapas internas pueden existir aunque la activacion publica siga en rollout controlado.

Flags principales:

- `QUICK_SEARCH_SHARED_CACHE_ENABLED=false`: activa reutilizacion persistente de Quick Search.
- `FARE_MEMORY_ENABLED=true`: master switch del dominio Fare Memory.
- `FARE_MEMORY_WATCHLIST_BACKFILL_ENABLED=false`: activa backfill historico al crear o guardar watchlist.
- `FARE_MEMORY_BOOT_WARMUP_ENABLED=false`: agenda warmup de arranque.
- `FARE_MEMORY_RETENTION_ENABLED=false`: activa pruning automatico.
- `FARE_MEMORY_REVALIDATION_WORKER_ENABLED=false`: activa worker periodico de revalidacion.
- Redis sigue siendo opcional mediante `REDIS_URL` y `QUICK_SEARCH_REDIS_*`.

La tabla completa y los riesgos por flag viven en `docs/specs/viru-fare-memory.md`.

## Puerta a puerta

`/puerta-a-puerta` usa perfiles explicitos (`local_demo`, `local_real`, `staging_safe`, `prod_gradual`) documentados en `docs/runbooks/runbook-activation-profiles.md`.

Los grupos de flags activos son:

- `DOOR_TO_DOOR_ENABLE_*`;
- `DOOR_TO_DOOR_GTFS_*`;
- `GOOGLE_MAPS_API_KEY`, `GTFS_NAP_API_KEY`, `NAVITIA_API_KEY` cuando el perfil los requiere.

## Providers de vuelo

El orden y la activacion de providers de vuelos se controlan desde:

- `FLIGHT_PROVIDER_ORDER=ryanair,vueling`;
- `FLIGHT_PROVIDER_RYANAIR_ENABLED=true`;
- `FLIGHT_PROVIDER_VUELING_ENABLED=true`;
- `FLIGHT_PROVIDER_NON_CORE_ENABLED=false`;
- `FLIGHT_PROVIDER_WIZZAIR_ENABLED=false`;
- `FLIGHT_PROVIDER_EASYJET_ENABLED=false`;
- `FLIGHT_PROVIDER_IBERIA_ENABLED=false`;
- `FLIGHT_PROVIDER_DUFFEL_ENABLED=false`.

La guia viva de integracion y rollout de providers esta en `docs/reference/backend/provider-integration-guide.md`.

## Flags legacy archivadas

Estas flags pertenecen a milestones M7-M13 y ya no son el sistema activo de rollout:

- `ff_prediction_enabled`;
- `ff_self_connect_enabled`;
- `ff_everywhere_enabled`;
- `ff_deeplink_hardened`;
- `ff_country_content`;
- `ff_full_i18n`;
- `ff_suggestions_pipeline`.

No deben usarse para implementar nuevas activaciones. Se conservan aqui solo para trazabilidad historica.
