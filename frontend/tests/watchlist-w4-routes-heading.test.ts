import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const SMART_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "SmartWatchListPanel.tsx");
const WATCHLIST_I18N = path.join(process.cwd(), "src", "i18n", "domains", "watchlist.ts");
const WATCHLIST_PAGE = path.join(process.cwd(), "src", "app", "(private)", "watchlist", "page.tsx");

const FORBIDDEN_WATCHLIST_COPY = ["Back", "Flight Watchlist", "Add flight", "Quick start", "Last update", "Min", "Max"];

test("W4: smart list heading uses rutas vigiladas copy and removes old long title", () => {
  const panelSource = fs.readFileSync(SMART_PANEL, "utf8");
  const i18nSource = fs.readFileSync(WATCHLIST_I18N, "utf8");

  assert.match(panelSource, /watchlist\.smartList\.heading/);
  assert.match(i18nSource, /heading:\s*"Rutas vigiladas"/);
  assert.doesNotMatch(panelSource, /Lista inteligente de vuelos/);
});

test("W4: search and sort controls remain visible in smart panel", () => {
  const panelSource = fs.readFileSync(SMART_PANEL, "utf8");

  assert.match(panelSource, /watchlist\.smartList\.search/);
  assert.match(panelSource, /watchlist\.smartList\.sort/);
  assert.match(panelSource, /watch-smart-search/);
  assert.match(panelSource, /watch-smart-sort/);
});

test("W4: summary copy uses rutas terminology and avoids vuelos in count line", () => {
  const panelSource = fs.readFileSync(SMART_PANEL, "utf8");
  const i18nSource = fs.readFileSync(WATCHLIST_I18N, "utf8");

  assert.match(panelSource, /watchlist\.smartList\.showingCount/);
  assert.match(i18nSource, /Mostrando \{shown\} de \{total\} rutas\./);
  assert.doesNotMatch(i18nSource, /Mostrando \{shown\} de \{total\} vuelos\./);
});

test("W4: watchlist page keeps forbidden EN literals blocked", () => {
  const source = fs.readFileSync(WATCHLIST_PAGE, "utf8");
  for (const snippet of FORBIDDEN_WATCHLIST_COPY) {
    assert.equal(source.includes(snippet), false, `watchlist page still contains forbidden EN copy: ${snippet}`);
  }
});
