/**
 * Phases 11-15 — Regression tests for dual-mode quick-search improvements.
 *
 *  Phase 11: Per-side emptyCausesExpanded, relax actions, and toggle
 *  Phase 12: Combined price shows null when one side has no price
 *  Phase 13: Return deep link fallback uses inverted route (not outbound)
 *  Phase 14: Weather is null in dual mode (not fetched per-side)
 *  Phase 15: Country-only dual exclusion and inverted IATAs
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

const USE_QUICK_SEARCH_SIDE = path.join(
  process.cwd(),
  "src",
  "modules",
  "quick-search",
  "state",
  "useQuickSearchSide.ts",
);

const UTILS_DUAL = path.join(
  process.cwd(),
  "src",
  "modules",
  "quick-search",
  "utils-dual.ts",
);

function readSource(): string {
  return fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");
}

function readSideSource(): string {
  return fs.readFileSync(USE_QUICK_SEARCH_SIDE, "utf8");
}

function readUtilsDual(): string {
  return fs.readFileSync(UTILS_DUAL, "utf8");
}

// ── Phase 11: Per-side emptyCausesExpanded ────────────────────────────

test("Phase 11: per-side emptyCausesExpanded state variables exist", () => {
  const source = readSource();
  assert.match(source, /outboundEmptyCausesExpanded/, "missing outboundEmptyCausesExpanded state");
  assert.match(source, /returnEmptyCausesExpanded/, "missing returnEmptyCausesExpanded state");
});

test("Phase 11: outbound panel uses per-side emptyCausesExpanded", () => {
  const source = readSource();
  assert.match(source, /emptyCausesExpanded=\{outboundEmptyCausesExpanded\}/, "outbound must use outboundEmptyCausesExpanded");
});

test("Phase 11: return panel uses per-side emptyCausesExpanded", () => {
  const source = readSource();
  assert.match(source, /emptyCausesExpanded=\{returnEmptyCausesExpanded\}/, "return must use returnEmptyCausesExpanded");
});

test("Phase 11: outbound toggle wired to setOutboundEmptyCausesExpanded", () => {
  const source = readSource();
  assert.match(source, /onToggleEmptyCauses=\{\(\) => setOutboundEmptyCausesExpanded/, "outbound toggle must wire correctly");
});

test("Phase 11: return toggle wired to setReturnEmptyCausesExpanded", () => {
  const source = readSource();
  assert.match(source, /onToggleEmptyCauses=\{\(\) => setReturnEmptyCausesExpanded/, "return toggle must wire correctly");
});

test("Phase 11: handleDualRelaxAction handler exists", () => {
  const source = readSource();
  assert.match(source, /handleDualRelaxAction/, "handler must exist");
});

test("Phase 11: outbound onRelaxAction wires to handleDualRelaxAction", () => {
  const source = readSource();
  assert.match(source, /onRelaxAction=\{.*handleDualRelaxAction.*"outbound".*\}/, "outbound relax must wire correctly");
});

test("Phase 11: return onRelaxAction wires to handleDualRelaxAction", () => {
  const source = readSource();
  assert.match(source, /onRelaxAction=\{.*handleDualRelaxAction.*"return".*\}/, "return relax must wire correctly");
});

test("Phase 11: per-side emptyCausesExpanded resets on dual mode exit", () => {
  const source = readSource();
  assert.match(source, /setOutboundEmptyCausesExpanded\(false\)/, "missing outbound reset");
  assert.match(source, /setReturnEmptyCausesExpanded\(false\)/, "missing return reset");
});

test("Phase 11: increase_duration skips re-search (view-only filter)", () => {
  const source = readSource();
  // Search within the handleDualRelaxAction handler body specifically
  const handlerStart = source.indexOf('const handleDualRelaxAction = useCallback(');
  const handlerBody = source.slice(handlerStart, handlerStart + 1500);
  assert.match(handlerBody, /if \(action === "increase_duration"\)/, "handler must check for increase_duration");
  assert.match(handlerBody, /return;\s*\}/, "increase_duration block must have early return to skip re-search");
});

test("Phase 11: handleDualRelaxAction deduplicates params with sideOrigin/sideDest", () => {
  const source = readSource();
  assert.match(source, /const sideOrigin = side === "outbound" \? origin : destination/, "must compute sideOrigin");
  assert.match(source, /const sideDest = side === "outbound" \? destination : origin/, "must compute sideDest");
  assert.match(source, /const sideDate = side === "outbound" \? travelDate : returnDate/, "must compute sideDate");
});

// ── Phase 12: Combined price null handling ───────────────────────────

test("Phase 12: combined price extracts obPrice/rbPrice separately", () => {
  const source = readSource();
  assert.match(source, /const obPrice = ob\.price_total \?\? ob\.price;/, "must extract obPrice");
  assert.match(source, /const rbPrice = rb\.price_total \?\? rb\.price;/, "must extract rbPrice");
});

test("Phase 12: combined price returns null when either price is missing", () => {
  const source = readSource();
  assert.match(source, /if \(obPrice == null \|\| rbPrice == null\) return null;/, "must return null (not 0) for missing prices");
});

// ── Phase 13: Return deep link fallback ──────────────────────────────

test("Phase 13: return side uses buildReturnFallbackUrl", () => {
  const source = readSource();
  assert.match(source, /buildReturnFallbackUrl/, "return side must use buildReturnFallbackUrl");
});

test("Phase 13: buildReturnFallbackUrl uses inverted route", () => {
  const source = readSource();
  // Find the buildReturnFallbackUrl function body
  const fnIdx = source.indexOf("const buildReturnFallbackUrl");
  const fnBody = source.slice(fnIdx, fnIdx + 1500);
  assert.match(fnBody, /originIata:\s*destination/, "must use destination as originIata");
  assert.match(fnBody, /destinationIata:\s*origin/, "must use origin as destinationIata");
  assert.match(fnBody, /dateOut:\s*returnDate/, "must use returnDate as dateOut");
});

test("Phase 13: fetchDeepLink accepts optional dateIn", () => {
  const sideSource = readSideSource();
  assert.match(sideSource, /dateIn\?:\s*string/, "fetchDeepLink must accept dateIn");
  assert.match(sideSource, /if \(params\.dateIn\)/, "must conditionally set date_in");
  assert.match(sideSource, /query\.set\(\"date_in\",\s*params\.dateIn\)/, "must pass dateIn to query");
});

// ── Phase 14: Weather hidden in dual mode ────────────────────────────

test("Phase 14: return side weather is explicitly null in dual mode", () => {
  const source = readSource();
  assert.match(source, /weatherOrigin=\{null\}.*Phase 14/, "return weatherOrigin must be null");
  assert.match(source, /weatherDestination=\{null\}.*Phase 14/, "return weatherDestination must be null");
});

// ── Phase 15: Country-only dual exclusion and inverted IATAs ─────────

test("Phase 15: isDualMode excludes originCountryOnly and destinationCountryOnly", () => {
  const source = readSource();
  assert.match(source, /!originCountryOnly\s*&&\s*!destinationCountryOnly/, "isDualMode must exclude country-only");
});

test("Phase 15: dual submit inverts route scopes for return leg", () => {
  const source = readSource();
  assert.match(source, /origin:\s*destinationRequestValue,/, "return leg must use destination scope as origin");
  assert.match(source, /destination:\s*originRequestValue,/, "return leg must use origin scope as destination");
});

test("Phase 15: dual mode cleanup resets both sides", () => {
  const source = readSource();
  assert.match(source, /outboundSide\.reset\(\)/, "must reset outbound");
  assert.match(source, /returnSide\.reset\(\)/, "must reset return");
  assert.match(source, /saveCombination\.reset\(\)/, "must reset saveCombination");
});

test("Phase 15: utils-dual buildDualSearchParams maps all fields correctly", () => {
  const utilsSource = readUtilsDual();
  // Verify the mapping function exists and maps all fields
  assert.match(utilsSource, /export function buildDualSearchParams/, "must export buildDualSearchParams");
  assert.match(utilsSource, /originIata: input\.origin/, "must map origin");
  assert.match(utilsSource, /destinationIata: input\.destination/, "must map destination");
  assert.match(utilsSource, /travelDate: input\.travelDate/, "must map travelDate");
  assert.match(utilsSource, /strictFilters: input\.strictFilters/, "must map strictFilters");
  assert.match(utilsSource, /excludeOrigins: input\.excludeOrigins/, "must map excludeOrigins");
  assert.match(utilsSource, /excludeDestinations: input\.excludeDestinations/, "must map excludeDestinations");
});

test("Phase 15: utils-dual findCombinationResult handles empty results", () => {
  const utilsSource = readUtilsDual();
  assert.match(utilsSource, /export function findCombinationResult/, "must export findCombinationResult");
  // Should return undefined for empty results
  assert.match(utilsSource, /return results\[0\]/, "must fallback to first result");
});
