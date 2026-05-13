import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const WATCHLIST_PAGE = path.join(process.cwd(), "src", "app", "(private)", "watchlist", "page.tsx");
const SMART_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "SmartWatchListPanel.tsx");
const DETAIL_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "WatchDetailPanel.tsx");
const HISTORY_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "HistoryIntegratedPanel.tsx");
const COMPARE_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "ComparePanels.tsx");
const NAV_V1 = path.join(process.cwd(), "src", "modules", "shared", "navigationV1.ts");

const FORBIDDEN_WATCHLIST_COPY = ["Back", "Flight Watchlist", "Add flight", "Quick start", "Last update"];

test("W0: /watchlist render path keeps main building blocks wired", () => {
  const source = fs.readFileSync(WATCHLIST_PAGE, "utf8");

  assert.match(source, /<h1>\{t\("watchlist\.title"\)\}<\/h1>/);
  assert.match(source, /<SmartWatchListPanel/);
  assert.match(source, /<WatchDetailPanel/);
  assert.match(source, /<HistoryIntegratedPanel/);
  assert.match(source, /<ComparePanels/);
});

test("W0: watchlist list/detail/history/calendar/compare copies remain present in current baseline", () => {
  const smartPanel = fs.readFileSync(SMART_PANEL, "utf8");
  const detailPanel = fs.readFileSync(DETAIL_PANEL, "utf8");
  const historyPanel = fs.readFileSync(HISTORY_PANEL, "utf8");
  const comparePanel = fs.readFileSync(COMPARE_PANEL, "utf8");

  assert.match(smartPanel, /Lista inteligente de vuelos/);
  assert.match(detailPanel, /watchlist\.detail\.title/);
  assert.match(historyPanel, /watchlist\.history\.title|Histórico integrado|Historico integrado/);
  assert.match(detailPanel, /Calendario/);
  assert.match(comparePanel, /Comparativa multi-vuelo/);
});

test("W0: watchlist private copy keeps EN blocked literals out of route source", () => {
  const source = fs.readFileSync(WATCHLIST_PAGE, "utf8");
  for (const snippet of FORBIDDEN_WATCHLIST_COPY) {
    assert.equal(source.includes(snippet), false, `watchlist page still contains forbidden EN copy: ${snippet}`);
  }
});

test("W0: private navigation does not expose /suggestions as core module", () => {
  const source = fs.readFileSync(NAV_V1, "utf8");
  assert.doesNotMatch(source, /href:\s*"\/suggestions"/);
});

