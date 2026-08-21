# AGENTS.md — viru-air

This file defines the default operating rules for coding agents working in `viru-air`.

Follow these instructions unless the user explicitly overrides them.

More specific instructions may exist in nested `AGENTS.md` files. When working inside a subdirectory, follow the closest applicable `AGENTS.md` in addition to this root file.

---

## Mission

Complete the requested task end-to-end with a small, intentional, verified change.

`viru-air` is not generic SaaS. It should remain clear, intentional, warm, animated, distinctive, and human, with strong visual taste and a close, approachable feel.

A good result is not merely code that compiles. A good result solves the real task, preserves product character, is verified with appropriate evidence, and is published correctly when the user asked for a completed change.

---

## Highest-priority repo constraints

These rules override softer guidance elsewhere in this file.

- The canonical Git repository is the current `viru-air` root.
- Do not use `_publish_repo` for any workflow.
- Treat `_publish_repo` as a deprecated local artifact that may not exist.
- If the current working directory is not a Git repository, stop and report the problem.
- Never create or maintain mirror folders, secondary publishing repos, or parallel GitHub versions.
- All Git operations, verification, commits, and pushes must happen from the canonical `viru-air` root.
- Default workflow is **direct commits to `main`**, unless the user explicitly asks for a branch or PR.
- Do not create feature branches or PRs unless the user explicitly asks for them.
- Do not leave requested changes only locally if the user asked for a real completed change.
- `users_prueba.txt` is an intentional project file. Do not delete it, replace it, untrack it, or treat its presence as an error unless the user explicitly asks.

Expected path for real completed changes:

1. make the requested change;
2. verify it properly;
3. commit to `main`;
4. push to GitHub.

For diagnosis-only work:

- Investigate locally first.
- Do not claim the issue is fixed until verification is complete.
- Do not commit or push unless the user asked for an actual completed change.

---

## Operating principles

### 1) Think before coding

- Do not assume silently.
- State important assumptions explicitly before implementing.
- If there are multiple plausible interpretations, name them instead of choosing one invisibly.
- Ask a clarification only when the ambiguity blocks a correct implementation or would materially affect architecture, data, security, public behavior, or product direction.
- If the ambiguity is minor, state the assumption briefly and proceed.
- Surface tradeoffs when they matter.

For non-trivial tasks, start with a brief plan:

1. [step] → verify: [check]
2. [step] → verify: [check]
3. [step] → verify: [check]

Keep the plan short, concrete, and tied to verification.

### 2) Bias toward useful action

- Do not stall on avoidable questions.
- Do not end with only a clarification unless genuinely blocked.
- When the likely intent is clear, proceed with a reasonable assumption and mention it.
- Prefer partial verified progress over speculative discussion.
- For long tasks, send brief milestone updates, not noisy logs.

Good pattern:

- “I’ll treat this as a frontend regression on the dashboard route, verify it in browser, then patch the smallest component-level cause.”

Bad pattern:

- “Can you clarify whether you want me to investigate the bug?” when the user already asked to fix it.

### 3) Make surgical, high-quality changes

- Write the minimum code needed to solve the requested problem **well**.
- Do not add random extra features, speculative architecture, or unnecessary abstraction.
- Touch only the code required by the task.
- Do not refactor unrelated areas.
- Do not “clean up” nearby code unless the task explicitly asks for it.
- Match the existing style and conventions of the file you are editing.
- If you notice unrelated problems, mention them separately instead of changing them.
- Every changed line should be traceable to the user’s request.

Allowed cleanup:

- Remove imports, variables, functions, or dead paths made unused by your own change.

Not allowed by default:

- Deleting pre-existing dead code.
- Reformatting unrelated files.
- Renaming things for taste.
- Refactoring adjacent modules “while you are there”.
- Replacing an existing pattern with a personal preference.
- Broad rewrites disguised as small fixes.

### 4) Work from goals to evidence

Translate vague requests into verifiable goals.

Examples:

- “Fix the bug” → reproduce it, isolate root cause, add or update a test if feasible, patch, then verify.
- “Add validation” → define invalid cases, test them if feasible, implement until they pass.
- “Refactor X” → preserve behavior and prove it with existing or added checks.
- “Make this UI better” → identify the UX problem, preserve Viru’s tone, patch the smallest meaningful surface, and verify visually.

Default loop:

1. Reproduce or inspect.
2. Isolate.
3. Patch.
4. Verify.
5. Summarize root cause and evidence.

Do not stop at “I changed the code”.
Stop only when the requested behavior is actually verified or when you can clearly explain what blocked verification.

---

## Canonical documentation

All canonical project documentation lives in `/docs`.

Before assuming architecture, expected behavior, technical decisions, contracts, runbooks, QA rules, or product context, consult `/docs` selectively.

Start with:

- `/docs/README.md`
- `/docs/INDICE_UNICO.md`
- `/docs/DOCS_INVENTORY.md`

Then read only the area relevant to the task:

- overview: `/docs/overview/`
- product: `/docs/product/`
- engineering: `/docs/engineering/`
- references/contracts: `/docs/reference/`
- specs: `/docs/specs/`
- ADRs: `/docs/adr/`
- runbooks: `/docs/runbooks/`
- QA: `/docs/qa/`
- prompts/AI context: `/docs/prompts/`

Use `/docs/archive/` only for historical context or traceability.

If archive content conflicts with live documentation, prefer the live/canonical document.

Prefer documents marked as:

- `Estado: vivo`
- `Fuente de verdad: sí`

Never use these as project documentation:

- `_publish_repo`;
- `node_modules`;
- `.venv`;
- `venv`;
- `.next`;
- caches;
- logs;
- test outputs;
- generated files;
- snapshots;
- dependency docs;
- local artifacts.

`users_prueba.txt` is not documentation, but it is intentionally kept in the project. Do not delete it or treat it as a documentation source.

Read only what is needed for the current task. If sources conflict, report the conflict instead of inventing a synthesis. If information is missing, state it clearly and leave a verifiable TODO.

See `/docs/AGENTS.md` for documentation-specific rules.

---

## Design context for agents

For UI/UX work driven by coding agents, use `/DESIGN.md` as the sole design source of truth. `/.codex/skills/viru-air-ui/SKILL.md` exists only to enforce that reading.

Rules:

- Treat `/DESIGN.md` as the active contract for UI proposals and incremental improvements.
- Preserve its dual-theme direction: Aviation Dark-Luxe at night and its luminous, non-generic counterpart by day.
- Use neither design guidance nor the skill to justify logic, route or API contract changes.
- If the design source changes location or scope, update `/docs/DOCS_INVENTORY.md` and `/docs/INDICE_UNICO.md` in the same change.

---

## Frontend component guidance: shadcn/ui

shadcn/ui is a known, preferred option for reusable frontend primitives in Viru Air, especially when the user explicitly asks for "shadcn", "shadcn/ui", "usa cosas de shadcn", "utiliza shadcn", or similar wording. It is not the design authority for Viru Air, and it must not override the product identity, existing design contract, or local component patterns by default.

Current repo state:

- Frontend app root: `/frontend`.
- Stack: Next.js 15, React 19, TypeScript, custom CSS modules/files under `/frontend/src/styles`.
- Package manager: npm, with `/frontend/package-lock.json`.
- Alias: `@/*` maps to `/frontend/src/*`.
- shadcn/ui is not currently initialized: no `/frontend/components.json` was present when this guidance was written.
- `/frontend/src/components/ui` exists, but currently contains project UI such as `map.tsx`; do not assume it is a shadcn-generated component library.
- No shared `/frontend/src/lib/utils.ts` or `cn` helper was present when this guidance was written.
- Tailwind was not configured when this guidance was written; no Tailwind config or Tailwind dependency was present in `/frontend/package.json`.

Usage rules:

- When the user explicitly asks for shadcn/ui, use shadcn/ui components where they fit the requested UI.
- When creating new frontend, consider shadcn/ui for common primitives before hand-rolling another generic button/input/dialog pattern.
- Prefer existing Viru Air components and established local patterns before adding new shadcn/ui components.
- Do not force shadcn/ui if a project-specific component already fits better, if the requested change is small, or if adding shadcn would create excessive setup or visual churn.
- Do not run a mass migration to shadcn/ui without an explicit task asking for that migration.
- Do not replace existing UI only to "normalize" it to shadcn/ui.
- Keep Viru Air's warm aeronautical identity, dual-theme direction, motion character, spacing rhythm, and existing visual hierarchy.
- If a needed shadcn/ui component is missing, add it with the official shadcn CLI from `/frontend` using npm.
- If shadcn/ui must be initialized for a task, initialize it minimally and verify the generated paths, aliases, Tailwind setup, tokens, and `cn` helper before using generated imports.

Good shadcn/ui candidates:

- Buttons, inputs, textareas, checkboxes, radios, switches, selects, tabs, badges, alerts, skeletons, simple cards, dialogs, sheets, dropdown menus, popovers, tooltips, toasts, and simple forms.

Do not force shadcn/ui for:

- Highly specific Viru Air surfaces, already-designed layouts, aviation/radar/route visuals, map components, timeline and fare intelligence views, custom empty states, complex domain flows, or logic-heavy components already encapsulated in the app.

Command examples:

```bash
cd frontend
npm exec shadcn@latest -- init
npm exec shadcn@latest -- add button input card dialog sheet dropdown-menu select tabs badge alert skeleton form
```

Style guardrails:

- Use Tailwind together with shadcn/ui when shadcn is introduced for a task.
- Preserve existing project tokens and CSS variables when they exist; adapt shadcn components to Viru's tokens instead of hardcoding a new palette.
- Avoid hardcoding new colors, radii, shadows, or base spacing unless the task truly requires it.
- Do not introduce global visual changes as a side effect of adding one component.
- Do not change themes, radius, base colors, global CSS, or the overall design system unless the user explicitly asks for that scope.

---

## Verification standard

Use the smallest set of checks that can prove the change safely.

Verification ladder:

1. Targeted test covering the bug or behavior.
2. Nearby related tests.
3. Build/typecheck/lint if relevant.
4. Real browser, API, or integration verification when the behavior depends on runtime state.

Rules:

- Prefer adding a regression test for bug fixes when feasible.
- Assume Playwright/Chromium are already available in this repo workflow; do not reinstall them unless a concrete missing-binary/version error proves it is necessary.
- Before creating new browser automation flows, reuse existing frontend tests/scripts and prior QA reports from `docs/qa/` whenever they already cover the same auth/session journey.
- Do not add broad, slow, speculative tests unrelated to the task.
- Do not rely on “build passes” as proof of a user-visible fix.
- If a test cannot be written or run, say so explicitly and explain why.
- Never claim a bug is fixed without evidence.
- Avoid final wording like:
  - “should be fixed”;
  - “likely fixed”;
  - “looks correct from the code”.

For UI, browser, API, and network bugs:

- Reproduce the issue before editing whenever feasible.
- Capture the real failing request and real failing response when the issue is HTTP/network related.
- Inspect console output, server logs, API payloads, response bodies, auth/session state, and actual runtime configuration when relevant.
- If frontend and backend disagree, treat the contract mismatch as a first-class root-cause candidate.
- For visual/UI validation, request manual user review in the real UI and collect explicit feedback (route, interaction, expected result, observed result).
- Build/tests/lint/typecheck in terminal remain the AI's responsibility when relevant.

“Done” means:

- the root cause is identified when applicable;
- the requested behavior is verified;
- relevant tests pass;
- build/typecheck/lint pass if relevant;
- browser-visible changes are verified with visible evidence when applicable;
- the final result is committed and pushed when the user asked for a completed change.

For browser-visible work, follow the more specific rules in `/frontend/AGENTS.md` and `/tests/AGENTS.md`.

---

## Product identity

### Viru is not generic SaaS

- Viru Air is not a generic dashboard template.
- It has more personality, more art-directed intention, and more visual character than a default SaaS admin panel.
- Do not flatten Viru into a generic, over-simplified, low-tension interface.
- “Not generic SaaS” means more personality, not less.

Preserve:

- hierarchy;
- rhythm;
- visual intention;
- premium warmth;
- warm aeronautical character with personality;
- controlled asymmetry where it helps;
- useful density;
- strong grouping;
- clear information priority;
- microcopy that feels close and alive;
- subtle motion that adds clarity, delight, continuity, and personality.

The goal is not “plain”.
The goal is “clear, warm, memorable, and distinctive without noise”.

### Warm identity principles

For design direction and reviews, apply these principles:

1. Warmth before coldness.
2. Personality before neutrality.
3. Intentional motion, not immobility.
4. Clarity without austerity.
5. Premium but close, never distant or austere.
6. Aeronautical aesthetic, not airline-corporate UI.
7. Light mode must have soul, not flat generic white.
8. Dark mode can be cinematic, never gloomy.
9. The interface must feel designed, alive, and cared for, not assembled.
10. Small details should make people smile without getting in the way.

### Simplicity rule

Simplicity in `viru-air` means:

- fewer unnecessary moving parts;
- clearer flows;
- stronger hierarchy;
- better grouping;
- more intentional UI.

Do not confuse “simple” with “empty”, “plain”, or “default SaaS”.

If two possible implementations exist:

- one is simpler but generic;
- the other is still controlled but has more hierarchy, intention, and product character;

prefer the second.

### Dual-theme rule

- Viru is dual-theme by contract: dark and light must share the same warm/aeronautical personality.
- Do not document or implement Viru as dark-only unless the user explicitly asks for that scope.
- Keep cues and semantics consistent across themes (IATA/rutas/terminales/radar, hierarchy, accent behavior, and state meaning).

Detailed frontend, visual hierarchy, adaptation, screenshot, and browser QA rules belong in `/frontend/AGENTS.md`.

---

## Git and publishing

Before committing:

- run `git status`;
- review the diff;
- stage only intentional files;
- avoid unrelated edits;
- verify from the canonical repo root.

Use clear Conventional Commits whenever possible:

- `feat: ...`
- `fix: ...`
- `refactor: ...`
- `docs: ...`
- `chore: ...`

If the change is significant, consider whether `HISTORY.md` should be updated.

Do not update `HISTORY.md` for every tiny change. Update it when the completed work materially changes product behavior, a visible workflow, public behavior, or an important repo/process rule.

---

## Scope control

Do not expand scope without permission.

If you find adjacent issues:

- mention them;
- separate them from the requested change;
- do not silently bundle them into the same fix.

If the user asks for one bug:

- fix one bug;
- do not opportunistically redesign the feature.

But:

- if the requested task is inherently structural, such as reorganizing a screen, improving hierarchy, adapting a reference, or making the UI feel more polished, do not under-solve it with a mechanically literal implementation;
- in those cases, preserve scope while still solving the real UX problem with judgment.

---

## Subagents and parallel work

Use subagents selectively.

Good use cases:

- read-heavy codebase exploration;
- browser triage;
- backend log analysis;
- contract inspection;
- documentation lookup;
- comparing multiple possible causes before one implementation owner edits code.

Rules:

- Give each subagent one bounded job and a clear return format.
- Prefer subagents for analysis, not simultaneous write-heavy implementation.
- Only one agent should own code-writing changes for a given fix.
- Merge conclusions before editing.
- Do not use subagents to avoid understanding the final change yourself.

---

## Code style and conventions

- Follow the existing local style of the repository and file.
- Prefer consistency with surrounding code over personal preference.
- Keep function and variable naming aligned with the existing module.
- Avoid introducing new patterns unless the existing code already uses them or the change clearly requires them.
- Prefer direct, readable code over cleverness.
- Do not introduce new dependencies unless they clearly improve the requested task and fit the project’s existing stack.

---

## Reusable setup and portability

- When a workflow is repeated often or a missing tool is causing slow fallback work, prefer installing/configuring the right repo-local tool once instead of repeating a slower workaround.
- Do this only when the future payoff is clear and the setup cost stays reasonable.
- Do not bloat the repo or violate clarity just to optimize in theory.
- Keep `viru-air` portable:
  - prefer repo-local dependencies;
  - prefer project scripts;
  - prefer pinned versions;
  - prefer relative paths;
  - prefer config stored in-repo rather than machine-specific global setup.
- If you improve recurring tooling, leave a short durable trail in the relevant doc, script, or config so future sessions can reuse it.

---

## Documentation updates

Update docs only when one of these is true:

- the change alters a real contract;
- a workflow changed;
- a command changed;
- a persistent repo rule changed;
- the user asked for documentation.

When you correct a recurring wrong assumption about the repo, update `AGENTS.md` so future runs inherit the fix.

If the completed work materially changes product behavior or a visible workflow, consider whether `HISTORY.md` should also be updated.

Do not update documentation just to create the appearance of completeness.

---

## Communication and responsiveness

Before tool-heavy work:

- acknowledge the task briefly;
- state the working assumption if needed;
- give a short plan tied to verification.

During longer work:

- send brief progress updates at real milestones;
- mention useful findings as soon as they are known;
- avoid noisy step-by-step logs;
- do not repeatedly restate the same plan.

When blocked:

- say exactly what blocks progress;
- say what evidence you already gathered;
- give the smallest next decision needed.

Do not over-explain obvious changes. The final report should be concise and factual.

---

## Output expectations

When reporting back after implementation, include:

- what changed;
- root cause, when applicable;
- files touched;
- how it was verified;
- any remaining limitation or uncertainty.

For browser-visible work, also include:

- route/page tested;
- verification method;
- exact interaction performed;
- what the visible evidence proves.

Keep the summary concise and factual.

Do not overclaim confidence.

Avoid:

- “should be fixed” as final proof;
- “I think it works”;
- “looks fine from the code”;
- long generic summaries that do not mention verification evidence.

---

## Anti-patterns to avoid

- guessing the cause and patching before reproducing;
- fixing multiple bugs at once without request;
- overengineering;
- speculative abstractions;
- broad refactors disguised as fixes;
- claiming success from tests that do not cover the real failure;
- claiming visual success without real browser evidence;
- flattening UI or product personality just to make implementation easier;
- leaving requested changes unpublished when the task called for completion;
- using `_publish_repo` or any secondary mirror as a fallback repository;
- creating parallel GitHub versions of `viru-air`;
- committing from any directory other than the canonical `viru-air` root;
- asking avoidable clarifying questions instead of making a safe assumption and proceeding;
- producing a large diff when a small, verified patch would solve the task.

---

## Nested guidance map

Use this root file for universal repo rules.

Use nested `AGENTS.md` files for specialized guidance:

- `/frontend/AGENTS.md`:
  - UI implementation;
  - visual hierarchy;
  - browser verification;
  - screenshots;
  - manual user visual review;
  - frontend contracts.

- `/backend/AGENTS.md`:
  - API behavior;
  - backend debugging;
  - server logs;
  - database/migration safety;
  - service-level verification.

- `/docs/AGENTS.md`:
  - documentation style;
  - canonical docs workflow;
  - inventory updates;
  - archive rules;
  - HISTORY updates.

- `/tests/AGENTS.md`:
  - testing strategy;
  - regression tests;
  - terminal test automation;
  - visual evidence;
  - stable test data.

Do not split guidance further unless repeated work proves that a more local instruction file would materially improve future agent behavior.

<!-- OMA:START — managed by oh-my-agent. Do not edit this block manually. -->

# oh-my-agent

## Architecture

- **SSOT**: `.agents/` directory (do not modify directly)
- **Response language**: Follows `language` in `.agents/oma-config.yaml`
- **Skills**: `.agents/skills/` (domain specialists)
- **Workflows**: `.agents/workflows/` (multi-step orchestration)
- **Subagents**: Same-vendor native dispatch via Codex custom agents in `.codex/agents/{name}.toml`; cross-vendor fallback via `oma agent:spawn`

## Per-Agent Dispatch

1. Resolve `target_vendor_for_agent` from `.agents/oma-config.yaml`.
2. If `target_vendor_for_agent === current_runtime_vendor`, use the runtime's native subagent path.
3. If vendors differ, or native subagents are unavailable, use `oma agent:spawn` for that agent only.

## Code Search

Prefer **serena MCP** tools over native find/grep when locating code — they are symbol-aware and faster on large repos. Fall back to native Read / Glob / Grep only when serena is unavailable or for plain file content reads.

| Task | Preferred tool |
|------|----------------|
| Locate a symbol definition (class / function / variable) | `find_symbol` |
| Find references / callers of a symbol | `find_referencing_symbols` |
| Outline a file's top-level symbols | `get_symbols_overview` |
| Pattern or regex search across the codebase | `search_for_pattern` |
| Find a file by name | `find_file` |
| List directory contents | `list_dir` |

## Workflows

Execute by naming the workflow in your prompt. Keywords are auto-detected via hooks.

| Workflow | File | Description |
|----------|------|-------------|
| orchestrate | `orchestrate.md` | Parallel subagents + Review Loop |
| work | `work.md` | Step-by-step with remediation loop |
| ultrawork | `ultrawork.md` | 5-Phase Gate Loop (11 reviews) |
| ralph | `ralph.md` | Persistent loop wrapping ultrawork with an independent judge |
| plan | `plan.md` | PM task breakdown |
| brainstorm | `brainstorm.md` | Design-first ideation |
| architecture | `architecture.md` | Architecture diagnosis, comparison, ADR |
| design | `design.md` | Design system + DESIGN.md with anti-pattern enforcement |
| review | `review.md` | QA audit |
| debug | `debug.md` | Root cause + minimal fix |
| deepsec | `deepsec.md` | Drive `oma-deepsec` end-to-end (setup / scan / pr-review / matchers / triage) |
| scm | `scm.md` | SCM + Git operations + Conventional Commits |
| docs | `docs.md` | Documentation drift verify + sync |
| recap | `recap.md` | Daily / period AI conversation recap |
| deepinit | `deepinit.md` | Project harness init (AGENTS.md / ARCHITECTURE.md / docs/) |
| convert | `convert.md` | File format conversion by category: documents→Markdown (oma-pdf/oma-hwp), image/video/audio transcode (ffmpeg) |
| video | `video.md` | Brief → script → assets → render-spec → Remotion (oma-video) |
| schedule | `schedule.md` | Register & manage time-based agent jobs via `oma schedule:*` |

(`tools` and `stack-set` are slash-invoked utilities, and `schedule` is a slash-invoked workflow (`oma schedule:*` time-based jobs); all are intentionally excluded from keyword detection.)

To execute: read and follow `.agents/workflows/{name}.md` step by step.

## Auto-Detection

Hooks: `UserPromptSubmit` (keyword detection), `PreToolUse`, `Stop` (persistent mode)
Keywords defined in `.agents/hooks/core/triggers.json` (multi-language).
Persistent workflows (orchestrate, ultrawork, work, ralph) block termination until complete.
Deactivate: say "workflow done".

## Rules

1. **Do not modify `.agents/` files** (SSOT protection).
2. Workflows execute via keyword detection or explicit naming, never self-initiated.
3. Response language follows `.agents/oma-config.yaml`

## Project Rules

Read the relevant file from `.agents/rules/` when working on matching code.

| Rule | File | Scope |
|------|------|-------|
| backend | `.agents/rules/backend.md` | on request |
| commit | `.agents/rules/commit.md` | on request |
| database | `.agents/rules/database.md` | **/*.{sql,prisma} |
| debug | `.agents/rules/debug.md` | on request |
| design | `.agents/rules/design.md` | on request |
| dev-workflow | `.agents/rules/dev-workflow.md` | on request |
| frontend | `.agents/rules/frontend.md` | **/*.{tsx,jsx,css,scss} |
| i18n-arb | `.agents/rules/i18n-arb.md` | **/*.arb |
| i18n-guide | `.agents/rules/i18n-guide.md` | always |
| infrastructure | `.agents/rules/infrastructure.md` | **/*.{tf,tfvars,hcl} |
| market | `.agents/rules/market.md` | on request |
| mobile | `.agents/rules/mobile.md` | **/*.{dart,swift,kt} |
| quality | `.agents/rules/quality.md` | on request |

<!-- OMA:END -->
