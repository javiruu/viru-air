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
test("WatchRow only renders trend metadata when a previous snapshot exists", () => {
  const source = read("modules/watchlist/components/WatchRow.tsx");
  assert.match(source, /meta\?\.latest && meta\.previous/, "trend status must require two snapshots");
  assert.match(source, /meta\.previous \? \(/, "trend chip must require a previous snapshot");
});

test("WatchRow computes trend-percent delta and renders the chip", () => {
  const source = read("modules/watchlist/components/WatchRow.tsx");
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

test("Dashboard page restores the historical quick-search hero and keeps unread alerts inside the alerts card", () => {
  const source = read("app/(private)/dashboard/page.tsx");
  assert.match(source, /const heroCtaHref = ["']\/quick-search["']/, "hero CTA must point to quick search");
  assert.match(source, /dashboard_click_hero_cta/, "missing historical hero CTA tracking");
  assert.match(source, /dashboard-hero-actions/, "missing historical hero actions block");
  assert.match(source, /hero-empty/, "missing historical hero empty state");
  assert.match(source, /hero-opportunity/, "missing historical hero opportunity state");
  assert.doesNotMatch(source, /DashboardNextActionCard/, "next-best-action card must not replace the hero quick-search CTA");
  assert.match(source, /const unreadAlertsCount = notificationSummary\?\.unread \?\? 0/, "missing compact unread count");
  assert.match(source, /unreadAlertsCount\s*>\s*0/, "missing unread count guard");
  assert.match(source, /module-inline-status module-inline-status-warning/, "unread alert copy should live as compact card text");
  assert.doesNotMatch(source, /unread-alerts-banner/, "legacy custom class must be gone");
  assert.doesNotMatch(source, /data-testid="dashboard-unread-alerts-banner"/, "unused testid must be gone");
  assert.doesNotMatch(source, /dashboard_unread_alerts_banner_click/, "banner tracking should be gone");
  assert.match(
    source,
    /t\(\s*["']dashboard\.nextAction\.messages\.unreadAlerts["']\s*,\s*\{\s*count:\s*unreadAlertsCount\s*\}/,
    "missing title i18n lookup with count",
  );
  const heroSection = source.slice(source.indexOf("<section className=\"dashboard-hero-state\""), source.indexOf("<section className=\"dashboard-section dashboard-section-manage\""));
  assert.match(heroSection, /href=\{heroCtaHref\}/, "hero must render the quick-search CTA");
  assert.doesNotMatch(heroSection, /unreadAlertsCount|dashboard\.nextAction\.messages\.unreadAlerts|DashboardNextActionCard/, "hero must not render unread alerts or next-best-action");
});

test("dashboard i18n keeps the pre-existing unreadAlerts / viewAlerts copy (no new keys added)", () => {
  const i18n = read("i18n/domains/dashboard.ts");
  assert.match(i18n, /unreadAlerts:\s*"Tienes \{count\} alertas sin leer\."/, "missing ES unreadAlerts copy");
  assert.match(i18n, /unreadAlerts:\s*"You have \{count\} unread alerts\."/, "missing EN unreadAlerts copy");
  assert.match(i18n, /viewAlerts:\s*"Ver alertas"/, "missing ES viewAlerts CTA");
  assert.match(i18n, /viewAlerts:\s*"View alerts"/, "missing EN viewAlerts CTA");
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

test("global text selection uses dual-theme design tokens", () => {
  const base = read("styles/base.css");
  const tokens = read("styles/tokens.css");
  const selectionRule = base.match(/::selection\s*\{[\s\S]*?\}/);
  const darkTokens = tokens.match(/:root\[data-theme="dark"\]\s*\{[\s\S]*?\n\}/);

  assert.ok(selectionRule?.[0], "missing global ::selection rule");
  const selectionCss = selectionRule[0];
  assert.match(selectionCss, /background-color:\s*var\(--color-selection-bg\)/);
  assert.match(selectionCss, /color:\s*var\(--color-selection-text\)/);
  assert.match(base, /::-moz-selection\s*\{[\s\S]*?--color-selection-bg/, "missing Firefox selection fallback");
  assert.match(tokens, /--color-selection-bg:\s*color-mix\(in srgb,\s*var\(--accent\)/);
  assert.match(tokens, /--color-selection-text:\s*var\(--ink\)/);
  assert.ok(darkTokens?.[0], "missing dark theme token block");
  const darkTokenCss = darkTokens[0];
  assert.match(darkTokenCss, /--color-selection-bg:/, "missing dark selection background token");
  assert.match(darkTokenCss, /--color-selection-text:/, "missing dark selection text token");
});

// ── Cross-cutting CSS surface check ───────────────────────────────────
test("components.css exposes every mini-feel surface class still in use", () => {
  const css = read("styles/components.css");
  for (const cls of [
    "qs-empty-softline",
    "qs-empty-calendar-fallback",
    "trend-chip-percent",
    "d2d-timezone-pill",
    "d2d-known-route-tag",
    "@keyframes routeSwapFlightPath",
  ]) {
    assert.ok(css.includes(cls), `components.css missing surface: ${cls}`);
  }
});
