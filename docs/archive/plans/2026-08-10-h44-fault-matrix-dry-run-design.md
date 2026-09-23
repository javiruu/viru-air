# H44 Fault Matrix and Dry-Run Design

**Status:** Implemented and validated

## Goal

Make the local hotel Mock canary execute a declarative matrix of fault profiles and provide a safe disposable dry-run, without network calls, database migrations, or browser E2E scope.

## Approach

Extend the existing `backend/scripts/hotel_mock_canary.py` rather than creating a parallel runner. The profile fixture remains the source of truth for expected status, error code, bounded counts, and external-call expectations. Each matrix scenario runs against its own temporary SQLite database and emits only redacted aggregate evidence.

`--dry-run` runs the same matrix in disposable SQLite files under the system temporary directory, validates each report, and deletes the databases and sidecar files after completion. It never accepts or mutates a caller-owned database. Normal canary mode keeps the existing explicit isolated-database contract.

## Evidence contract

Each scenario reports only:

- profile name and expected/observed status;
- expected/observed error code when allowlisted;
- expected/observed external calls (always zero for Mock network I/O);
- bounded row counts, snapshots, eligible snapshots, and warnings/review flags;
- provider resolver and adapter-call counts.

Private identifiers, payloads, URLs, secrets, and raw provider data remain rejected by `validate_evidence`.

## Matrix semantics

- transport failures: failed run, no eligible snapshots;
- empty provider: empty response, no eligible snapshots;
- sold out: unavailable snapshots, no eligible current price;
- invalid deeplink: sanitized link evidence only;
- ambiguous matching: partial/review warning and no confirmed provider alias;
- stale history: stale warning and no eligible current price;
- partial batch: partial status and warning for the received batch;
- happy path: successful Mock ingestion.

The matrix intentionally does not claim live availability or commercial-provider behavior. Browser E2E, CI orchestration, commercial-provider canary, and a persisted historical matrix remain separate follow-up work.
