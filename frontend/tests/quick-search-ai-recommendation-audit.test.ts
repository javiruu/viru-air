/**
 * Phase 16 — AI Recommendation audit tests.
 *
 * Verifies:
 *  - Heuristic fallback when OpenAI is unavailable
 *  - Single preferred result (never more than one)
 *  - Frontend star renders correctly for AI preferred
 *  - AI preferred row has distinct CSS class
 *  - Reason is shown only when non-empty
 *  - Normalizer handles missing ai_preference meta
 */

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

// ── Paths ────────────────────────────────────────────────────────────

const QUICK_SEARCH_VIEW = path.join(
  process.cwd(),
  "src",
  "modules",
  "quick-search",
  "QuickSearchView.tsx",
);

const RESULTS_LIST = path.join(
  process.cwd(),
  "src",
  "modules",
  "quick-search",
  "components",
  "QuickSearchResultsList.tsx",
);

const BACKEND_PREFERENCE = path.resolve(
  process.cwd(),
  "..",
  "backend",
  "app",
  "services",
  "quick_search_ai_preference.py",
);

function readSource(filePath: string): string {
  return fs.readFileSync(filePath, "utf8");
}

// ── 1. Frontend: AI preferred star exists and is non-aggressive ──────

test("Phase 16: AI preferred renders as a warm star, not a badge or overlay", () => {
  const source = readSource(RESULTS_LIST);

  assert.match(
    source,
    /className="qs-result-recommendation-star"/,
    "AI preferred result must render the recommendation star",
  );
  assert.doesNotMatch(
    source,
    /className=\{\`qs-tag qs-tag-\$\{tag\.tone\}\`\}/,
    "AI preferred must not render as a tag badge",
  );

  // Must NOT use any full-width or overlay class
  assert.doesNotMatch(
    source,
    /qs-overlay|qs-fullscreen|qs-modal.*ai/i,
    "AI preferred must not use overlay or fullscreen class",
  );
});

test("Phase 16: AI preferred styling no longer relies on tag metadata", () => {
  const viewSource = readSource(QUICK_SEARCH_VIEW);

  assert.doesNotMatch(
    viewSource,
    /getAiPreferredTag|getResultTags/,
    "Removed recommendation badges must not leave tag metadata helpers behind",
  );
});

test("Phase 16: AI preferred does not hide other results", () => {
  const source = readSource(RESULTS_LIST);

  assert.match(
    source,
    /props\.visibleResults\.map\(/,
    "All visible results must be mapped, not just the AI preferred one",
  );

  assert.doesNotMatch(
    source,
    /\.filter\(.*ai_preferred/,
    "Must not filter out non-preferred results",
  );
});

// ── 2. Frontend: Reason shown only when non-empty ────────────────────

test("Phase 16: AI reason is trimmed before display", () => {
  const source = readSource(RESULTS_LIST);

  assert.match(
    source,
    /const aiReason = typeof r\.ai_preferred_reason === \"string\" \? r\.ai_preferred_reason\.trim\(\) : \"\"/,
    "AI reason must be trimmed to handle whitespace-only strings",
  );
});

test("Phase 16: AI reason is included in the star tooltip only when non-empty", () => {
  const source = readSource(RESULTS_LIST);

  assert.match(
    source,
    /const recommendationLabel = aiReason/,
    "AI reason must be conditional on a non-empty aiReason",
  );
  assert.match(
    source,
    /props\.t\("aiPreferredReasonLabel"\)/,
    "The recommendation tooltip must use the translated reason label",
  );
});

// ── 3. Frontend: Row class for AI preferred ──────────────────────────

test("Phase 16: AI preferred row gets qs-result-row-ai class", () => {
  const source = readSource(RESULTS_LIST);

  assert.match(
    source,
    /\$\{r\.ai_preferred \? \"qs-result-row-ai\" : \"\"\}/,
    "AI preferred row must get qs-result-row-ai CSS class",
  );
});

test("Phase 16: AI preferred star exposes an accessible tooltip", () => {
  const source = readSource(RESULTS_LIST);

  assert.match(
    source,
    /aria-label=\{props\.t\(\"aiPreferredAria\"\)\}/,
    "AI preferred star must expose a concise accessible name",
  );
  assert.match(
    source,
    /aria-describedby=\{recommendationTooltipId\}/,
    "AI preferred star must reference its tooltip",
  );
});

// ── 4. Frontend: Only ONE preferred result ───────────────────────────

test("Phase 16: recommendation star only marks the preferred result", () => {
  const source = readSource(RESULTS_LIST);

  assert.match(
    source,
    /const recommendationMark = r\.ai_preferred \? \(/,
    "The recommendation star must be conditional on ai_preferred",
  );
});

test("Phase 16: Backend sets ai_preferred on exactly one result", () => {
  const source = readSource(BACKEND_PREFERENCE);

  // The heuristic picks exactly one result via min()
  assert.match(
    source,
    /preferred = min\(results, key=score\)/,
    "Heuristic must select exactly one result using min()",
  );
});

// ── 5. Backend: Heuristic scoring includes key factors ───────────────

test("Phase 16: Heuristic scoring includes price, duration, distance, and stale penalty", () => {
  const source = readSource(BACKEND_PREFERENCE);

  assert.match(source, /ranking_score/, "Heuristic must consider ranking_score");
  assert.match(source, /price_delta/, "Heuristic must consider price delta from minimum");
  assert.match(source, /duration_total/, "Heuristic must consider duration");
  assert.match(source, /distance_penalty/, "Heuristic must consider distance penalty");
  assert.match(source, /stale_penalty/, "Heuristic must penalize stale data");
});

test("Phase 16: Heuristic fallback reason mentions the route", () => {
  const source = readSource(BACKEND_PREFERENCE);

  assert.match(
    source,
    /reason=f\"Mejor equilibrio.*\{route\}/,
    "Heuristic reason must mention the route for transparency",
  );
});

// ── 6. Backend: Fallback chain is robust ─────────────────────────────

test("Phase 16: Backend falls back to heuristic when OpenAI fails", () => {
  const source = readSource(BACKEND_PREFERENCE);

  assert.match(
    source,
    /fallback_used=True/,
    "Fallback must set fallback_used=True",
  );
});

test("Phase 16: Backend validates preferred_result_id exists in candidates", () => {
  const source = readSource(BACKEND_PREFERENCE);

  assert.match(
    source,
    /valid_ids = \{str\(item\.get\(\"result_id\"\)/,
    "Backend must validate preferred_result_id against actual result IDs",
  );
});

test("Phase 16: Backend handles missing OpenAI key gracefully", () => {
  const source = readSource(BACKEND_PREFERENCE);

  assert.match(
    source,
    /missing_openai_key/,
    "Backend must handle missing OPENAI_API_KEY",
  );
});

// ── 7. Copy: i18n keys exist for both ES and EN ─────────────────────

test("Phase 16: Copy keys aiPreferredPrice, aiPreferredAria, aiPreferredReasonLabel exist", () => {
  const copySource = readSource(
    path.join(
      process.cwd(),
      "src",
      "modules",
      "shared",
      "quickSearchCopy.ts",
    ),
  );

  assert.match(copySource, /aiPreferredPrice:/, "ES copy missing aiPreferredPrice");
  assert.match(copySource, /aiPreferredAria:/, "ES copy missing aiPreferredAria");
  assert.match(copySource, /aiPreferredReasonLabel:/, "ES copy missing aiPreferredReasonLabel");

  // EN copy
  const enSection = copySource.slice(copySource.indexOf("en: {"));
  assert.match(enSection, /aiPreferredPrice:/, "EN copy missing aiPreferredPrice");
  assert.match(enSection, /aiPreferredAria:/, "EN copy missing aiPreferredAria");
  assert.match(enSection, /aiPreferredReasonLabel:/, "EN copy missing aiPreferredReasonLabel");
});
