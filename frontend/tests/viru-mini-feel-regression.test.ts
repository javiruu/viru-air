/**
 * Viru mini-feel regression suite
 * --------------------------------
 * Covers the recent cosmetic mini-features (not #6 / #7 by user request).
 * Keeps the suite resilient and additive: copy keys, surface classes,
 * selectors and minimal structural presence — no runtime rendering.
 */
import { strict as assert } from "node:assert";
import { test } from "node:test";
import fs from "node:fs";
import path from "node:path";

const ROOT = path.join(process.cwd(), "src");
const TESTS_ROOT = process.cwd();

const read = (relativePath: string) => {
  const abs = fs.existsSync(path.join(ROOT, relativePath))
    ? path.join(ROOT, relativePath)
    : path.join(process.cwd(), relativePath);
  return fs.readFileSync(abs, "utf8");
};

// ── #1 Swap O/D flight-path (animated via .route-pulse already wired) ──
test("animated route swap adds a Bezier flight-path via CSS", () => {
  const css = read("styles/components.css");
  assert.match(css, /@keyframes routeSwapFlightPath/, "missing @keyframes in components.css");
  assert.match(
    css,
    /\.route-pulse\s+\.qs-route-line/,
    "missing route-pulse wiring in components.css",
  );
  assert.match(
    css,
    /@media \(prefers-reduced-motion: no-preference\)[\s\S]*?\.route-pulse\s+\.qs-route-line/,
    "swap path animation must respect prefers-reduced-motion",
  );
});

test("swap animation coexists with the existing routePulse in screens.css", () => {
  const screens = read("styles/screens.css");
  assert.match(screens, /\.route-pulse/, "screens.css no longer drives .route-pulse");
});

// ── #2/#3 Empty-state softline + honest calendar copy ──────────────────
test("QuickSearchStatePanels renders empty softline + calendar fallback", () => {
  const source = read("modules/quick-search/components/QuickSearchStatePanels.tsx");
  assert.match(source, /qs-empty-calendar-fallback/, "missing calendar fallback class wiring");
  assert.match(source, /qs-empty-softline/, "missing softline class wiring");
  assert.match(
    source,
    /props\.zeroResultActions\.length === 1/,
    "softline should only appear when there is exactly one relax action"
  );
});

// ── #4 Microtoast preserved (skipped by design — locked working tree) ──
test("QuickSearchView still saves resume snapshot (no microtoast regression)", () => {
  const source = read("modules/quick-search/QuickSearchView.tsx");
  assert.match(source, /saveResumeSearchSnapshot/, "snapshot save call missing — no regressions wanted");
});

// ── #5 Watchlist price-delta percent chip ─────────────────────────────
test("SmartWatchListPanel computes trend-percent delta and renders the chip", () => {
  const source = read("modules/watchlist/components/SmartWatchListPanel.tsx");
  assert.match(source, /trendPercentLabel/, "missing trendPercentLabel wiring");
  assert.match(source, /trend-chip-percent/, "missing trend-chip-percent rendering");
  assert.doesNotMatch(
    source,
    /trend-chip-percent"[^>]*>{trendPercentLabel}<\/span>(\s|\S)*<svg[\s\S]*?d="M6 15l6-6 6 6"/,
    "trend chip order must keep percent after delta label, before closing span",
  );
  // i18n key wired
  assert.match(source, /watchlist\.smartList\.trendPercentDelta/, "missing i18n key wiring");
});

test("watchlist i18n exposes trendPercentDelta in es + en", () => {
  const en = read("i18n/domains/watchlist.ts");
  assert.match(en, /trendPercentDelta: ".*% vs previous period"/, "missing EN copy");
  assert.match(en, /trendPercentDelta: ".*% vs periodo anterior"/, "missing ES copy");
});

// ── #8/#9/#10 Dashboard mini feel (eyebrow + buen día + última nota) ──
test("Dashboard page wires season eyebrow + good day + latest note pill", () => {
  const source = read("app/(private)/dashboard/page.tsx");
  assert.match(source, /seasonModeKey/, "missing seasonal eyebrow state");
  assert.match(source, /upcomingWatch/, "missing good-day-to-fly data");
  assert.match(source, /draftNote/, "missing latest-note pill data");
  assert.match(source, /dashboard-season-eyebrow/, "missing season eyebrow class");
  assert.match(source, /good-day-to-fly/, "missing good day block class");
  assert.match(source, /latest-note-pill/, "missing latest note pill class");
  assert.match(source, /dashboard\.hero\.seasonEyebrow/, "missing i18n eyebrow lookup");
});

test("dashboard hero seasonal i18n exists in es + en", () => {
  const en = read("i18n/domains/dashboard.ts");
  assert.match(en, /seasonEyebrow: \{/, "missing season eyebrow structured key");
  assert.match(en, /summer: "(?:☀️ )?Modo veraniego"/, "missing ES summer copy");
  assert.match(en, /summer: "(?:☀️ )?Summer mode"/, "missing EN summer copy");
  assert.match(en, /winter: "(?:❄️ )?Modo invierno"/, "missing ES winter copy");
  assert.match(en, /festive: "(?:🎉 )?Modo festivo"/, "missing ES festive copy");
  assert.match(en, /goodDayToFly:/, "missing good-day-to-fly copy");
  assert.match(en, /latestNotePill:/, "missing latest-note pill copy");
});

// ── #11/#12 Door-to-Door timezone pill + known-route tag ──────────────
test("DoorToDoorPanel renders timezone pill + known-route tag", () => {
  const source = read("modules/door-to-door/DoorToDoorPanel.tsx");
  assert.match(source, /d2d-timezone-pill/, "missing timezone pill class");
  assert.match(source, /d2d-known-route-tag/, "missing known-route tag class");
  assert.match(source, /userTimeZone/, "missing timezone computation");
  assert.match(source, /(?:knownRouteCount|history\.history\.length)\s*>\s*1/, "missing known-route history rule");
  assert.match(source, /doorToDoor\.form\.timezonePill/, "missing timezone i18n lookup");
  assert.match(source, /doorToDoor\.form\.knownRouteTag/, "missing known-route i18n lookup");
});

test("doorToDoor i18n exposes timezone + known-route copy in es + en", () => {
  const en = read("i18n/domains/doorToDoor.ts");
  assert.match(en, /timezonePill: "Aqu[^"]*est[^"]*: \{zone\}"/, "missing ES timezone pill copy");
  assert.match(en, /timezonePill: "You are here: \{zone\}"/, "missing EN timezone pill copy");
  assert.match(en, /knownRouteTag:/, "missing known-route tag copy");
  assert.match(en, /knownRouteTooltip:/, "missing known-route tooltip copy");
  assert.match(en, /timezoneAria:/, "missing timezone aria-label copy");
});

// ── Cross-cutting CSS surface check ───────────────────────────────────
test("components.css exposes every mini-feel surface class", () => {
  const css = read("styles/components.css");
  for (const cls of [
    "qs-empty-softline",
    "qs-empty-calendar-fallback",
    "trend-chip-percent",
    "dashboard-season-eyebrow",
    "good-day-to-fly",
    "latest-note-pill",
    "d2d-timezone-pill",
    "d2d-known-route-tag",
    "@keyframes routeSwapFlightPath",
  ]) {
    assert.ok(css.includes(cls), `components.css missing surface: ${cls}`);
  }
});
