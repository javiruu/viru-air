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
| `risk_allowed` | unsupported | n/a | warning `strict_filter_not_enforceable` | warning `degraded_filter_application` | risk model pending |

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





