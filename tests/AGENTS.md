# tests/AGENTS.md — viru-tracker testing rules

This file defines testing-specific rules for coding agents working inside the testing area of `viru-tracker`.

The root `/AGENTS.md` still applies. This file adds specific guidance for regression tests, browser automation, TestSprite, visual evidence, stable test data, and verification strategy.

---

## Testing mission

Tests in `viru-tracker` must prove real behavior with the smallest reliable check.

A good test is:

- targeted;
- meaningful;
- repeatable;
- tied to user-visible or contract-level behavior;
- not brittle;
- not broader than the task requires.

Do not add tests only to appear thorough. Add or update tests when they prove behavior, prevent regression, or verify a changed contract.

---

## Verification strategy

Use the smallest set of checks that safely proves the change.

Verification ladder:

1. Targeted regression test for the changed behavior.
2. Nearby related tests.
3. Build/typecheck/lint when relevant.
4. API/integration verification when runtime behavior matters.
5. Real browser verification for browser-visible work.
6. TestSprite or screenshots for visual/user-flow evidence.

Do not use a broad test suite as a substitute for a targeted check when the bug or behavior can be tested directly.

Do not claim a fix is verified unless the checks actually cover the changed behavior.

---

## Regression tests

Prefer adding or updating a regression test when:

- fixing a bug;
- changing validation;
- changing API request/response behavior;
- changing auth/session-dependent behavior;
- changing navigation or conditional rendering;
- changing data access logic;
- changing important UI state;
- changing a flow likely to break again.

A regression test should fail before the fix when feasible.

Good regression tests prove:

- the original failing case;
- the expected fixed behavior;
- the important failure path when relevant.

If a regression test cannot be written, explain why in the final report.

Avoid tests that only assert implementation details while missing the user-visible behavior.

---

## Test scope

Keep tests close to the behavior being changed.

Use:

- unit tests for isolated logic;
- component tests for local UI behavior;
- integration tests for API/service boundaries;
- end-to-end or browser automation for real flows;
- TestSprite for multi-step browser-visible workflows;
- screenshots for scoped visual verification.

Do not add broad, slow, fragile tests for a small local change.

Do not rewrite unrelated tests just because they are nearby.

Do not update snapshots casually. Understand why the output changed before accepting a new snapshot.

---

## Browser-visible evidence

Browser-visible work needs real rendered evidence whenever feasible.

Do not claim a visual or browser-visible fix based only on:

- code inspection;
- lint;
- typecheck;
- build success;
- reasoning;
- “it should work”.

Browser-visible work is verified with visible evidence from at least one of these paths:

1. TestSprite or real browser automation;
2. screenshots captured by the agent in the real browser flow.

Use TestSprite by default for:

- multi-step flows;
- real navigation;
- login/register/account menu behavior;
- forms with validation;
- dashboards and interactive states;
- reported browser regressions;
- session-dependent behavior;
- API-backed UI interactions.

Use screenshots instead when the change is static, scoped, or when TestSprite is flaky for that route.

Screenshot expectations:

- simple UI change → full section/page + focused changed component;
- structural/layout change → full page + changed section + interaction state if relevant;
- stateful UI → capture affected default/open/loading/empty/error/success states when relevant.

Screenshots must show the real rendered result and enough context to prove the reported issue is resolved.

If browser evidence is unavailable, say exactly what remains unverified and why.

---

## Test data

Keep test data stable, minimal, and understandable.

When creating or editing test data:

- use the smallest data set that proves the behavior;
- keep names and values readable;
- avoid hidden dependencies between tests;
- avoid relying on test execution order;
- avoid changing shared fixtures unless the task requires it;
- do not introduce data that hides the real bug;
- do not use real private user data.

If stable project fixtures already exist, prefer using them over inventing new large fixtures.

Do not modify `users_prueba.txt` unless the user explicitly asks and the impact is understood.

---

## API and integration tests

For API or backend integration tests:

- identify the route, method, request shape, response shape, and status code;
- test the important success path;
- test relevant failure paths when feasible;
- keep expected errors consistent with backend conventions;
- avoid asserting unstable fields unless they are part of the contract;
- do not mock away the behavior you are trying to verify.

For API-backed bugs, prefer tests that prove the real contract rather than only internal helper behavior.

When frontend and backend disagree, treat the contract mismatch as a first-class test target.

---

## Frontend tests

For frontend behavior:

- test user-observable behavior over implementation details;
- prefer accessible queries/selectors when available;
- avoid brittle selectors tied to styling unless no better option exists;
- test loading, empty, error, success, and disabled states when they changed;
- test form validation and submit behavior when relevant;
- verify navigation and route-dependent behavior when changed.

Do not add snapshot-heavy frontend tests unless snapshots are already the established project pattern and the change is truly structural.

Frontend tests do not replace real rendered verification when the visual result matters.

---

## Backend tests

For backend behavior:

- test changed validation, authorization, data access, and contracts;
- include important failure paths when feasible;
- avoid broad integration tests when a focused service or endpoint test proves the behavior;
- do not weaken tests to fit a broken implementation;
- do not update expected responses without understanding the behavior change.

For migration or schema changes:

- verify migration application with the normal project command when feasible;
- test behavior that depends on the new schema;
- mention unverified rollback/down behavior if not checked.

---

## Flaky tests

Do not normalize flaky tests as acceptable.

When a test is flaky:

- identify whether the flake is caused by timing, async state, network dependency, shared state, order dependency, or environment setup;
- prefer deterministic waiting over arbitrary sleeps;
- isolate shared state;
- avoid weakening assertions until they no longer prove behavior;
- report unrelated flakes separately if they are outside the task.

If a flaky test blocks verification and cannot be fixed within scope, state:

- which test is flaky;
- what failed;
- whether the failure appears related to the change;
- what verification was still completed.

---

## Mocks and stubs

Use mocks only when they preserve the behavior being tested.

Good mocks:

- isolate external services;
- avoid live destructive calls;
- make tests deterministic;
- preserve the contract shape relevant to the test.

Bad mocks:

- mock away the bug;
- assert implementation details instead of behavior;
- drift from real API response shapes;
- hide auth/session/data consistency issues.

If a mock represents an external contract, keep it consistent with docs, types, or observed responses.

---

## Test commands and performance

Use the project’s existing scripts and documented commands.

Before inventing a new command:

- check package scripts, test config, Makefile/task runner, or docs;
- prefer repo-local tools over global tools;
- avoid machine-specific paths;
- do not require new global setup unless clearly justified.

Keep test suites practical:

- prefer targeted tests during development;
- run broader suites only when the change justifies it;
- do not add slow tests for behavior that can be proven faster;
- do not skip relevant tests only because they are slower if they are the only meaningful proof;
- if a full suite is too slow or unavailable, run the targeted subset and state the limitation.

If a recurring missing tool blocks useful verification and has future value, prefer adding a documented repo-local setup path instead of repeating fragile workarounds.

---

## Evidence in final reports

Final reports for testing work must include:

- which tests/checks were run;
- whether they passed or failed;
- what behavior the tests prove;
- any browser route or flow tested;
- any screenshots or TestSprite evidence used;
- any known limitation or unverified part.

Do not write:

- “tests pass” without naming the tests;
- “should be fixed”;
- “looks good”;
- “verified” when the check did not cover the changed behavior.

Use concrete evidence.

---

## Testing anti-patterns

Avoid:

- adding broad tests unrelated to the task;
- updating snapshots without understanding the change;
- weakening assertions to make tests pass;
- mocking away the behavior under test;
- relying on test order or shared mutable state;
- using real private user data;
- treating build success as behavior verification;
- claiming visual success without browser evidence;
- ignoring flaky tests without explanation;
- changing stable fixtures casually.