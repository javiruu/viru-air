/**
 * Fase 9 — Frontend regression tests for dual (ida + vuelta) quick‑search.
 *
 * These tests guard the wiring that was broken or missing before the
 * dual‑stabilization cycle:
 *  1. Return datepicker wired with calendar hints
 *  2. Dual divider rendered between panels
 *  3. Per‑side independent pagination
 *  4. Combined banner conditional rendering
 *
 * Tests use both source‑code assertions (like calendar‑hints‑wiring tests)
 * and static markup checks where useful.
 */

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { QuickSearchDatePicker } from "../src/modules/quick-search/components/QuickSearchDatePicker";

// ── Paths ────────────────────────────────────────────────────────────

const QUICK_SEARCH_VIEW = path.join(
  process.cwd(),
  "src",
  "modules",
  "quick-search",
  "QuickSearchView.tsx",
);

// ── 1. Return datepicker wired with calendar hints ───────────────────

test("return datepicker is wired with dayHintsByIso from return-side cache", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");

  // The return datepicker must receive hints from the return-side cache
  assert.match(
    source,
    /dayHintsByIso=\{calendarHintsActiveReturn\?\.dayHintsByIso \|\| \{\}\}/,
    "return datepicker missing dayHintsByIso from return-side cache",
  );

  // Hints loading state
  assert.match(
    source,
    /hintsLoading=\{calendarHintsLoadingKeyReturn === calendarHintsRequestKeyReturn\}/,
    "return datepicker missing return-side hintsLoading",
  );

  // Scope badge
  assert.match(
    source,
    /showCountryEstimateBadge=\{canRequestCalendarHints && hasCountryScopeForCalendarHints\}/,
    "return datepicker missing showCountryEstimateBadge",
  );

  // Scope mode
  assert.match(
    source,
    /hintScopeMode=\{calendarHintsActiveReturn\?\.scopeMode \|\| calendarHintsScopeMode\}/,
    "return datepicker missing return-side hintScopeMode",
  );

  // Visible month callback (per‑side, not shared)
  assert.match(
    source,
    /onVisibleMonthChange=\{setCalendarVisibleMonthReturn\}/,
    "return datepicker missing its own onVisibleMonthChange (setCalendarVisibleMonthReturn)",
  );
});

test("return datepicker variant is 'return' (not 'outbound')", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");

  assert.match(
    source,
    /name="return_date"/,
    "return datepicker missing name='return_date'",
  );
  assert.match(
    source,
    /variant="return"/,
    "return datepicker missing variant='return'",
  );
});

test("return-side calendar hints cache is separate from outbound", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");

  // Separate state variables
  assert.match(source, /calendarVisibleMonthReturn/);
  assert.match(source, /calendarHintsByKeyReturn/);
  assert.match(source, /calendarHintsLoadingKeyReturn/);

  // Separate scope signature (inverted IATA pair)
  assert.match(source, /calendarHintsScopeSignatureReturn/);
  assert.match(source, /calendarHintsRequestKeyReturn/);

  // Invalidation clears BOTH caches
  assert.match(source, /setCalendarHintsByKey\(\{\}\)/);
  assert.match(source, /setCalendarHintsByKeyReturn\(\{\}\)/);
  assert.match(source, /setCalendarHintsLoadingKeyReturn\(null\)/);
});

test("return-side calendar hints fetch inverts IATA pair", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");

  // The return leg fetch MUST invert: origin → destination pool, destination → origin pool
  assert.match(
    source,
    /origin_iata:\s*destinationCountryOnly/,
    "return hints missing inverted origin_iata (destinationCountryOnly)",
  );
  assert.match(
    source,
    /destination_iata:\s*originCountryOnly/,
    "return hints missing inverted destination_iata (originCountryOnly)",
  );
});

// ── 2. QuickSearchDatePicker renders hints in variant="return" ────────

test("QuickSearchDatePicker renders hints of low/mid/high/none buckets in variant=return", () => {
  const html = renderToStaticMarkup(
    <QuickSearchDatePicker
      name="return_date"
      label="Vuelta"
      value="2026-06-15"
      onChange={() => undefined}
      placeholder="Selecciona fechas"
      localeTag="es-ES"
      variant="return"
      defaultOpen={true}
      dayHintsByIso={{
        "2026-06-10": {
          date: "2026-06-10",
          min_price: 45.0,
          bucket: "low",
        },
        "2026-06-15": {
          date: "2026-06-15",
          min_price: 120.0,
          bucket: "mid",
        },
        "2026-06-20": {
          date: "2026-06-20",
          min_price: 250.0,
          bucket: "high",
        },
        "2026-06-25": {
          date: "2026-06-25",
          min_price: null,
          bucket: "none",
          no_data_reason: "no_fare_data",
        },
      }}
    />,
  );

  // All four bucket states should render (component uses hint-{bucket} classes)
  assert.match(html, /hint-low/);
  assert.match(html, /hint-mid/);
  assert.match(html, /hint-high/);
  assert.match(html, /is-no-price-data/);

  // The no-data marker
  assert.match(html, /qs-date-day__no-price-icon/);
  assert.match(html, /qs-date-day__no-price-tooltip/);

  // Return-specific label
  assert.match(html, /Vuelta/);
});

// ── 3. Dual divider rendered between panels ──────────────────────────

test("dual workspace renders qs-dual-divider between outbound and return panels", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");

  assert.match(
    source,
    /<div className="qs-dual-divider" \/>/,
    "qs-dual-divider not found between panels — return panel would be invisible",
  );
});

test("quick-search route renders an explicit swap button", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");

  assert.match(source, /swapRouteInputs/);
  assert.match(source, /className="qs-route-swap"/);
  assert.match(source, /aria-label=\{t\("swapRouteAria"\)\}/);
});

test("QuickSearchDualWorkspace uses 3-column grid from CSS", () => {
  const dualCssPath = path.join(
    process.cwd(),
    "src",
    "styles",
    "quick-search-dual.css",
  );
  const css = fs.readFileSync(dualCssPath, "utf8");

  assert.match(
    css,
    /grid-template-columns:\s*1fr\s+1px\s+1fr/,
    "qs-dual-workspace must use 3‑column grid (1fr 1px 1fr)",
  );
});

test("dual divider has visual ::after pseudo‑element for gradient", () => {
  const dualCssPath = path.join(
    process.cwd(),
    "src",
    "styles",
    "quick-search-dual.css",
  );
  const css = fs.readFileSync(dualCssPath, "utf8");

  assert.match(css, /\.qs-dual-divider/);
  assert.match(css, /\.qs-dual-divider::after/);
  assert.match(css, /qs-outbound-ink/);
  assert.match(css, /qs-return-ink/);
});

// ── 4. Per‑side pagination ───────────────────────────────────────────

test("outbound and return panels have independent pagination", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");

  // Outbound uses outboundSide for pagination
  assert.match(
    source,
    /outboundSide\.goToPage/,
    "outbound panel missing per‑side goToPage",
  );
  assert.match(
    source,
    /outboundSide\.currentPage/,
    "outbound panel missing per‑side currentPage",
  );

  // Return uses returnSide for pagination
  assert.match(
    source,
    /returnSide\.goToPage/,
    "return panel missing per‑side goToPage",
  );
  assert.match(
    source,
    /returnSide\.currentPage/,
    "return panel missing per‑side currentPage",
  );

  // Outbound pagination gated by outbound searchState
  assert.match(
    source,
    /outboundSide\.searchState === "success"/,
    "outbound pagination missing searchState gate",
  );

  // Return pagination gated by return searchState
  assert.match(
    source,
    /returnSide\.searchState === "success"/,
    "return pagination missing searchState gate",
  );
});

test("pagination uses page presentation instead of full search loading", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");
  const sideHookPath = path.join(
    process.cwd(),
    "src",
    "modules",
    "quick-search",
    "state",
    "useQuickSearchSide.ts",
  );
  const sideHookSource = fs.readFileSync(sideHookPath, "utf8");

  assert.match(source, /presentation:\s*"page"/);
  assert.match(source, /isPageChanging/);
  assert.match(sideHookSource, /presentation\?:\s*"search"\s*\|\s*"page"/);
  assert.match(sideHookSource, /runSearch\(params,\s*page,\s*\{\s*presentation:\s*"page"\s*\}\)/);
  assert.doesNotMatch(sideHookSource, /void runSearch\(params,\s*page\);/);
});

test("dual workspace renders per-side view controls and independent state", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");

  assert.match(source, /outboundViewState/);
  assert.match(source, /returnViewState/);
  assert.match(source, /<QuickSearchSideViewControls/);
  assert.match(source, /title=\{t\("sideViewControlsOutboundTitle"\)\}/);
  assert.match(source, /title=\{t\("sideViewControlsReturnTitle"\)\}/);
  assert.match(source, /outboundPanelState\.visibleResults/);
  assert.match(source, /returnPanelState\.visibleResults/);
});

// ── 5. Combined banner conditional rendering ─────────────────────────

test("QuickSearchCombinedBanner is imported and rendered in dual workspace", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");

  assert.match(
    source,
    /import.*QuickSearchCombinedBanner/,
    "QuickSearchCombinedBanner not imported",
  );
  assert.match(
    source,
    /<QuickSearchCombinedBanner/,
    "QuickSearchCombinedBanner not rendered",
  );
  assert.match(source, /const dualCombinationVisible =/);
  assert.match(source, /outboundPanelState\.visibleResults\.length > 0/);
  assert.match(source, /returnPanelState\.visibleResults\.length > 0/);
});

test("combined banner receives combined price and per‑side formatMoney", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");

  // Per‑side formatMoney helpers exist
  assert.match(source, /formatMoneyOutbound/);
  assert.match(source, /formatMoneyReturn/);

  // The banner receives per‑side data
  assert.match(source, /outboundSide\.results/);
  assert.match(source, /returnSide\.results/);
  assert.match(source, /outboundSide\.searchMeta/);
  assert.match(source, /returnSide\.searchMeta/);
});

test("save combination callback uses findCombinationResult helper", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");

  assert.match(
    source,
    /findCombinationResult\(outboundPanelState\.visibleResults,\s*outboundSide\.selectedResultId\)/,
    "save callback missing findCombinationResult for outbound",
  );
  assert.match(
    source,
    /findCombinationResult\(returnPanelState\.visibleResults,\s*returnSide\.selectedResultId\)/,
    "save callback missing findCombinationResult for return",
  );
  assert.match(
    source,
    /saveCombination\.saveCombination\(\{/,
    "save callback missing saveCombination call",
  );
  assert.match(
    source,
    /groupId:\s*crypto\.randomUUID\(\)/,
    "save callback missing groupId generation",
  );
});

// ── 6. Dual mode flag guards ─────────────────────────────────────────

test("isDualMode excludes country‑only scope", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");

  // isDualMode must not be true when country‑only is active
  const isDualModePattern =
    /isDualMode\s*=\s*isReturn\s*&&\s*!!returnDate\s*&&\s*!!travelDate\s*&&\s*routeInputsValid\s*&&\s*!originCountryOnly\s*&&\s*!destinationCountryOnly/;
  assert.match(
    source,
    isDualModePattern,
    "isDualMode must exclude country‑only scope (!originCountryOnly && !destinationCountryOnly)",
  );
});

test("dual mode cleanup resets both sides on exit", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");

  assert.match(source, /wasDualModeRef/);
  assert.match(source, /outboundSide\.reset\(\)/);
  assert.match(source, /returnSide\.reset\(\)/);
  assert.match(source, /saveCombination\.reset\(\)/);
});

test("dual submit uses buildDualSearchParams helper", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");

  assert.match(
    source,
    /buildDualSearchParams\(\{/,
    "dual submit must use buildDualSearchParams helper",
  );

  // Return leg must invert IATA
  assert.match(
    source,
    /origin:\s*destination,/,
    "return leg missing inverted origin (must use destination)",
  );
  assert.match(
    source,
    /destination:\s*origin,/,
    "return leg missing inverted destination (must use origin)",
  );
  assert.match(
    source,
    /travelDate:\s*returnDate,/,
    "return leg must use returnDate as travelDate",
  );
});

// ── 7. Date grid layout ───────────────────────────────────────────────

test("qs-date-grid uses explicit column layout (not auto‑fit)", () => {
  const cssPath = path.join(
    process.cwd(),
    "src",
    "styles",
    "screens.css",
  );
  const css = fs.readFileSync(cssPath, "utf8");

  // The grid must NOT use auto‑fit (which caused misalignment)
  assert.doesNotMatch(
    css,
    /\.qs-date-grid\s*\{[^}]*grid-template-columns:\s*repeat\(auto-fit/,
    "qs-date-grid should not use repeat(auto-fit) — causes misalignment",
  );

  // Must have explicit columns
  assert.match(
    css,
    /\.qs-date-grid\s*\{[^}]*grid-template-columns:\s*1fr\s+auto/,
    "qs-date-grid missing explicit 1fr auto grid columns",
  );
});

test("qs-date-grid has conditional has-return modifier", () => {
  const cssPath = path.join(
    process.cwd(),
    "src",
    "styles",
    "screens.css",
  );
  const css = fs.readFileSync(cssPath, "utf8");

  assert.match(
    css,
    /\.qs-date-grid\.has-return/,
    "missing .qs-date-grid.has-return rule for 3‑column layout",
  );

  assert.match(
    css,
    /qs-date-grid\.has-return\s*\{[^}]*grid-template-columns:\s*1fr\s+auto\s+1fr/,
    ".has-return must use 1fr auto 1fr for 3 columns",
  );
});

test("dual workspace hover wiring is scoped to round-trip panels", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");

  assert.match(
    source,
    /const \[dualHoverSide, setDualHoverSide\] = useState<"outbound" \| "return" \| null>\(null\);/,
    "dual hover state missing from QuickSearchView",
  );
  assert.match(
    source,
    /<QuickSearchDualWorkspace ariaLabel="Round-trip results" hoveredSide=\{dualHoverSide\}>/,
    "dual workspace missing hoveredSide wiring",
  );
  assert.match(
    source,
    /onHoverStart=\{\(\) => setDualHoverSide\("outbound"\)\}/,
    "outbound panel missing hover start wiring",
  );
  assert.match(
    source,
    /onHoverStart=\{\(\) => setDualHoverSide\("return"\)\}/,
    "return panel missing hover start wiring",
  );
  assert.match(
    source,
    /onHoverEnd=\{\(\) => setDualHoverSide\(null\)\}/,
    "dual hover state must reset on hover end",
  );
});

test("dual workspace hover styles only apply on hover-capable desktop viewports", () => {
  const dualCssPath = path.join(
    process.cwd(),
    "src",
    "styles",
    "quick-search-dual.css",
  );
  const css = fs.readFileSync(dualCssPath, "utf8");

  assert.match(
    css,
    /@media \(min-width: 900px\) and \(hover: hover\) and \(pointer: fine\)/,
    "hover effect must be limited to desktop hover-capable devices",
  );
  assert.match(
    css,
    /data-hovered-side="outbound"\]\s+\.qs-dual-panel--return/,
    "outbound hover must dim the return panel",
  );
  assert.match(
    css,
    /data-hovered-side="return"\]\s+\.qs-dual-panel--outbound/,
    "return hover must dim the outbound panel",
  );
  assert.match(
    css,
    /opacity:\s*0\.74/,
    "dimmed panel opacity must stay legible",
  );
  assert.match(
    css,
    /transition:\s*\n\s*opacity 180ms ease,/,
    "dual panel hover needs a smooth opacity transition",
  );
});
