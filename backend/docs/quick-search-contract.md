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

`execution.max_pairs` is applied to base O×D planned pairs (after filtering and priority ordering).
`execution.max_requests` limits provider request units (O×D×date).
`execution.timeout_ms` is applied per provider request.
`execution.concurrency_limit` controls max parallel provider calls.

Planned pairs expose: seed/nearby category, distances from seed, and `pair_priority_score`.
Execution metadata includes waves, cache hits, provider calls and effective limits.

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

## Observability and debug
- Every search emits `meta.query_trace_id`.
- Phase timings are exposed in `meta.pipeline_metrics`.
- Structured counters are exposed in `meta.pipeline_counters`.
- Structured warning objects are exposed in `meta.warnings_structured`.
- Debug payload is available only when `APP_ENV=local` and `debug=true`.
