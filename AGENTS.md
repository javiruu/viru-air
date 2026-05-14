# AGENTS.md — viru-tracker

This file defines the default operating rules for coding agents working in `viru-tracker`.

Follow these instructions unless the user explicitly overrides them.

More specific instructions may exist in nested `AGENTS.md` files. When working inside a subdirectory, follow the closest applicable `AGENTS.md` in addition to this root file.

---

## Mission

Complete the requested task end-to-end with a small, intentional, verified change.

`viru-tracker` is not generic SaaS. It should remain clear, controlled, sober, distinctive, and slightly editorial, while still having personality and feeling user-friendly, warm, approachable, and close.

A good result is not merely code that compiles. A good result solves the real task, preserves product character, is verified with appropriate evidence, and is published correctly when the user asked for a completed change.

---

## Highest-priority repo constraints

These rules override softer guidance elsewhere in this file.

- The canonical Git repository is the current `viru-tracker` root.
- Do not use `_publish_repo` for any workflow.
- Treat `_publish_repo` as a deprecated local artifact that may not exist.
- If the current working directory is not a Git repository, stop and report the problem.
- Never create or maintain mirror folders, secondary publishing repos, or parallel GitHub versions.
- All Git operations, verification, commits, and pushes must happen from the canonical `viru-tracker` root.
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

For UI/UX work driven by coding agents, use these local artifacts as persistent design context:

- `/DESIGN.md` (canonical design direction for agents in this repo root);
- `/.codex/skills/viru-tracker-ui/SKILL.md`;
- `/.codex/skills/viru-tracker-ui/references/product-context.md`;
- `/.codex/skills/viru-tracker-ui/references/visual-direction.md`;
- `/.codex/skills/viru-tracker-ui/references/qa-checklist.md`.

Rules:

- Treat `/DESIGN.md` as the active design contract for agent-driven UI proposals and incremental improvements.
- Keep it aligned with canonical UI docs in `/docs/ui` (`estetica.md`, `UI_CONTRACT_V1.md`, `UI_SYSTEM_V1.md`, `UI_VISUAL_QA_CHECKLIST.md`).
- Use the skill/references to guide tone, hierarchy, and QA expectations; do not use them to justify logic, route, or API contract changes.
- If these files are added, moved, renamed, or archived, update `/docs/DOCS_INVENTORY.md` and `/docs/INDICE_UNICO.md` in the same change.

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
- Before creating new Playwright/TestSprite flows, reuse existing frontend tests/scripts and prior QA reports from `docs/qa/` whenever they already cover the same auth/session journey.
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

- Viru Tracker is not a generic dashboard template.
- It has more personality, more editorial intention, and more visual character than a default SaaS admin panel.
- Do not flatten Viru into a generic, over-simplified, low-tension interface.

Preserve:

- hierarchy;
- rhythm;
- visual intention;
- premium restraint;
- editorial composition;
- controlled asymmetry where it helps;
- useful density;
- strong grouping;
- clear information priority.

The goal is not “plain”.
The goal is “clear, intentional, sober, and distinctive”.

### Simplicity rule

Simplicity in `viru-tracker` means:

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
- Keep `viru-tracker` portable:
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
- creating parallel GitHub versions of `viru-tracker`;
- committing from any directory other than the canonical `viru-tracker` root;
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
  - TestSprite usage;
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
  - TestSprite/test automation;
  - visual evidence;
  - stable test data.

Do not split guidance further unless repeated work proves that a more local instruction file would materially improve future agent behavior.
