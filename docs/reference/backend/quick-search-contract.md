Status: reference
Scope: technical reference for implementation work
Last reviewed: 2026-04-17
Canonical source: docs/reference/backend/quick-search-contract.md
Related: docs/INDICE_UNICO.md, docs/overview/current-state.md

---
# Quick-Search Backend Contract (Canonical v2)

## Canonical request shape

```json
{
  "origin": {
    "seed_iata": "LEI",
    "include_nearby": true,
    "radius_km": 180,
    "max_candidates": 6
  },
  "destination": {
    "seed_iata": "DUB",
    "include_nearby": false,
    "radius_km": 150,
    "max_candidates": 6
  },
  "travel": {
    "date": "2026-06-14",
    "flex_before": 1,
    "flex_after": 2
  },
  "constraints": {
    "departure_window": { "after": "06:00", "before": "22:00" },
    "exclude_origins": [],
    "exclude_destinations": [],
    "strict_filters": true,
    "include_stops": false,
    "max_stops": 0,
    "soft_filters_weight": 0.6
  },
  "execution": {
    "max_pairs": 24,
    "max_requests": 120,
    "timeout_ms": 8000,
    "concurrency_limit": 6
  }
}
```

## Required fields
- `origin.seed_iata`
- `destination.seed_iata`
- `travel.date`

## Optional fields
- `origin.include_nearby`, `origin.radius_km`, `origin.max_candidates`
- `destination.include_nearby`, `destination.radius_km`, `destination.max_candidates`

## Radius semantics (canonical v2)
- `radius_km` is a **valid numeric radius**, not an on/off sentinel.
- Valid range: `10..500`.
- `include_nearby` toggles expansion independently per side:
  - `false` → no nearby expansion for that side (seed only), radius is ignored operationally.
  - `true` → nearby expansion enabled and radius is used.
- Defensive compatibility: legacy clients sending `radius_km=0` with `include_nearby=false` are normalized to default `150` server-side before validation.
- New clients should always send a valid radius (for example current UI value, default `150`) and should not send sentinel `0`.

### Expansion rules
- Seed is always included first when valid.
- `max_candidates` counts the final set including seed.
- If seed is explicitly excluded in `exclude_origins`/`exclude_destinations`, request is rejected.
- Origin and destination expansion are independent (no cross-side side-effects).
- `travel.flex_before`, `travel.flex_after`
- `constraints.*`
- `execution.*`

## Legacy compatibility
The endpoint still accepts legacy flat payload/query params and normalizes them internally.
Legacy aliases are exposed in response `meta.legacy_aliases_used` for transition tracking.

Legacy aliases (accepted temporarily):
- `include_nearby_origin` / `include_nearby_origins`
- `include_nearby_destination` / `include_nearby_destinations`
- `date`
- `departure_from` / `departure_to`
- `strict_mode`
- `dias_antes` / `dias_despues`

### Legacy conflict watchlist
- `date` vs `travel_date`: `travel_date` is canonical; `date` should be treated as compatibility alias.
- `include_stops` / `max_stops`: accepted for compatibility but not fully enforceable in quick mode.
- `strict_mode` vs `strict_filters`: `strict_filters` is canonical.
- `include_nearby_origin(s)` / `include_nearby_destination(s)`: canonical uses plural side flags.
- `radius_km=0` sentinel: deprecated; clients must send valid radius in `10..500`.

## Filter implementation status
Response includes:
- `meta.filter_support.supported`
- `meta.filter_support.legacy_partial`
- `meta.filter_support.pending`

Current intent:
- Supported: `strict_filters`, `departure_window`, `exclude_origins`, `exclude_destinations`
- Legacy partial: `include_stops`, `max_stops`, `soft_filters_weight`
- Pending: full stop-logic, full soft-ranking weight behavior

## Response compatibility
The endpoint still returns `query`, `filters`, `results` and now adds:
- `meta.contract_version`
- `meta.legacy_aliases_used`
- `meta.filter_support`
- `meta.pair_counts`
- `meta.ai_preference`
- `meta.search_fingerprint`
- `meta.search_cache`

### AI preferred result
- `meta.ai_preference`:
  - `enabled`: `boolean`
  - `source`: `ai | heuristic`
  - `preferred_result_id`: `string | null`
  - `fallback_used`: `boolean`
- `results[]` may include:
  - `ai_preferred`: `boolean`
  - `ai_preferred_reason`: `string | null`
- At most one result per response may arrive with `ai_preferred=true`.
- The preferred result is selected from the already ranked and paginated response set; the backend does not reorder `results[]`.
- If OpenAI is unavailable, times out, or returns invalid output, backend falls back to a deterministic heuristic and exposes that through `meta.ai_preference.source="heuristic"` plus `fallback_used=true`.

## Freshness envelope (Fare Memory canonical contract)

> Estado: definido en backend como contrato canonico preparatorio desde 2026-06-14. La integracion visible por defecto en `results[]` puede activarse por fases posteriores, pero cualquier implementacion nueva debe respetar este shape.

Per-result freshness payload:

```json
{
  "freshness": {
    "status": "fresh",
    "observed_at": "2026-06-14T10:15:00Z",
    "expires_at": "2026-06-14T12:15:00Z",
    "age_seconds": 420,
    "confidence_score": 0.91,
    "source": "provider_cache",
    "requires_revalidation": false,
    "validation_status": "revalidated"
  }
}
```

Canonical rules:

- `status` allowed values:
  - `fresh`
  - `warm`
  - `stale`
  - `expired`
  - `negative_fresh`
  - `negative_stale`
  - `provider_error_fresh`
  - `provider_error_stale`
- `price` missing must stay `null`, never `0`.
- `duration_total_min` missing must stay `null`, never `0`.
- If the value comes from cache, `source` must say so.
- If the backend knows the price is historical only, it must not serialize it as `fresh`.
- Provider failure must remain distinguishable from `no_results`.

Implementation note:

- Helper module: `backend/app/services/fare_memory.py`
- Canonical builder: `build_freshness_payload(...)`
- Fingerprints defined in the same module are preparatory for Fare Memory phases 24-25 and are not a replacement for `query_signature`.

## Exact search cache metadata (Fare Memory Fase 27)

Quick Search may expose exact-search cache metadata at `meta.search_cache`:

```json
{
  "search_fingerprint": "fsm_search_...",
  "search_cache": {
    "exact_hit": true,
    "search_fingerprint": "fsm_search_...",
    "freshness": {
      "status": "fresh",
      "observed_at": "2026-06-15T10:00:00Z",
      "expires_at": "2026-06-15T11:00:00Z",
      "age_seconds": 30,
      "confidence_score": 0.95,
      "source": "provider_cache",
      "requires_revalidation": false,
      "validation_status": "revalidated"
    },
    "requires_revalidation": false,
    "provider": "search_exact"
  }
}
```

Rules:

- `exact_hit=true` means the full response payload was served from exact-search cache.
- `exact_hit=false` means the backend resolved the request normally and persisted the final payload for future exact reuse.
- `query_signature` remains the public observability signature; `search_fingerprint` is the canonical Fare Memory identity key for exact search reuse.

## Provider status (multi-provider compatible)

`meta.provider_status` keeps legacy compatibility and now includes aggregated provider state:

- `overall_status`: `ok | partial_degraded | total_outage`
- `providers[]`:
  - `id`
  - `status`
  - `degraded`
  - `errors`
  - `timeouts`
  - `results_count`
- `legacy`: compatibility payload derived for older consumers.

Warnings canónicos esperados en `meta.warnings_structured`:

- `provider_error_partial`
- `provider_timeout_partial`
- `provider_total_outage`
- `provider_partial_results_served`

## Negative cache (Fare Memory Fase 28)

Quick Search maintains a dedicated negative cache for route-date-provider units when the system learns that retrying immediately has low value.

Current intent:

- `no_availability` -> returns empty result without provider call for a short reusable window.
- `provider_timeout` / `provider_error` / `provider_total_outage` -> returns no flights plus canonical warning codes and applies shorter backoff.

Behavioral rule:

- `provider_error` is not serialized as silent `no_results`.
- `meta.pipeline_counters.negative_cache_hits` tracks dedicated negative-cache reuse separately from `l1_cache_hits` and `l2_cache_hits`.

## Monthly calendar hints (`POST /api/v1/search/quick/calendar-hints`)

Fast monthly endpoint for `/quick-search` datepicker heat hints.

### Request

```json
{
  "origin_iata": "MAD",
  "destination_iata": "DUB",
  "month": "2030-06",
  "adults": 1,
  "aggregation_mode": "min",
  "bucket_mode": "monthly_terciles"
}
```

Country scope request (mixed or both sides):

```json
{
  "origin_iata": ["MAD", "BCN", "AGP"],
  "destination_iata": "DUB",
  "month": "2030-06",
  "adults": 1,
  "aggregation_mode": "median",
  "bucket_mode": "guidelines",
  "guideline_thresholds": {
    "low_max": 90,
    "mid_max": 150,
    "currency": "EUR"
  }
}
```

### Response

```json
{
  "days": [
    {
      "date": "2030-06-05",
      "min_price": 60.0,
      "bucket": "low",
      "no_data_reason": null
    },
    {
      "date": "2030-06-20",
      "min_price": null,
      "bucket": "none",
      "no_data_reason": "no_fare_data"
    }
  ],
  "meta": {
    "currency": "EUR",
    "cache_ttl_sec": 600,
    "cache_hit": false,
    "partial": false,
    "scope_mode": "country_mixed",
    "ranked_airports": {
      "origin": ["MAD", "BCN", "AGP"],
      "destination": ["DUB"],
      "origin_count": 3,
      "destination_count": 1
    },
    "ranked_routes_count": 3,
    "aggregation_mode": "median",
    "bucket_mode": "guidelines",
    "guideline_thresholds_effective": {
      "low_max": 90.0,
      "mid_max": 150.0,
      "currency": "EUR"
    }
  }
}
```

### Bucket semantics
- `bucket_mode=monthly_terciles`:
  - `low`: cheaper third of priced days in the month.
  - `mid`: middle third of priced days.
  - `high`: expensive third of priced days.
- `bucket_mode=guidelines`:
  - `low`: `price <= low_max`
  - `mid`: `price > low_max` and `price <= mid_max`
  - `high`: `price > mid_max`
- `none`: day without usable fare data.

### Scope and aggregation notes
- `origin_iata` and `destination_iata` accept a single IATA (`string`) or a seed pool (`string[]`).
- `scope_mode`:
  - `iata`: IATA↔IATA request.
  - `country_mixed`: one side is a country pool.
  - `country_country`: both sides are country pools.
- `aggregation_mode`:
  - `min`: day price = minimum across recommended routes.
  - `median`: day price = median across recommended routes.
  - `fixed_route`: day price from a single recommended route.
- For `scope_mode=iata`, backend keeps simple route behavior and treats aggregation effectively as `min`.
- `bucket_mode`:
  - `monthly_terciles` (default)
  - `guidelines`
- `guideline_thresholds` is optional but required in practice for deterministic custom guideline behavior:
  - `{ low_max, mid_max, currency }`
  - `low_max >= 0`
  - `mid_max > low_max`
  - `currency` in `EUR|USD|GBP`

## Search preferences extension (`GET/PUT /api/v1/preferences/search`)
- Added field: `country_price_hint_mode_default` with allowed values:
  - `min`
  - `median`
  - `fixed_route`
- Default value: `min`.
- This preference is consumed by quick-search calendar hints when at least one side is country scope.
- Added fields:
  - `calendar_hint_bucket_mode_default`: `monthly_terciles|guidelines` (default `monthly_terciles`)
  - `calendar_hint_guideline_low_max_default`: number (default `90`)
  - `calendar_hint_guideline_mid_max_default`: number (default `150`, must be greater than `low`)
- Guideline thresholds are stored in `preferred_currency` and converted when that currency is changed through this endpoint.

## Quick-search seed catalog
- `GET /api/v1/airports/seeds` is the canonical source for seed airports allowed by quick-search UI.
- The UI should use this catalog for IATA validation, autocomplete and country-only airport pools instead of broader static airport datasets.
- Response shape:
  - `items[]`: `{ iata, name, municipality, country_code, iso_region, type, is_primary, source }`
  - `count`
  - `source`

`execution.max_pairs` is applied to base O×D planned pairs (after filtering and priority ordering).
`execution.max_requests` limits provider request units (O×D×date).
`execution.timeout_ms` is applied per provider request.
`execution.concurrency_limit` controls max parallel provider calls.

Planned pairs expose: seed/nearby category, distances from seed, and `pair_priority_score`.
Execution metadata includes waves, cache hits, provider calls and effective limits.

### Result item shape (`results[]`)
Stable fields returned for frontend compatibility:
- `result_id`: stable row id generated server-side
- `origin`, `destination`, `travel_date`, `departure_time_local`
- `price`, `price_total`, `currency`, `source`
- `duration_total_min`: nullable until provider duration data is exposed in quick mode
- `ranking_score`: numeric alias of the final ranking score used by the UI
- `stale_data`: current quick-search responses return `false` unless degraded/stale semantics are introduced later
- `itinerary_type`: currently `direct` in quick mode
- `legs`: currently an empty list in quick mode unless richer provider segment data is introduced later

Compatibility/extended fields still returned:
- `score`: structured ranking breakdown
- `origin_seed_iata`, `destination_seed_iata`
- `origin_iata_used`, `destination_iata_used`
- `origin_is_seed`, `destination_is_seed`
- `origin_distance_from_seed_km`, `destination_distance_from_seed_km`
- `pair_category`, `discovery_explanation`, `query_trace_id`, `selected_from_pair_id`, `candidate_reason`

Defensive client note:
- Clients should still normalize missing optional fields such as `duration_total_min`, `legs` or `ranking_score` for backward compatibility with older responses.

## Ranking (current)
Final result ranking uses a multi-factor score:
- `price_component` (relative to cheapest candidate in current result set)
- `origin_seed_penalty`
- `destination_seed_penalty`
- `distance_penalty_total`
- `pair_category` bias (`seed-seed` < mixed < `nearby-nearby`)

Tie-breakers (stable):
1. `final_score`
2. `price`
3. `distance_penalty_total`
4. `travel_date`
5. `departure_time_local`

## Final deduplication
A dedicated dedupe phase runs after ranking and before serialization.
Semantic identity key (heuristic):
- `origin_iata_used`
- `destination_iata_used`
- `travel_date`
- `departure_time_local`
- `source`
- `currency`

When duplicates compete, the winner is selected by:
1. lower `final_score`
2. lower `price`
3. lower `distance_penalty_total`

## Filter matrix (Quick-Search)
| Filter | Type | Phase | Strict mode | Non-strict mode | Notes |
|---|---|---|---|---|---|
| `exclude_origins`, `exclude_destinations` | hard | expansion / pre-pairs | enforced | enforced | side-specific exclusions |
| `departure_window` | hard | post-fetch filter | enforced | can relax only when result set is empty | legacy behavior kept |
| `soft_filters_weight` | soft | ranking | scales soft penalties | scales soft penalties | affects seed/deviation penalties |
| `include_stops`, `max_stops` | unsupported (legacy_partial) | n/a | warning `strict_filter_not_enforceable` | warning `degraded_filter_application` | provider data not reliable in quick mode |
| `duration_max_min` | unsupported | n/a | warning `strict_filter_not_enforceable` | warning `degraded_filter_application` | provider missing duration field |

## Shared cache (V2.1 — persistent cross-user cache)

> **V2.1** (Junio 2026) introduce cache compartida persistente en BD como fuente de verdad.

### Semántica de cache compartida

La cache compartida opera sobre **unidades exactas** `(origin_iata, destination_iata, travel_date, provider)`, NO sobre el payload completo de la respuesta final al usuario.

**Diferencias clave entre los tres conceptos de reutilización:**

| Concepto | Clave | Alcance | Persistencia | Usuarios |
|---|---|---|---|---|
| **Unidad exacta cacheable** (`unit_cache_key`) | `(origin, destination, date, provider)` | Resultado crudo de un provider para una ruta-fecha concreta | 24h (ready), 2h (empty), 30min (degraded) | Cross-user (sin identidad de usuario) |
| **Respuesta final recompuesta** | `query_signature` (qsig_*) | Payload completo del endpoint tras ranking, dedupe y paginación | No se cachea como payload bruto canónico | N/A (se recompone desde unidades) |
| **Snapshots de watchlist** | `(watch_id, captured_at_utc)` | Precio canónico para un watch concreto | Indefinida (histórico) | Single-user (asociado a FlightWatch) |

### TTL por categoría de resultado

- `ready`: **24h** (86400s) — resultados con vuelos válidos
- `empty`: **2h** (7200s) — búsqueda sin vuelos encontrados
- `degraded`: **30min** (1800s) — resultados parciales o con errores de provider
- `pending`: **60s** (timeout de trabajo) — unidad en progreso por otra request concurrente

### Cache key canonicalization

- `origin_iata`: uppercase, trimmed, validated IATA
- `destination_iata`: uppercase, trimmed, validated IATA  
- `travel_date`: ISO 8601 date string (YYYY-MM-DD)
- `provider`: lowercase provider id (e.g. `ryanair`, `duffel`)

La **cache compartida es cross-user pero NO almacena identidad de usuario**. La tabla `quick_search_cache_entry` no tiene FK a `users`.

### Reutilización para búsquedas ampliadas

Cuando una búsqueda usa `include_nearby` o `flex`, el backend:
1. Descompone la búsqueda en unidades exactas `(origin, destination, date, provider)`
2. Consulta la cache compartida para cada unidad
3. Solo llama al provider para las unidades no cacheadas o expiradas
4. Recompone la respuesta final (ranking, dedupe, paginación) desde las unidades resueltas

### Feature flags

- `QUICK_SEARCH_SHARED_CACHE_ENABLED=true` — activa la cache persistente
- `QUICK_SEARCH_SHARED_CACHE_READY_TTL_SECONDS=86400`
- `QUICK_SEARCH_SHARED_CACHE_EMPTY_TTL_SECONDS=7200`
- `QUICK_SEARCH_SHARED_CACHE_DEGRADED_TTL_SECONDS=1800`
- `QUICK_SEARCH_SHARED_CACHE_USE_MEMORY_HOT_LAYER=true` — mantiene capa en memoria como L1

Con el flag `QUICK_SEARCH_SHARED_CACHE_ENABLED=false`, el sistema usa exclusivamente la cache en memoria actual (TTL 300s) sin tocar la tabla persistente.

### Observabilidad de cache

Contadores expuestos en `meta.pipeline_counters`:
- `shared_cache_hits`: aciertos en cache persistente
- `shared_cache_misses`: fallos que requirieron fetch real
- `shared_cache_stale_count`: entradas expiradas encontradas
- `provider_calls_avoided`: llamadas a provider evitadas gracias a la cache

### Siguiente paso: Redis como hot layer

La arquitectura está diseñada para que Redis pueda añadirse como capa L1 (caliente) sin cambiar la fuente de verdad (BD). La cache en BD seguiría siendo el contrato canónico; Redis sería una aceleración con TTL más corto.

## Implementation status (Junio 2026)

La cache compartida persistente (V2.1) está implementada con las siguientes piezas:

| Componente | Archivo | Estado |
|---|---|---|
| Modelo DB | `backend/app/infrastructure/db/models.py` → `QuickSearchCacheEntry` | ✅ vivo |
| Migración | `backend/alembic/versions/0030_add_quick_search_shared_cache.py` | ✅ aplicada |
| Servicio de cache | `backend/app/services/quick_search_cache_service.py` | ✅ vivo |
| Canonicalización | `backend/app/services/quick_search_execution.py` → `build_unit_cache_key`, `build_cache_source_hash`, `classify_cache_result` | ✅ vivo |
| Integración execution | `backend/app/services/quick_search_execution.py` → `execute_plan` + `_fetch_with_cache` (L1→L2→provider) | ✅ vivo |
| Anti-stampede | `backend/app/services/quick_search_execution.py` → per-key `threading.Lock` en `_fetch_with_cache` | ✅ vivo |
| Integración watchlist | `backend/app/api/v1/watchlist.py` → `_refresh_watch_now` consulta y persiste cache | ✅ vivo |
| Wiring endpoint | `backend/app/api/v1/search.py` → callables `shared_cache_get/set` + pruning | ✅ vivo |
| Feature flags | `backend/.env.example` → 5 env vars `QUICK_SEARCH_SHARED_CACHE_*` | ✅ vivo |
| Observabilidad | `pipeline_counters.l1_cache_hits`, `pipeline_counters.l2_cache_hits`, `provider_calls` en logs | ✅ vivo |
| Limpieza | `prune_expired_entries` llamado en ~10% de requests | ✅ vivo |
| Tests | `backend/tests/unit/test_quick_search_cache_models.py` (17 tests), `test_quick_search_shared_cache.py` (12 tests) | ✅ vivo |

### Activación

```bash
QUICK_SEARCH_SHARED_CACHE_ENABLED=true
```

Con el flag en `false`, el sistema usa exclusivamente la cache en memoria actual (L1, TTL 300s).

### Siguiente paso: Redis como hot layer

La arquitectura está diseñada para añadir Redis como capa L1 (caliente) sin cambiar la fuente de verdad (BD). La cache en BD sigue siendo el contrato canónico; Redis sería una aceleración con TTL más corto.

## Observability and debug
- Every search emits `meta.query_trace_id`.
- Phase timings are exposed in `meta.pipeline_metrics`.
- Structured counters are exposed in `meta.pipeline_counters`.
- Structured warning objects are exposed in `meta.warnings_structured`.
- Debug payload is available only when `APP_ENV=local` and `debug=true`.
- Rejected quick-search requests now return a standard error envelope with `correlation_id`.
- For backend validation rejections during quick-search expansion, `details[0]` includes:
  - `query_trace_id`
  - `reason`
  - `reason_code` / `rejected_value` when the backend can derive them
  - `canonical_request` for local diagnosis





