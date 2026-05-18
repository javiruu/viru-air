# backend/AGENTS.md — viru-tracker backend rules

This file defines backend-specific rules for coding agents working inside the backend area of `viru-tracker`.

The root `/AGENTS.md` still applies. This file adds specific guidance for API behavior, backend debugging, service contracts, logs, data safety, and service-level verification.

---

## Backend mission

Backend work must be:

- correct;
- traceable;
- secure by default;
- compatible with documented contracts;
- safe for existing data and user-facing flows;
- verified with the smallest meaningful checks.

When backend payloads drive UI presentation (status, labels, metadata), preserve theme-agnostic semantics so dark/light rendering can remain consistent in frontend contracts.

Do not treat backend work as only “making tests pass”. A backend change is complete only when the real behavior, contract, failure mode, and evidence are understood.

---

## Backend operating principles

When editing backend code:

- Make the smallest meaningful change that solves the real behavior problem.
- Match the existing architecture, naming, error style, validation style, and module boundaries.
- Do not introduce a new service pattern, abstraction, dependency, or framework unless the task clearly requires it.
- Do not change public API behavior accidentally.
- Do not hide backend bugs with frontend-only assumptions.
- Do not weaken validation, authorization, data consistency, or observability for convenience.
- If a change affects public behavior, check the relevant docs or contracts before implementing.

For backend changes, think in terms of:

1. caller/user goal;
2. API or service contract;
3. validation and authorization;
4. data impact;
5. failure modes;
6. verification evidence.

---

## API contract rules

When changing or debugging an API endpoint:

- Identify the route, method, request shape, response shape, and status codes involved.
- Preserve existing public contracts unless the user explicitly asked to change them.
- If a contract must change, update the relevant docs and frontend expectations.
- Do not guess request/response shapes when docs, types, tests, or real traffic are available.
- Treat frontend/backend mismatch as a first-class root-cause candidate.
- Keep error responses consistent with existing backend conventions.
- Avoid returning misleading success responses when the underlying operation failed.

For API-backed bugs, capture when feasible:

- exact failing request;
- request payload;
- response status;
- response body;
- relevant server log;
- correlation/request id if available.

---

## Validation and authorization

Do not weaken validation or authorization to make a test or flow pass.

When touching validation:

- preserve existing required fields unless the task asks otherwise;
- validate at the correct boundary;
- return useful errors consistent with existing conventions;
- cover important invalid cases when feasible;
- avoid duplicating validation logic across layers unless the existing architecture does so.

When touching authorization or session-dependent behavior:

- verify the user/session context used by the backend;
- preserve least-privilege behavior;
- check both allowed and disallowed paths when feasible;
- do not trust client-provided identity or role fields unless that is already the established pattern;
- avoid exposing sensitive data in responses or logs.

---

## Data and migration safety

Be conservative with persistent data.

Before changing database logic, migrations, schemas, seeds, or destructive operations:

- inspect the existing model/schema and related docs;
- understand whether the change is backward-compatible;
- identify possible data loss, data drift, or migration-order risks;
- prefer additive or reversible changes when feasible;
- do not delete or rewrite data unless the user explicitly asked and the impact is understood.

For migrations:

- follow existing migration naming, style, and tooling;
- avoid editing already-applied migrations unless the project convention allows it;
- add a new migration for schema changes when appropriate;
- include rollback/down behavior if the project supports it;
- verify migration application with the project’s normal command when feasible.

For seeds/test data:

- do not alter stable test data casually;
- keep seed changes minimal and traceable to the task;
- avoid introducing data that hides the real bug.

---

## Error handling and observability

Backend failures should be diagnosable.

When changing error handling:

- preserve existing error format and status-code conventions;
- do not swallow exceptions silently;
- avoid leaking sensitive internals to clients;
- include enough context in logs to debug the issue;
- keep logs concise and useful;
- preserve correlation/request ids if the project uses them.

When debugging:

- check server logs before guessing;
- distinguish client errors, server errors, validation errors, auth errors, and dependency failures;
- identify the smallest failing case;
- summarize root cause in one or two sentences.

---

## Backend debugging loop

For backend bugs:

1. Reproduce the issue with the real route, command, job, or service path whenever feasible.
2. Capture the failing request/input and failing output/error.
3. Inspect logs and relevant contract/docs.
4. Isolate the smallest failing unit or integration path.
5. Add or update a regression test when feasible.
6. Patch the smallest responsible surface.
7. Re-run targeted tests.
8. Run broader checks only when relevant.
9. Verify the real route, command, job, or service path again.
10. Summarize root cause and evidence.

Do not claim the issue is fixed because the code “looks right”.

---

## External services and integrations

When backend behavior depends on external services, queues, storage, email, auth providers, telemetry, or third-party APIs:

- identify the dependency and failure mode;
- avoid hardcoding environment-specific values;
- preserve existing configuration patterns;
- do not commit secrets, tokens, credentials, or private data;
- handle timeouts and failure responses consistently with existing patterns;
- avoid making live destructive calls unless the user explicitly asked and the environment is safe.

If an integration cannot be verified locally, say exactly what was mocked, simulated, or left unverified.

---

## Security and privacy

Do not introduce security regressions.

When touching backend code:

- do not expose secrets in logs, errors, fixtures, or docs;
- do not return private user data unless the contract requires it;
- do not bypass authentication or authorization checks;
- do not trust client-controlled values for identity, ownership, or permissions;
- avoid SQL/string injection risks;
- avoid unsafe filesystem paths or shell command construction;
- keep CORS, cookies, sessions, and tokens consistent with existing security assumptions.

If a requested change appears to weaken security, stop and explain the risk before implementing.

---

## Performance and reliability

Do not prematurely optimize, but avoid obvious backend regressions.

When changing data access, loops, jobs, or heavy endpoints:

- avoid obvious N+1 queries;
- avoid unbounded queries when pagination or filtering exists;
- preserve existing caching behavior unless intentionally changing it;
- avoid blocking long-running work in request/response paths unless already established;
- consider timeout, retry, and idempotency behavior when relevant.

If performance is part of the task, verify with the smallest meaningful measurement available.

---

## Backend tests

Prefer the smallest meaningful test that proves the behavior.

Use backend tests when:

- an API contract changed;
- a bug can be reproduced at unit or integration level;
- validation or authorization changed;
- data access logic changed;
- a regression is likely to recur;
- a migration/schema change needs verification.

Test both success and important failure paths when feasible.

Do not add broad, slow, brittle tests unrelated to the task.

Do not update snapshots or expected responses casually. Understand why the output changed.

For cross-layer or browser-visible behavior, follow `/tests/AGENTS.md` and `/frontend/AGENTS.md` when applicable.

---

## Configuration and environment

Follow existing project configuration patterns.

- Prefer environment variables, config files, or project scripts already used by the repo.
- Do not add machine-specific paths.
- Do not require global tools when a repo-local or documented alternative exists.
- Do not commit `.env` files, secrets, local database dumps, or generated credentials.
- If a missing tool repeatedly blocks work and has clear future value, prefer adding a documented repo-local setup path.

When a command depends on environment setup, mention the assumption or limitation in the final report.

---

## Documentation impact

Update docs only when the backend change alters:

- public API behavior;
- request or response contracts;
- status codes or error shapes;
- auth/session expectations;
- environment variables;
- setup commands;
- migration or operational workflows;
- persistent repo rules.

Do not update docs just to appear thorough.

When a contract changes, prefer updating the canonical docs under `/docs/reference/`, `/docs/specs/`, or the relevant live doc identified by `/docs/DOCS_INVENTORY.md`.

---

## Final report for backend work

The final response must include:

- what changed;
- root cause, when applicable;
- files touched;
- tests or checks run;
- real route/command/job verified, when applicable;
- any migration/data impact;
- any limitation or unverified part.

For API/network bugs, include:

- route/method tested;
- request scenario;
- response status/body observed;
- relevant logs or correlation id when available.

Do not finish with vague proof such as:

- “should be fixed”;
- “looks correct”;
- “tests pass” without naming the tests;
- “probably an API issue”.

Use concrete evidence.

---

## Backend anti-patterns

Avoid:

- changing public API behavior accidentally;
- patching before reproducing the failing backend path;
- weakening validation or authorization;
- swallowing errors silently;
- leaking secrets or sensitive data in logs/responses;
- hiding contract mismatches with frontend-only patches;
- editing already-applied migrations casually;
- making destructive data changes without explicit instruction;
- broad refactors while fixing one endpoint;
- claiming success without naming the route, command, job, or tests verified.
