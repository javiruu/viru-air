/**
 * Phase 16 — AI Recommendation audit tests.
 *
 * Verifies:
 *  - Heuristic fallback when OpenAI is unavailable
 *  - Single preferred result (never more than one)
 *  - Frontend badge renders correctly for AI preferred
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

// ── 1. Frontend: AI preferred tag exists and is non-aggressive ────────

test("Phase 16: AI preferred tag renders as a small badge, not an overlay", () => {
  const source = readSource(RESULTS_LIST);

  // The AI tag must be a <span> with qs-tag class (inline badge)
  assert.match(
    source,
    /className=\{\`qs-tag qs-tag-\$\{tag\.tone\}\`\}/,
    "AI preferred tag must use qs-tag class (inline badge, not overlay)",
  );

  // Must NOT use any full-width or overlay class
  assert.doesNotMatch(
    source,
    /qs-overlay|qs-fullscreen|qs-modal.*ai/i,
    "AI preferred must not use overlay or fullscreen class",
  );
});

test("Phase 16: AI preferred tag uses 'ai' tone for visual distinction", () => {
  const viewSource = readSource(QUICK_SEARCH_VIEW);

  // getAiPreferredTag must return tone: "ai"
  assert.match(
    viewSource,
    /tone:\s*\"ai\"/,
    "getAiPreferredTag must return tone 'ai' for the badge",
  );
});

test("Phase 16: AI preferred does not hide other results", () => {
  const source = readSource(RESULTS_LIST);

  // All results are rendered in the same list, AI preferred is just a tag
  assert.match(
    source,
    /props\.visibleResults\.map\(/,
    "All visible results must be mapped, not just the AI preferred one",
  );

  // No conditional rendering that hides non-preferred results
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

test("Phase 16: AI reason label only shown when aiReason is truthy", () => {
  const source = readSource(RESULTS_LIST);

  // In the normal view
  assert.match(
    source,
    /\{r\.ai_preferred && aiReason \? \(/,
    "AI reason must be conditional on both ai_preferred and aiReason being truthy",
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

test("Phase 16: AI preferred aria-label is set on the tag", () => {
  const source = readSource(RESULTS_LIST);

  assert.match(
    source,
    /aria-label=\{tag\.key === \"ai-preferred\" \? props\.t\(\"aiPreferredAria\"\) : undefined\}/,
    "AI preferred tag must have aria-label for accessibility",
  );
});

// ── 4. Frontend: Only ONE preferred result ───────────────────────────

test("Phase 16: getAiPreferredTag only marks the preferred result", () => {
  const source = readSource(QUICK_SEARCH_VIEW);

  // The tag is generated per-result, only when result.ai_preferred is true
  assert.match(
    source,
    /if \(!result\.ai_preferred\) return null;/,
    "getAiPreferredTag must return null when ai_preferred is falsy",
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
