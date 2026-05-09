# AGENTS.md — viru-tracker 

This file defines the default operating rules for coding agents working in `viru-tracker`.
Follow these instructions unless the user explicitly overrides them.

## Core operating principles

### 1) Think before coding
- Do not assume silently.
- State important assumptions explicitly before implementing.
- If there are multiple plausible interpretations, name them instead of choosing one invisibly.
- If something is unclear and blocks a correct implementation, say what is unclear.
- Prefer a short clarification over building on a weak assumption.
- Surface tradeoffs when they matter.

For non-trivial tasks, start with a brief plan:

1. [step] → verify: [check]
2. [step] → verify: [check]
3. [step] → verify: [check]

### 2) Clarity first, not flattening
- Write the minimum code needed to solve the requested problem **well**.
- Do not add random extra features, speculative architecture, or unnecessary abstraction.
- But do **not** reduce the solution to a bland or generic version if the product clearly needs stronger structure, hierarchy, or personality.
- Simplicity in `viru-tracker` means:
  - fewer unnecessary moving parts,
  - clearer flows,
  - stronger hierarchy,
  - better grouping,
  - more intentional UI.
- Do not confuse “simple” with “empty”, “plain”, or “default SaaS”.
- If a design or flow is supposed to feel premium, editorial, or distinctive, preserve that intention.
- Prefer direct code over overengineering, but do not remove nuance that makes the experience feel designed.

Rule of thumb:
- If 50 lines solve it clearly, do not write 200.
- But if 50 lines create a dead, generic, low-personality result, that is not the right 50 lines.
- Do not optimize for the smallest implementation at the cost of product quality.

### 3) Surgical changes
- Touch only the code required by the task.
- Do not refactor unrelated areas.
- Do not “clean up” nearby code unless the task explicitly asks for it.
- Match the existing style and conventions of the file you are editing.
- If you notice unrelated problems, mention them separately instead of changing them.

Allowed cleanup:
- Remove imports, variables, functions, or dead paths made unused by your own change.

Not allowed by default:
- Deleting pre-existing dead code
- Reformatting unrelated files
- Renaming things for taste
- Refactoring adjacent modules “while you are there”

Every changed line should be traceable to the user’s request.

### 4) Goal-driven execution
Translate vague requests into verifiable goals.

Examples:
- “Fix the bug” → reproduce it, write a test if feasible, then make the test pass.
- “Add validation” → write failing cases first, then implement until they pass.
- “Refactor X” → preserve behavior and prove it with existing or added checks.

Prefer a tight verification loop:
1. Reproduce
2. Isolate
3. Patch
4. Verify
5. Summarize root cause and evidence

Do not stop at “I changed the code”.
Stop only when success criteria are met.

---

## Repo-specific rules for viru-tracker

### Git and publishing
- Every requested code change that is considered complete must be prepared for GitHub with clean traceability.
- Default workflow is **branch + PR into `main`**, not direct pushes to `main`.
- Use branches named like:
  - `feature/...`
  - `fix/...`
  - `refactor/...`
  - `chore/...`
  - `docs/...`
- Do not merge directly into `main` unless the user explicitly overrides this.
- Do not leave requested changes only locally if the user asked for a real completed change.
- Before proposing a PR-ready state, ensure the diff is intentional and limited to the task.
- If the change is significant, note whether `HISTORY.md` should be updated.

For diagnosis-only work:
- You may investigate locally first.
- Do not claim the issue is fixed until verification is complete.
- When the user asked for a real change, the final result must be ready for PR flow into `main`.

By default, viru-tracker uses a simple single-branch workflow: commit directly to `main` after proper verification.

### Planning and execution
For non-trivial tasks:
- Start with a short plan before editing.
- Keep the plan tied to concrete verification steps.
- If the task becomes long or noisy, compress the context and continue from a clean summary.
- Prefer one clearly defined problem per run instead of mixing unrelated fixes.

### Reusable setup and portability
- When a workflow is repeated often or a missing tool is causing slow fallback work, prefer installing/configuring the right tool once instead of repeating a slower workaround.
- Do this only when the future payoff is clear and the setup cost stays reasonable; do not bloat the repo or violate clarity just to optimize in theory.
- Keep `viru-tracker` as portable as feasible: prefer repo-local dependencies, project scripts, pinned versions, relative paths, and config stored in-repo rather than machine-specific global setup when possible.
- If you improve recurring tooling, leave a short, durable trail: update the relevant doc/script/config so future sessions can reuse it without rediscovering the setup.

---

## Debugging and verification rules

### Debugging rules
For UI, browser, API, and network bugs:
- Reproduce the issue in a real browser before editing code whenever feasible.
- Do not claim a fix based only on unit tests if the bug is visible in the real app.
- Capture the real failing request and the real failing response before patching when the issue is HTTP/network related.

Never claim a bug is fixed without as much of the following as feasible:
- exact failing request
- exact response body
- console output
- server log and/or correlation_id
- failing test before patch
- passing verification after patch

When debugging:
1. Reproduce the issue
2. Identify the smallest failing case
3. Add or update a regression test when feasible
4. Apply the smallest patch possible
5. Re-run the relevant checks
6. Reproduce again in the real flow
7. Summarize root cause in one or two sentences

### Browser-first rule for frontend regressions
For issues visible in the UI:
- Prefer real browser verification over purely synthetic confidence.
- Prefer TestSprite for fast real-flow verification when feasible, especially for reported visual regressions.
- Inspect:
  - console errors
  - network requests
  - request payloads
  - response bodies
  - auth/session state if relevant
  - actual API base URL used by the browser
- If frontend and backend disagree, treat the contract mismatch as a first-class root-cause candidate.

### No invisible verification
- Do not claim a UI fix based on reasoning alone.
- Do not claim a visual fix from code inspection alone.
- Do not claim a browser-visible issue is fixed only because the build passes.
- Avoid endings like:
  - “should be fixed”
  - “likely fixed”
  - “looks correct from the code”
as final verification.

A browser-visible issue is only considered verified if there is visible evidence from one of these paths:
1. **TestSprite**
2. **Screenshots captured by the agent in the real browser flow**

If neither exists, the task is not done.

### TestSprite-first policy
Use TestSprite by default when the task involves:
- multi-step flows
- real navigation between pages
- login/register/account menu behavior
- forms with validation
- dashboards and interactive states
- reported browser regressions
- interactions that depend on real session or API state

Do not skip TestSprite just because the code change seems small.

Do not force TestSprite when:
- the task is a tiny static visual change and screenshots are faster and sufficient
- TestSprite is flaky for that route and manual screenshot verification is more reliable
- the page state is simple enough that 2–4 screenshots fully prove the result

Decision rule:
- use TestSprite for flows
- use screenshots for scoped static verification
- use both when the change is critical

### Screenshot verification protocol
When TestSprite is not used, the agent must capture screenshots itself in the browser.

For a simple UI change:
- 1 screenshot of the full section or page after the change
- 1 screenshot focused on the changed component

For a structural or layout change:
- 1 screenshot of the full page
- 1 screenshot of the changed section
- 1 screenshot showing the interaction result if the component changes state

For stateful UI:
- capture relevant states if affected:
  - default
  - open/expanded
  - empty/error/success if changed

Screenshot rules:
- Prefer full-context screenshots over tiny crops.
- The screenshot must show the real rendered result.
- If the user specifically complained about positioning, spacing, hierarchy, or duplication, capture enough context to prove that exact issue is resolved.

### Tests and verification
Use the smallest set of checks that can prove the change safely.

Verification ladder:
1. Targeted test covering the bug or behavior
2. Nearby related tests
3. Build/typecheck/lint if relevant
4. TestSprite or real browser verification for UI/network issues

Rules:
- Prefer adding a regression test for bug fixes when feasible.
- Do not add broad, slow, speculative tests unrelated to the task.
- Do not rely on “build passes” as proof of a user-visible fix.
- For browser/UI/visual bugs, prefer a quick TestSprite check in the real flow after the patch when feasible.
- If TestSprite is missing or fragile but likely to be reused, prefer spending a bit of time making that path work cleanly instead of repeatedly falling back to slower synthetic-only checks.
- If a test cannot be written or run, say so explicitly and explain why.

“Done” means:
- the root cause is identified,
- the requested behavior is verified,
- relevant tests pass,
- build passes if relevant,
- and browser-visible changes were verified in the real browser with TestSprite or self-captured screenshots.

### Git and publishing
- Every requested code change that is considered complete must be published to GitHub with clean traceability.
- Default workflow is **direct commits to `main`**, not branches or pull requests.
- Do not create feature branches or PRs unless the user explicitly asks for them.
- Do not leave requested changes only locally if the user asked for a real completed change.
- Before committing, ensure the diff is intentional, limited to the task, and free of unrelated edits.
- Use clear Conventional Commits whenever possible:
  - `feat: ...`
  - `fix: ...`
  - `refactor: ...`
  - `docs: ...`
  - `chore: ...`
- If the change is significant, consider whether `HISTORY.md` should be updated.
- Never create multiple parallel GitHub versions of `viru-tracker` by default.
- The expected path is:
  1. make the requested change
  2. verify it properly
  3. commit to `main`
  4. push to GitHub

For diagnosis-only work:
- You may investigate locally first.
- Do not claim the issue is fixed until verification is complete.
- When the user asked for a real change, the final result must be committed and pushed to `main`.

Before publishing:
- check `git status`
- review the diff
- avoid committing unrelated files
- prefer intentional staging over accidental bulk commits when possible

### Required evidence for browser-visible work
For any UI/UX/layout/browser-visible task, the final report must include:
- verification method used:
  - TestSprite
  - screenshots
  - both
- exact page/route tested
- exact interaction performed
- visible result observed
- any limitations

Visible work must be shown, not guessed.

---

## Subagents / parallel work
Use subagents selectively.

Good use cases:
- read-heavy codebase exploration
- browser triage
- backend log analysis
- contract inspection
- documentation lookup

Rules:
- Give each subagent one bounded job and a clear return format.
- Prefer subagents for analysis, not simultaneous write-heavy implementation.
- Only one agent should own code-writing changes for a given fix.
- Merge conclusions before editing.

---

## Scope control
Do not expand scope without permission.

If you find adjacent issues:
- mention them,
- separate them from the requested change,
- and do not silently bundle them into the same fix.

If the user asks for one bug:
- fix one bug,
- do not opportunistically redesign the feature.

But:
- if the requested task is inherently structural (for example, reorganizing a screen, improving hierarchy, adapting a reference, or making the UI feel more polished), do not under-solve it with a mechanically literal implementation.
- In those cases, preserve scope while still solving the real UX problem with judgment.

---

## Code style and conventions
- Follow the existing local style of the repository and file.
- Prefer consistency with surrounding code over personal preference.
- Keep function and variable naming aligned with the existing module.
- Avoid introducing new patterns unless the existing code already uses them or the change clearly requires them.

---

## Documentation
Update docs only when one of these is true:
- the change alters a real contract,
- a workflow changed,
- a command changed,
- a persistent repo rule changed,
- or the user asked for documentation.

When you correct a recurring wrong assumption about the repo, update `AGENTS.md` so future runs inherit the fix.

If the completed work materially changes product behavior or a visible workflow, consider whether `HISTORY.md` should also be updated.

---

## Output expectations
When reporting back after implementation, include:
- what changed
- root cause
- files touched
- how it was verified
- any remaining limitation or uncertainty

For browser-visible work, also include:
- route/page tested
- verification method
- what the visible evidence proves

Keep the summary concise and factual.
Do not overclaim confidence.

---

## Anti-patterns to avoid
- guessing the cause and patching before reproducing
- fixing multiple bugs at once without request
- overengineering
- speculative abstractions
- broad refactors disguised as fixes
- claiming success from tests that do not cover the real failure
- claiming visual success without TestSprite or screenshots
- flattening UI or product personality just to make implementation easier
- turning a strong reference into a generic beige dashboard
- translating a distinctive design into a weak “minimum viable” layout
- leaving requested changes unpublished when the task called for completion
- merging to `main` directly when the default repo workflow is PR-based

---

## Quality bar
These instructions are working if they lead to:
- smaller diffs
- fewer unrelated edits
- fewer speculative fixes
- more reproducible debugging
- clearer verification
- fewer rewrites caused by overcomplication
- clarifying questions or explicit assumptions before implementation, not after mistakes
- stronger results when adapting external inspiration
- less generic UI
- more intentional hierarchy, composition, and personality

---

## Product-specific design rules for viru-tracker

### Viru is not generic SaaS
- Viru Tracker is not a generic dashboard template.
- It has more personality, more editorial intention, and more visual character than a default SaaS admin panel.
- Do not flatten Viru into a generic, over-simplified, low-tension interface.
- Preserve:
  - hierarchy
  - rhythm
  - visual intention
  - premium restraint
  - editorial composition
  - controlled asymmetry where it helps
- The goal is not “plain”.
- The goal is “clear, intentional, sober, and distinctive”.

### When adapting UI/UX from outside
- Treat outside references as structural inspiration, not as literal clones and not as excuses to oversimplify.
- Extract:
  - layout logic
  - interaction patterns
  - hierarchy
  - grouping
  - affordances
  - visual rhythm
- Then adapt them to Viru’s tone and product identity.
- Do not over-adapt them into something ultra-simple, flat, or timid.
- If the source has strong personality, retain an equivalent level of intention in the adaptation.
- Viru should feel more refined, not more generic.

### Design adaptation rule
When the user asks to copy or adapt something from outside:
1. Identify what makes the reference strong:
   - composition
   - spacing
   - density
   - emphasis
   - motion
   - information hierarchy
2. Preserve those strengths in the adaptation
3. Re-skin them into Viru
4. Do not reduce them to a bland “safe” implementation unless explicitly asked

### Simplicity rule for UI
- Simplify logic.
- Simplify flows.
- Simplify friction.
- Do **not** simplify away character.
- Do **not** erase useful density.
- Do **not** remove hierarchy just because it is easier to code.

### Standard for good Viru UI
A good result in `viru-tracker` should feel:
- controlled
- elegant
- slightly editorial
- not noisy
- not empty
- not generic
- clearly designed by someone making deliberate choices

### If in doubt
If two possible implementations exist:
- one is simpler but generic,
- the other is still controlled but has more hierarchy, intention, and product character,

prefer the second.
