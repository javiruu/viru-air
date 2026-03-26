# Global UI i18n (ES/EN) - Design Doc

Date: 2026-02-19
Owner: Codex
Status: Approved by user

## Context
The UI is currently Spanish-first with scattered hardcoded strings. The goal is to deliver a complete bilingual (ES/EN) interface across all public and private pages, with consistent copy, formatting, and accessibility text.

## Goals
- Provide full ES/EN coverage for all UI copy (public and private).
- Centralize translations to ensure consistency and scalability.
- Use user preference as the source of truth for active language.
- Keep formatting (dates/numbers/currency) aligned with locale.

## Non-Goals
- No runtime translation service or external i18n platform.
- No URL-based locale routing.
- No backend-translated copy beyond exposing locale.

## Decisions (Approved)
1. Centralized dictionary-based i18n for the entire app.
2. Language resolution: user preference first, then browser, then ES fallback.
3. Static imports for dictionaries to avoid latency.

## Architecture
### Core API
- `t(key, params)` for translated strings.
- `useI18n()` hook to access current locale, locale tag, and helpers.
- Minimal plural support with `one/other` keys.

### Locale resolution
1. `preferences/region.language` as primary.
2. `navigator.language` fallback.
3. Default to `es`.

### Locale tags
- `es` -> `es-ES`
- `en` -> `en-US`

## Dictionary Structure
```
frontend/src/i18n/
  index.ts
  es.ts
  en.ts
  shared.ts
  domains/
    account.ts
    preferences.ts
    support.ts
    public.ts
```

### Key naming
- `domain.section.label` (e.g., `account.profile.title`).
- Reuse shared labels in `shared` (buttons, empty states, errors).

## Migration Strategy
1. Shared/global UI (layout, header, footer, menu, loaders).
2. Public pages (landing, policies, public help).
3. Private core (dashboard, quick search, alerts, watchlist).
4. Account system and preferences.
5. Admin and remaining pages.

Rule: no visible hardcoded text remains in `frontend/src/app` after migration.

## UX Consistency
- Missing keys fall back to ES and log a console warning.
- All `aria-label`, `aria-live`, and a11y strings go through `t()`.
- Check EN labels for truncation/overflow and adjust spacing if needed.

## Backend Alignment
- Keep `preferences/region.language` as source of truth.
- Ensure `me.locale` reflects active language when available.
- Validation accepts only `es` or `en`.
- No backend translation; frontend is responsible for copy.

## Testing & QA
- Smoke UI in ES and EN across all routes.
- Automated string checks for hardcoded copy in app pages.
- Unit tests for fallback and basic pluralization.
- Visual QA for EN overflow in buttons, headers, and labels.

## Risks
- Incomplete migration leaves mixed-language screens.
- Long EN labels may cause layout overflow.
- Missing keys could degrade user trust if not handled cleanly.

## Open Questions
- None at this time.
