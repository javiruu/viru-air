# Manual QA — Watchlist incoming-aircraft delay prediction

Date: 2026-07-28
Surface: `http://127.0.0.1:3102/watchlist?watch_id=watch-prediction` (mocked browser API) and backend TestClient integration endpoint.

## Verdict

**PASS — high confidence (0.90).** The deterministic high-risk rotation is rendered in both themes and desktop/mobile viewports, with no raw i18n keys, horizontal overflow, or console errors. The DB-backed endpoint returns the exact incoming aircraft prediction and withholds another user's rotation.

## Scenario inventory (brainstorm before execution)

P0: available/high exact rotation; endpoint ownership/privacy; deterministic no-provider-call path.

P1: low/healthy landed rotation; stale rotation; missing registration; no incoming aircraft; active inbound; terminal/landed inbound; 25-hour cutoff; multi-leg target.
P2: dark theme; light theme; mobile width; desktop width; Spanish i18n; raw-key absence; horizontal overflow; console errors; model/risk/disclaimer copy; provider failure/degraded coverage.

## surfaceEvidence

| scenario id | criterion reference | surface | exact invocation | verdict | artifactRefs |
|---|---|---|---|---|---|
| S01 | available/high exact rotation | Browser UI | `node frontend/scripts/qa_watchlist_delay_prediction.mjs`; mocked `GET /api/v1/watchlist/watch-prediction/live` | PASS | A01,A02,A03,A04 |
| S02 | dark desktop rendering | Browser UI, 1440x1000 | same script, `theme=dark` | PASS | A01 |
| S03 | light desktop rendering | Browser UI, 1440x1000 | same script, `theme=light` | PASS | A02 |
| S04 | dark mobile rendering | Browser UI, 390x844 | same script, `theme=dark` | PASS | A03 |
| S05 | light mobile rendering | Browser UI, 390x844 | same script, `theme=light` | PASS | A04 |
| S06 | Spanish i18n and no raw keys | Browser DOM assertions | script assertions `title`, `disclaimer`, `no_raw_i18n` | PASS | A01-A04 |
| S07 | no overflow / console errors | Browser DOM + console listener | script assertions `no_horizontal_overflow`, `no_console_errors` | PASS | A01-A04 |
| S08 | exact shared incoming aircraft and bounded estimate | DB-backed API | `backend/.venv/Scripts/python.exe -m pytest tests/integration/test_watchlist_delay_prediction.py::test_watchlist_live_response_predicts_delay_from_shared_incoming_aircraft -q` | PASS | A05 |
| S09 | endpoint ownership/privacy | DB-backed API | `backend/.venv/Scripts/python.exe -m pytest tests/integration/test_watchlist_delay_prediction.py::test_watchlist_delay_prediction_does_not_reveal_another_users_rotation -q` | PASS | A06 |
| S10 | low-risk healthy landed rotation | prediction service | `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_incoming_delay_prediction.py -q` | PASS | A07 |
| S11 | stale rotation lowers confidence | prediction service | same unit test command | PASS | A07 |
| S12 | UI component contract/no network/randomness | Node test | `node --test --import tsx frontend/tests/watchlist-delay-prediction.test.ts` | PASS | A08 |

## adversarialCases

| scenario id | criterion reference | adversarial class | expected behavior | verdict | artifactRefs |
|---|---|---|---|---|---|
| A-S01 | high risk | exact shared registration | available prediction with 20–40 min, score 90 | PASS | A05 |
| A-S02 | privacy | incoming rotation owned by another user | `insufficient_data`, `incoming_not_found`; no route leak | PASS | A06 |
| A-S03 | healthy rotation | landed with 100-minute turnaround | low risk, 0–15 min | PASS | A07 |
| A-S04 | stale rotation | stale inbound observation | low confidence/guarded estimate | PASS | A07 |
| A-S05 | missing registration | no registration identity | not exercised by available fixtures; requires dedicated fixture | NOT_RUN | — |
| A-S06 | no incoming | no matching inbound leg | not exercised by available fixtures; requires dedicated fixture | NOT_RUN | — |
| A-S07 | active inbound | airborne inbound factor | factor includes `incoming_airborne` | PASS | A05,A07 |
| A-S08 | landed inbound | healthy landed rotation | low-risk estimate with landed factor | PASS | A07 |
| A-S08b | cancelled/diverted inbound | non-viable rotation | excluded from candidate query | NOT_RUN | — |
| A-S09 | 25h cutoff | inbound outside rotation cutoff | no prediction | NOT_RUN | — |
| A-S10 | multi-leg | multi-leg target consistency | prediction attached to correct leg only | NOT_RUN | — |
| A-S11 | provider calls | `refresh=false` persisted response | endpoint returns DB state without provider invocation | PASS | A05 |
| A-S12 | theme | dark/light parity | same semantics and readable contrast | PASS | A01,A02 |
| A-S13 | responsive | 390px mobile | no clipping or horizontal overflow | PASS | A03,A04 |
| A-S14 | i18n | Spanish locale | translated copy, no `watchlist.*` raw keys | PASS | A01-A04 |
| A-S15 | stability | browser console/runtime | zero console errors | PASS | A01-A04 |
| A-S16 | degraded provider | provider unavailable/coverage degraded | honest unavailable state | NOT_RUN | — |

## artifactRefs

| id | kind | description | path |
|---|---|---|---|
| A01 | screenshot | Desktop dark operational panel | `docs/qa/screenshots/watchlist-delay-prediction/desktop_dark.png` |
| A02 | screenshot | Desktop light operational panel | `docs/qa/screenshots/watchlist-delay-prediction/desktop_light.png` |
| A03 | screenshot | Mobile dark operational panel | `docs/qa/screenshots/watchlist-delay-prediction/mobile_dark.png` |
| A04 | screenshot | Mobile light operational panel | `docs/qa/screenshots/watchlist-delay-prediction/mobile_light.png` |
| A05 | test transcript | DB-backed exact incoming rotation integration test (1 passed) | `backend/tests/integration/test_watchlist_delay_prediction.py` |
| A06 | test transcript | Cross-user rotation privacy integration test (1 passed) | `backend/tests/integration/test_watchlist_delay_prediction.py` |
| A07 | test transcript | Prediction unit suite (3 passed) | `backend/tests/unit/test_incoming_delay_prediction.py` |
| A08 | test transcript | Frontend contract test (1 passed) | `frontend/tests/watchlist-delay-prediction.test.ts` |
| A09 | report | Fresh four-scenario Playwright report; all assertions true | `docs/qa/reports/2026-07-28-watchlist-delay-prediction.json` |

## Coverage limitations

Missing-registration, no-incoming, 25-hour cutoff, multi-leg,
cancelled/diverted incoming and provider-degraded fixtures were not available
in the supplied executable flow; they remain explicit follow-up cases rather
than inferred passes. No product/source files were changed by this QA lane.
