Status: reference
Scope: technical reference for implementation work
Last reviewed: 2026-04-15
Canonical source: docs/reference/backend/quick-search-acceptance-checklist.md
Related: docs/INDICE_UNICO.md, docs/overview/current-state.md

---
# Quick-Search Backend Acceptance Checklist (Cycle 10)

## Core pipeline
- [x] Contract canonical request normalized
- [x] Seed resolution validated
- [x] Nearby expansion by side (origin/destination) with metadata
- [x] Pair planning with explicit priority and no blind truncation
- [x] Execution planner with budget, timeout, concurrency, cache
- [x] Post-fetch filtering + strict/non-strict behavior
- [x] Final multi-factor ranking
- [x] Final semantic dedupe
- [x] Structured response + observability metadata

## Scenario validation
- [x] Seed only
- [x] Nearby origin only
- [x] Nearby destination only
- [x] Nearby both sides (cross pairs)
- [x] Budget constrained (`max_requests`)
- [x] Partial provider timeout with graceful degradation
- [x] LEI nearby reference behavior verified by expansion/planned pairs

## Filters
- [x] Exclusions hard-applied
- [x] Departure window hard-applied with strict/non-strict semantics
- [x] Soft weight applied to ranking penalties
- [x] Unsupported filters produce structured warnings (no fake support)

## Observability
- [x] `query_trace_id` per search
- [x] `pipeline_metrics` per phase
- [x] `pipeline_counters` and execution counters
- [x] Structured warnings list
- [x] Debug payload gated by `APP_ENV=local` + `debug=true`

## Residual risks (known)
- Provider data model still does not expose reliable stops/duration/risk for strict enforcement.
- Cache is in-memory only (single process scope).
- End-to-end HTTP integration test is optional/skipped when fastapi test deps are unavailable.





