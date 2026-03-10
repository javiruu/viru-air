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
    "timeout_ms": 8000
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

`execution.max_pairs` and `execution.max_requests` are applied to pair planning.
`execution.timeout_ms` is already part of the contract; provider-level timeout enforcement is marked as pending.
