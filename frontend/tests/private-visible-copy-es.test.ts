import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const DASHBOARD_PAGE = path.join(process.cwd(), "src", "app", "(private)", "dashboard", "page.tsx");
const WATCHLIST_PAGE = path.join(process.cwd(), "src", "app", "(private)", "watchlist", "page.tsx");
const HISTORY_PAGE = path.join(process.cwd(), "src", "app", "(private)", "history", "page.tsx");
const ALERTS_PAGE = path.join(process.cwd(), "src", "app", "(private)", "alerts", "page.tsx");
const QUICK_SEARCH_PAGE = path.join(process.cwd(), "src", "app", "(private)", "quick-search", "page.tsx");
const PREFERENCES_PAGE = path.join(process.cwd(), "src", "app", "(private)", "preferences", "page.tsx");
const SUGGESTIONS_PAGE = path.join(process.cwd(), "src", "app", "(private)", "suggestions", "page.tsx");

const FORBIDDEN_DASHBOARD_COPY = [
  "Quick start",
  "Got it",
];

const FORBIDDEN_WATCHLIST_COPY = [
  "Back",
  "Flight Watchlist",
  "Add flight",
  "Quick start",
  "Got it",
  "Last update:",
];

const FORBIDDEN_HISTORY_COPY = [
  "Redirecting to the unified panel",
  "History is now part of Flight Watchlist.",
];

const FORBIDDEN_PRIVATE_COPY_LITERALS = [
  /["'`]Back["'`]/,
  /["'`]Flight Watchlist["'`]/,
  /["'`]Add flight["'`]/,
  /["'`]Quick start["'`]/,
  /["'`]Got it["'`]/,
  /["'`]Last update:["'`]/,
];

test("private session routes avoid forbidden EN copy for ES locale", () => {
  const dashboardSource = fs.readFileSync(DASHBOARD_PAGE, "utf8");
  const watchlistSource = fs.readFileSync(WATCHLIST_PAGE, "utf8");
  const historySource = fs.readFileSync(HISTORY_PAGE, "utf8");
  const alertsSource = fs.readFileSync(ALERTS_PAGE, "utf8");
  const quickSearchSource = fs.readFileSync(QUICK_SEARCH_PAGE, "utf8");
  const preferencesSource = fs.readFileSync(PREFERENCES_PAGE, "utf8");
  const suggestionsSource = fs.readFileSync(SUGGESTIONS_PAGE, "utf8");
  const privateSources = [
    dashboardSource,
    watchlistSource,
    historySource,
    alertsSource,
    quickSearchSource,
    preferencesSource,
    suggestionsSource,
  ];

  for (const snippet of FORBIDDEN_DASHBOARD_COPY) {
    assert.equal(dashboardSource.includes(snippet), false, `dashboard still contains: ${snippet}`);
  }
  for (const snippet of FORBIDDEN_WATCHLIST_COPY) {
    assert.equal(watchlistSource.includes(snippet), false, `watchlist still contains: ${snippet}`);
  }
  for (const snippet of FORBIDDEN_HISTORY_COPY) {
    assert.equal(historySource.includes(snippet), false, `history still contains: ${snippet}`);
  }
  for (const snippet of FORBIDDEN_PRIVATE_COPY_LITERALS) {
    for (const source of privateSources) {
      assert.doesNotMatch(source, snippet, `private source still contains forbidden EN copy: ${snippet}`);
    }
  }
});
