# docs/AGENTS.md — viru-tracker documentation rules

This file defines documentation-specific rules for coding agents working inside `/docs`.

The root `/AGENTS.md` still applies. This file adds specific guidance for canonical documentation, inventory updates, archive handling, documentation style, and `HISTORY.md`.

---

## Documentation mission

Documentation work must make `viru-tracker` easier to understand, maintain, verify, and continue.

A good documentation change is:

- accurate;
- concise;
- easy to navigate;
- consistent with the canonical docs structure;
- traceable to real product, engineering, or workflow behavior;
- not padded with speculative or decorative content.

Do not update docs just to appear thorough. Update docs when they preserve useful knowledge or reflect a real change.

---

## Canonical documentation source

All canonical project documentation lives in `/docs`.

Before documenting architecture, expected behavior, technical decisions, contracts, runbooks, QA rules, or product context, check the relevant canonical docs selectively.

Start with:

- `/docs/README.md`
- `/docs/INDICE_UNICO.md`
- `/docs/DOCS_INVENTORY.md`

Then read only the area relevant to the task:

- `/docs/overview/`
- `/docs/product/`
- `/docs/engineering/`
- `/docs/reference/`
- `/docs/specs/`
- `/docs/adr/`
- `/docs/runbooks/`
- `/docs/qa/`
- `/docs/prompts/`

Use `/docs/archive/` only for historical context or traceability.

If archive content conflicts with live documentation, prefer the live/canonical document.

---

## Source-of-truth rules

Prefer documents marked as:

- `Estado: vivo`
- `Fuente de verdad: sí`

Use `/docs/DOCS_INVENTORY.md` to check whether a document is live, archived, duplicated, sensitive, pending manual review, or source of truth.

If sources conflict:

- do not invent a synthesis;
- report the conflict clearly;
- prefer live source-of-truth docs over archived or duplicated material;
- leave a verifiable TODO if the correct source cannot be determined.

If information is missing:

- state what is missing;
- avoid pretending the docs are complete;
- add a TODO only if it helps future maintainers resolve the gap.

---

## Valid and invalid documentation sources

Valid documentation sources include:

- live files under `/docs`;
- relevant source code when documenting actual behavior;
- tests when documenting verified behavior;
- canonical specs, ADRs, runbooks, and reference docs.

Never treat these as project documentation:

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
- local artifacts;
- secrets;
- private user data.

`users_prueba.txt` is intentional project data, not documentation. Do not delete it, rewrite it, cite it as docs, or treat its presence as an error unless the user explicitly asks.

Do not create or preserve documentation that exposes secrets, API keys, tokens, credentials, private user data, production dumps, or security-sensitive details that do not belong in repo docs.

If sensitive information is found:

- do not spread it into more files;
- remove or redact it if the task allows;
- mention the issue clearly in the final report;
- recommend rotation only when a real secret exposure is evident.

---

## When to update docs

Update docs only when one of these is true:

- the user asked for documentation;
- architecture changed;
- product behavior changed;
- a public or internal contract changed;
- a setup command changed;
- a workflow or runbook changed;
- a QA or verification rule changed;
- a persistent repo rule changed;
- a recurring wrong assumption needs to be corrected.

Do not update docs for:

- tiny internal refactors with no behavior or workflow change;
- cosmetic code changes;
- speculative future ideas unless the user asked for planning docs;
- broad “cleanup” not tied to a real need;
- generated content that duplicates existing docs.

When a change affects code and docs, keep them consistent in the same completed change when feasible.

---

## Documentation placement

Place documentation in the most specific appropriate area:

- Product context → `/docs/product/`
- Architecture and engineering decisions → `/docs/engineering/`
- API/contracts/reference material → `/docs/reference/`
- Product or technical specs → `/docs/specs/`
- Architecture decisions → `/docs/adr/`
- Operational procedures → `/docs/runbooks/`
- QA and verification workflows → `/docs/qa/`
- AI/agent guidance and prompt strategy → `/docs/prompts/`
- Historical or superseded material → `/docs/archive/`

Do not create new top-level documentation folders unless the existing structure clearly cannot fit the material.

Do not add root-level docs unless the user explicitly asks or the file is a standard repo entrypoint.

---

## DOCS_INVENTORY.md

Update `/docs/DOCS_INVENTORY.md` when documentation is:

- added;
- deleted;
- moved;
- archived;
- renamed;
- promoted to source of truth;
- marked duplicated, sensitive, stale, or pending manual review.

Inventory entries should make it clear:

- what the document is for;
- whether it is live or archived;
- whether it is a source of truth;
- whether it needs manual review;
- whether it supersedes or duplicates another document.

Do not let the inventory become aspirational. It should describe the actual docs that exist.

---

## Archive rules

Use `/docs/archive/` for historical context, superseded docs, old plans, deprecated decisions, and traceability.

When archiving a document:

- preserve useful historical context;
- make clear that it is not the current source of truth;
- update `/docs/DOCS_INVENTORY.md`;
- link or mention the live replacement when one exists.

Do not use archive docs as canonical guidance if a live doc conflicts with them.

Do not delete historical docs unless the user explicitly asks or they contain sensitive information that should not remain in the repo.

---

## Documentation style

Write docs that are practical and maintainable.

Prefer:

- clear headings;
- short paragraphs;
- concrete commands;
- explicit assumptions;
- examples when they reduce ambiguity;
- links or references to canonical docs when useful;
- TODOs that are specific and verifiable.

Avoid:

- vague motivational text;
- repeated explanations across many files;
- huge walls of prose;
- undocumented acronyms;
- speculative architecture;
- stale roadmap promises;
- copying content from old docs without checking current truth;
- saying something is canonical if it is not marked or supported as such.

Keep wording direct. A future agent should be able to act from the doc without asking what it means.

Preserve the language and naming style of the document being edited. If a document uses Spanish metadata such as `Estado: vivo`, `Fuente de verdad: sí`, or `Pendiente de revisión`, keep that style consistent.

Do not rename concepts, routes, services, files, or workflows for taste. Use the names that appear in the codebase and canonical docs.

---

## Special document types

When documenting contracts or specs:

- include the exact route, method, event, command, schema, or workflow when applicable;
- distinguish current behavior from desired behavior;
- distinguish verified facts from assumptions;
- keep request/response examples consistent with code, tests, or observed behavior;
- update related frontend/backend references when a contract changes.

Runbooks should include:

- purpose;
- prerequisites;
- commands;
- expected output or success criteria;
- rollback or recovery notes when relevant;
- common failure modes;
- verification steps.

Use ADRs only for durable decisions that affect architecture, contracts, infrastructure, data, security, or long-term maintainability.

ADRs should include:

- context;
- decision;
- consequences;
- alternatives considered when useful;
- date/status if the existing ADR style uses them.

Do not create ADRs for tiny implementation choices.

Do not rewrite old ADRs to pretend history changed. Add a new ADR or mark supersession when decisions evolve.

---

## HISTORY.md

Consider updating `HISTORY.md` when the completed work materially changes:

- product behavior;
- user-visible workflows;
- public API behavior;
- operational workflows;
- setup commands;
- major verification or QA expectations;
- important repo rules.

Do not update `HISTORY.md` for every tiny fix, cosmetic change, or internal refactor.

When updating `HISTORY.md`:

- keep entries concise;
- describe user-visible or maintainer-relevant impact;
- do not include noisy implementation details;
- keep the existing format.

---

## AGENTS.md and prompt documentation

Update agent/prompt docs when a recurring wrong assumption, workflow error, or repo-specific behavior should be inherited by future agents.

Good reasons include:

- Codex keeps using the wrong repo path;
- verification expectations changed;
- canonical docs moved;
- a tool or workflow became standard;
- a project-specific file must not be touched;
- frontend/backend/test rules need clearer local guidance.

Do not overfit `AGENTS.md` to one isolated mistake if the general rule already exists.

---

## Documentation verification

Before finishing documentation work:

- check that links/paths are correct when feasible;
- check that referenced files actually exist when feasible;
- check that the doc does not conflict with live source-of-truth docs;
- check that inventory updates match the actual files changed;
- run formatting or lint checks if the project has docs checks.

If verification cannot be completed, say exactly what was not checked and why.

---

## Final report for docs work

The final response must include:

- what documentation changed;
- files touched;
- why the change was needed;
- whether `/docs/DOCS_INVENTORY.md` was updated or why it was not needed;
- whether `HISTORY.md` was updated or why it was not needed;
- any remaining uncertainty or TODO.

Do not claim docs are canonical, complete, or verified unless the relevant checks were actually performed.

---

## Documentation anti-patterns

Avoid:

- treating archive docs as current truth;
- creating duplicate docs instead of updating the canonical one;
- adding broad documentation “cleanup” unrelated to the task;
- writing speculative architecture as fact;
- updating `HISTORY.md` for noise;
- forgetting `/docs/DOCS_INVENTORY.md` after adding, moving, or archiving docs;
- copying stale content forward without checking it;
- using generated files, caches, logs, or local artifacts as documentation sources;
- documenting behavior that was not verified or supported by code/docs;
- exposing secrets or private data in docs.