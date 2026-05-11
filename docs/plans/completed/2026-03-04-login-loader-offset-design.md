# Login Loader Offset Design (2026-03-04)

## Goal
Move the login marketing loader block (the rotating words list) down by 3px on `/login` to better align visually, without changing content or layout elsewhere.

## Scope
- CSS-only adjustment in `frontend/src/styles/globals.css`.
- Target class: `.login-words`.
- Use `transform: translateY(3px)` as the minimal visual shift.

## Non-Goals
- No changes to text/i18n strings.
- No markup or component changes.
- No changes to other login layout elements.

## Approach Options Considered
1. `margin-top: 3px` on `.login-words` (affects layout flow).
2. `transform: translateY(3px)` on `.login-words` (visual shift only). **Chosen.**
3. Apply shift to container (`.login-loader` or `.marketing-card`) (too broad).

## Risks
- Minor subpixel rendering differences across browsers due to transform. Acceptable for 3px shift.

## Testing
- Visual check on `/login` in the browser (desktop).

## Rollback
- Remove the `transform` on `.login-words`.
