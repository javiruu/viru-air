# frontend/AGENTS.md — viru-tracker frontend rules

This file defines frontend-specific rules for coding agents working inside the frontend area of `viru-tracker`.

The root `/AGENTS.md` still applies. This file adds specific guidance for UI implementation, visual quality, browser verification, frontend/API contracts, and user-visible behavior.

---

## Frontend mission

Frontend work must produce user-visible results that are:

- clear;
- controlled;
- sober;
- distinctive;
- responsive;
- verified in the real UI when applicable.

Do not treat frontend work as only “making the code compile”. A frontend change is complete only when the rendered behavior is correct and verified with appropriate evidence.

---

## Product identity in UI

`viru-tracker` is not generic SaaS.

Do not flatten the interface into a bland admin dashboard.

Preserve:

- hierarchy;
- rhythm;
- useful density;
- visual intention;
- premium restraint;
- editorial composition;
- controlled asymmetry where it helps;
- strong grouping;
- clear information priority.

The UI should feel intentional, calm, structured, elegant, not noisy, not empty, and not generic.

Simplicity means reducing friction and unnecessary logic, not removing character.

---

## UI implementation principles

When editing frontend code:

- Make the smallest meaningful change that solves the real UX problem.
- Match the existing component style, naming, structure, and conventions.
- Prefer improving the local component or flow over introducing global abstractions.
- Do not redesign unrelated areas.
- Do not replace a distinctive interface with a generic card/grid layout.
- Do not remove useful density just to make implementation easier.
- Do not make every section visually equal; preserve priority and hierarchy.
- Keep spacing, grouping, typography, contrast, and state intentional.

For UI changes, think in terms of:

1. user goal;
2. information hierarchy;
3. interaction path;
4. visual state;
5. verification evidence.

---

## Design adaptation

When the user asks to copy, adapt, or take inspiration from an outside UI/reference:

1. Identify what makes the reference strong:
   - composition;
   - spacing;
   - density;
   - emphasis;
   - motion;
   - grouping;
   - affordances;
   - information hierarchy.
2. Preserve those strengths.
3. Re-skin them into Viru’s tone.
4. Do not reduce them to a bland “safe” implementation unless explicitly asked.

Treat references as structural inspiration, not literal clones.

If the reference has strong personality, Viru should retain an equivalent level of intention while staying sober and controlled.

---

## Layout and visual hierarchy

Prefer:

- clear section hierarchy;
- intentional whitespace;
- grouped controls;
- meaningful density;
- strong empty, loading, error, and success states;
- readable typography;
- restrained contrast;
- consistent alignment;
- responsive layouts that still feel designed;
- motion only when it clarifies state or improves perceived quality.

Avoid:

- generic dashboards with equal-weight cards everywhere;
- decorative noise;
- oversized empty areas without purpose;
- cramped controls with no rhythm;
- hidden state changes with no feedback;
- visual changes that only work at one viewport;
- “it looks fine from code” assumptions.

---

## Component and state rules

For interactive components, account for relevant states:

- default;
- hover/focus;
- active/selected;
- loading;
- empty;
- success;
- error;
- disabled;
- responsive/mobile if affected.

Do not introduce state that cannot be explained by the user flow.

When changing forms:

- preserve validation behavior unless the task asks to change it;
- show useful error feedback;
- avoid silent failures;
- verify real submit behavior when feasible;
- inspect request payloads and responses for API-backed forms.

When changing navigation:

- verify the actual route transition;
- verify active states;
- verify auth/session-dependent behavior when relevant;
- check browser console and network requests.

---

## Frontend/API contract

When frontend behavior depends on backend/API data:

- Inspect the real request payload.
- Inspect the real response body.
- Verify the actual API base URL used by the browser.
- Check auth/session state if relevant.
- Treat frontend/backend mismatch as a first-class root-cause candidate.
- Do not patch only the UI if the real issue is a contract mismatch.
- Do not guess response shapes when canonical docs, types, or observed responses are available.

If a contract is unclear:

- check `/docs/reference/`, `/docs/specs/`, and relevant backend code selectively;
- state the assumption;
- avoid inventing frontend-only behavior that hides backend inconsistencies.

---

## Browser-first verification

For browser-visible work, real rendered verification is required whenever feasible.

Before creating a new Playwright/TestSprite scenario, check and reuse existing repo assets first (especially `frontend/tests/*quick-search*e2e*.ts`, `frontend/scripts/qa_*.mjs`, and prior evidence in `docs/qa/reports/`).

Do not claim a visual or browser-visible fix based only on:

- code inspection;
- typecheck;
- lint;
- build success;
- reasoning;
- “it should work”.

Browser-visible work is verified with visible evidence from one of these paths:

1. TestSprite or real browser automation;
2. screenshots captured by the agent in the real browser flow.

If neither is available, say exactly what remains unverified.

---

## TestSprite policy

Use TestSprite by default when the task involves:

- multi-step flows;
- real navigation between pages;
- login/register/account menu behavior;
- forms with validation;
- dashboards and interactive states;
- reported browser regressions;
- session-dependent behavior;
- API-backed UI interactions.

Do not force TestSprite when:

- the task is a tiny static visual change and screenshots are faster and sufficient;
- TestSprite is flaky for that route and manual screenshot verification is more reliable;
- the page state is simple enough that 2–4 screenshots fully prove the result.

Decision rule:

- use TestSprite for flows;
- use screenshots for scoped static verification;
- use both when the change is critical.

---

## Screenshot verification

When TestSprite is not used, capture screenshots in the real browser.

For a simple UI change:

- 1 screenshot of the full section or page after the change;
- 1 screenshot focused on the changed component.

For a structural or layout change:

- 1 screenshot of the full page;
- 1 screenshot of the changed section;
- 1 screenshot showing the interaction result if the component changes state.

For stateful UI, capture affected states when relevant:

- default;
- open/expanded;
- loading;
- empty;
- error;
- success.

Screenshot rules:

- Prefer full-context screenshots over tiny crops.
- The screenshot must show the real rendered result.
- If the user complained about positioning, spacing, hierarchy, duplication, or visual balance, capture enough context to prove that exact issue is resolved.
- Do not rely on screenshots of intermediate broken states unless explaining a limitation.

---

## Frontend debugging loop

For frontend bugs:

1. Reproduce the issue in the browser whenever feasible.
2. Check console errors.
3. Check network requests and responses if API-backed.
4. Inspect relevant state, props, route params, and session/auth assumptions.
5. Identify the smallest failing case.
6. Patch the smallest responsible surface.
7. Re-run relevant checks.
8. Verify again in the real flow.
9. Summarize root cause and evidence.

For HTTP/network issues, capture:

- failing request;
- payload;
- response status;
- response body;
- relevant console/server log when available.

---

## Responsive behavior

When a change affects layout, spacing, navigation, cards, forms, dashboards, or modals:

- verify desktop layout;
- verify at least one narrow/mobile viewport when feasible;
- avoid layouts that only work at the current viewport;
- preserve hierarchy across breakpoints;
- avoid hiding critical actions on small screens;
- do not introduce horizontal overflow unless intentional.

---

## Accessibility and usability

Do not degrade accessibility.

When touching interactive UI:

- preserve keyboard accessibility;
- keep visible focus states;
- use semantic elements where possible;
- preserve labels for inputs and controls;
- avoid clickable non-interactive elements unless the existing pattern requires it;
- ensure disabled/loading states are understandable;
- avoid relying only on color to communicate important state.

Do not overbuild accessibility abstractions beyond the task, but do not break basic usability.

---

## Styling, dependencies, and motion

Follow the project’s existing styling system.

- Prefer existing components, tokens, utilities, and patterns.
- Do not introduce a new UI library unless the task explicitly requires it.
- Do not introduce new global styles for a local problem.
- Avoid one-off magic numbers unless they are clearly local and justified by the design.
- Keep class names and structure readable.
- Remove styling made unused by your own change.

Motion should be restrained and purposeful. Use it to clarify state, continuity, or perceived quality, not as decoration.

---

## Performance and loading

For frontend changes that affect data-heavy views, dashboards, lists, tables, or repeated components:

- avoid unnecessary re-renders when obvious;
- avoid expensive computation in render paths when easy to prevent;
- preserve existing loading behavior unless intentionally changing it;
- do not replace incremental/loading states with blank screens;
- avoid hiding real latency with misleading success states.

Do not prematurely optimize. Only address performance when it is relevant to the task or obviously impacted by the change.

---

## Frontend tests

Prefer the smallest meaningful test that proves the behavior.

Use frontend tests when:

- a bug can be reproduced at component or integration level;
- a form validation path changed;
- navigation or conditional rendering changed;
- a regression is likely to recur;
- the behavior can be tested without brittle implementation details.

Do not add broad, fragile, snapshot-heavy tests unrelated to the task.

For visual/browser flows, follow `/tests/AGENTS.md` in addition to this file.

---

## Final report for frontend work

The final response must include:

- what changed;
- root cause, when applicable;
- files touched;
- verification method;
- route/page tested;
- exact interaction performed, if relevant;
- visible result observed;
- any limitation or unverified part.

For browser-visible work, do not finish with vague proof such as:

- “should be fixed”;
- “looks correct”;
- “build passes”;
- “I think it works”.

Use evidence from the real UI.

---

## Frontend anti-patterns

Avoid:

- claiming visual success without real browser evidence;
- treating build success as UI verification;
- flattening Viru into generic SaaS;
- removing hierarchy to simplify implementation;
- replacing a strong reference with a bland version;
- hiding API/contract issues with frontend-only patches;
- changing unrelated components while fixing one UI issue;
- adding global styles for a local problem;
- introducing new dependencies for minor UI work;
- shipping stateful UI without checking relevant states;
- ignoring mobile/responsive impact when layout changes;
- using screenshots that do not show the changed area clearly.
