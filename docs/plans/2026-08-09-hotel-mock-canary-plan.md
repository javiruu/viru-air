# Hotel Mock Canary Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a reproducible offline Mock canary runner that verifies per-run latency persistence and fail-closed kill-switch behavior without external providers or production databases.

**Architecture:** Add a Python runner under `backend/scripts/` that requires an explicit isolated SQLite URL, resolves activation flags, runs a Mock sweep, and emits only bounded redacted JSON evidence. Run a second kill-switch scenario with the Mock adapter wrapped to count calls, proving `HOTEL_FEATURE_ENABLED=false` blocks before provider I/O and does not mutate provider data. Keep the runner independent of API credentials, network access, and live providers.

**Tech Stack:** Python 3.12, SQLAlchemy, existing hotel activation/sweep services, pytest, JSON evidence.

---

### Task 1: Define runner contract and forbidden evidence fields

**Files:**
- Create: `backend/scripts/hotel_mock_canary.py`
- Test: `backend/tests/unit/test_hotel_mock_canary.py`

**Step 1: Write failing tests**

Cover:
- nominal Mock scenario reports `passed`, `mock`, no external calls, bounded aggregates and no private IDs;
- kill switch reports `passed`, zero adapter calls, and an allowlisted disabled reason;
- non-Mock provider or missing isolated DB is rejected before execution;
- serialized evidence rejects forbidden keys such as `user_id`, `hotel_id`, `provider_run_id`, `api_key`, `token`, `secret`, and `payload`.

**Step 2: Run focused tests**

```bash
cd backend
python -m pytest tests/unit/test_hotel_mock_canary.py -q
```

Expected initial result: FAIL because the runner does not exist.

**Step 3: Implement pure helpers**

Add bounded constants, allowlists, safe JSON serialization, forbidden-key recursive validation, and an evidence builder. The builder must never accept raw ORM objects or exception text.

**Step 4: Run focused tests again**

Expected: helper and evidence tests pass.

---

### Task 2: Implement the nominal offline Mock scenario

**Files:**
- Modify: `backend/scripts/hotel_mock_canary.py`
- Test: `backend/tests/unit/test_hotel_mock_canary.py`

**Step 1: Require explicit isolation**

Accept `--db-url` only for SQLite URLs and reject `sqlite:///./viru.db`, non-SQLite URLs, empty values, or paths outside the temporary/explicit isolated contract. Avoid deleting or resetting an existing file.

**Step 2: Create isolated schema**

Use a temporary SQLite path supplied by the test/CLI, `Base.metadata.create_all`, and no application startup side effects. Do not run provider resolution before flags/profile validation.

**Step 3: Execute Mock sweep**

Set/validate `HOTEL_PROFILE=local_fixture` or `local_demo`, `HOTEL_PROVIDER=mock`, feature and sweep flags true, then call `run_hotel_sweep(provider="mock")`. Inspect only aggregate values: status, snapshot count, latency aggregate count, allowlisted dimensions/outcomes, and external call count (always zero because Mock is local).

**Step 4: Verify persistence**

Query `HotelProviderLatencyAggregate` and confirm at least the ingestion aggregate exists for the run, with non-negative bounded values and no run ID in evidence.

**Step 5: Run nominal tests**

```bash
python -m pytest tests/unit/test_hotel_mock_canary.py -q
```

---

### Task 3: Implement the global kill-switch scenario

**Files:**
- Modify: `backend/scripts/hotel_mock_canary.py`
- Test: `backend/tests/unit/test_hotel_mock_canary.py`

**Step 1: Wrap Mock adapter**

Use a delegating adapter or monkeypatch only inside the runner scenario to count `fetch_hotels` and `fetch_hotel_rates`. Do not modify the production adapter contract.

**Step 2: Disable the feature**

Resolve with `HOTEL_PROFILE=local_demo`, `HOTEL_PROVIDER=mock`, `HOTEL_FEATURE_ENABLED=false`, `HOTEL_SWEEP_ENABLED=false`. Call the common sweep boundary and assert terminal blocked status/reason without resolving or invoking provider I/O.

**Step 3: Verify zero calls and no provider mutations**

Assert counted adapter calls are zero and the isolated database contains no provider aliases, rates, latency aggregates, or snapshots caused by the blocked scenario. Existing read-only data must not be deleted.

**Step 4: Run tests**

```bash
python -m pytest tests/unit/test_hotel_mock_canary.py -q
```

---

### Task 4: Add CLI and evidence file output

**Files:**
- Modify: `backend/scripts/hotel_mock_canary.py`
- Create: `backend/tests/fixtures/hotel_mock_canary_expected.json` (only if needed for stable expected dimensions)
- Test: `backend/tests/unit/test_hotel_mock_canary.py`

**Step 1: Add CLI options**

Support `--db-url`, `--output`, `--profile`, and `--provider`, with defaults that remain safe. Require `--provider mock`; require an explicit DB URL for real CLI execution; write atomically to the requested output path only after all gates complete.

**Step 2: Define report shape**

Include `schema_version`, UTC timestamp, runner, profile, provider mode, migration revision, overall status, scenario statuses, external calls expected/observed, bounded counts, and known limitations. Exclude all internal identifiers and raw exceptions.

**Step 3: Test CLI**

Use `subprocess` with a temporary SQLite DB and output path. Assert exit code 0, valid JSON, `passed` nominal/kill-switch scenarios, zero external calls, and forbidden-key scan. Test non-zero exit for unsafe provider/profile/DB arguments.

---

### Task 5: Update H37/H41/H43/H45 evidence claims

**Files:**
- Modify: `docs/reference/backend/hoteles-flags-canary-killswitch-h43.md`
- Modify: `docs/reference/backend/hoteles-release-canary-smoke-rollback-h45.md`
- Modify: `docs/reference/backend/hoteles-benchmark-rate-limits-locks-cost-h37.md`
- Modify: `docs/reference/backend/hoteles-observability-e2e-h41.md`

Document only what the runner proves:
- offline fixture/mock canary is reproducible;
- global kill switch has zero Mock calls and no provider mutations;
- latency aggregate persistence is observed on an isolated DB;
- this is not a commercial provider canary, production traffic split, field metric, or SLO evidence;
- evidence is bounded/redacted and has an expiration/ownership caveat.

Keep `staging_canary`, `prod_gradual`, Makcorps, PostgreSQL concurrency and production cost explicitly pending.

---

### Task 6: Validate and review

Run from `backend/`:

```bash
python -m pytest tests/unit/test_hotel_mock_canary.py tests/unit/test_hotel_provider_latency_persistence.py tests/unit/test_hotel_provider_latency_migration.py tests/unit/test_hotels_ingestion.py tests/unit/test_hotels_sweep_worker.py -q
python -m ruff check scripts/hotel_mock_canary.py tests/unit/test_hotel_mock_canary.py
python -m compileall -q app scripts/hotel_mock_canary.py
python scripts/hotel_mock_canary.py --help
```

Also run `git diff --check`, inspect generated evidence for forbidden fields, and request independent review focused on isolation, kill-switch ordering, privacy, and the distinction between Mock fixture canary and live/provider canary.
