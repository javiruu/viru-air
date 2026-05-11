# Quick-Search Airport Modal Layout Design

**Goal:** Make the origin/destination country selector modal scalable for large datasets with two-panel layout, independent scroll, and sticky header/search while keeping logic unchanged.

**Scope:** Only add minimal class anchors in `page.tsx` and scoped CSS in `globals.css`. No logic changes, no copy changes, no new tokens.

## Constraints
- No changes to handlers, state, or dataset logic.
- Only add className and minimal wrappers if missing.
- CSS must be scoped to `.qs-airport-modal*`.
- Keep existing modal look; only layout/overflow/sticky improvements.

## Approach (Recommended)
- Add class anchors to modal root, header, body, countries column, airports column, search wrapper, and recents wrapper.
- Apply CSS for max-height, overflow hidden, two-column grid with independent scrolling, sticky header and sticky search, and responsive stacking < 900px.
- Add optional density tweak for country list items within `.qs-airport-modal__countries` only.

## UX Expectations
- Modal height capped at ~82vh.
- Header always visible.
- Countries and airports scroll independently.
- Search remains sticky on airport list.
- Recents wrap without overflow.
- Responsive stacking for narrow viewports.

## Risks
- If the modal's scroll container is not itself, sticky behavior may be limited, but no regressions expected.

## Manual QA
- Scroll long countries list: header visible, left column scrolls.
- Select country with many airports: right column scrolls; search stays sticky.
- <=900px: columns stacked.
- Actions still functional (clear, use all country).
