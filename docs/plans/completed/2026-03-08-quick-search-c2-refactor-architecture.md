# Quick Search C2 Refactor Architecture (2026-03-08)

## Goal
Reduce coupling and file size in `frontend/src/app/(private)/quick-search/page.tsx` without changing runtime behavior.

## Resulting structure

- `frontend/src/app/(private)/quick-search/page.tsx`
  - Thin route wrapper only.
- `frontend/src/modules/quick-search/QuickSearchView.tsx`
  - Main composed view logic.
- `frontend/src/modules/quick-search/types.ts`
  - Domain and UI interaction types for quick-search.
- `frontend/src/modules/quick-search/requestBuilder.ts`
  - Query serialization for `/api/v1/search/quick` contract.
- `frontend/src/modules/quick-search/responseNormalizer.ts`
  - Result normalization/fallback behavior.
- `frontend/src/modules/quick-search/useQuickSearchMainState.ts`
  - Centralized state controller hook.
- `frontend/src/modules/quick-search/components/*`
  - Split UI blocks:
    - `QuickSearchSearchForm`
    - `QuickSearchAdvancedFilters`
    - `QuickSearchLoadingProgress`
    - `QuickSearchResultsList`
    - `QuickSearchStatePanels` (idle/empty/error/rate states)

## Invariants preserved

- Request contract for quick search remains query-string based and unchanged in keys:
  - `origin_iata`, `destination_iata`, `travel_date`, `date`, `flex_days_before`, `flex_days_after`, `radius_km`, `include_stops`, `include_nearby_*`, `max_stops`, exclusions, strict/soft fields.
- Strict/soft filtering toggles are preserved.
- Flex days behavior preserved.
- Alternatives visibility/marking preserved.
- No new state/form library introduced.

## Testing additions

- Added utility/smoke coverage in `frontend/tests/quick-search-refactor-utils.test.ts`:
  - request builder contract checks,
  - response normalizer edge case (missing id + fallback legs),
  - smoke flow for builder + normalizer interop.

## Why this shape

- Keeps routing file tiny and stable.
- Isolates API-facing serialization and normalization so future backend changes are localized.
- Concentrates state in one hook for easier incremental migration to smaller hooks later.
- Moves large JSX regions to named components to reduce cognitive load.
