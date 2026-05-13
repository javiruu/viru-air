import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const WATCHLIST_PAGE = path.join(process.cwd(), "src", "app", "(private)", "watchlist", "page.tsx");
const SMART_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "SmartWatchListPanel.tsx");
const DETAIL_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "WatchDetailPanel.tsx");
const HISTORY_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "HistoryIntegratedPanel.tsx");
const MAP_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "WatchlistMapDecisionPanel.tsx");
const COMPARE_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "ComparePanels.tsx");
const SUMMARY = path.join(process.cwd(), "src", "modules", "watchlist", "summary.ts");

const FORBIDDEN_EN_COPY = ["Back", "Flight Watchlist", "Add flight", "Quick start", "Last update", "Min", "Max"];

test("W9: main reading order remains routes -> detail -> history -> compare -> map", () => {
  const source = fs.readFileSync(WATCHLIST_PAGE, "utf8");
  const listPos = source.indexOf("<SmartWatchListPanel");
  const detailPos = source.indexOf("<WatchDetailPanel");
  const historyPos = source.indexOf("<HistoryIntegratedPanel");
  const comparePos = source.indexOf("<ComparePanels");
  const mapPos = source.indexOf("<WatchlistMapDecisionPanel");

  assert.ok(listPos >= 0 && detailPos >= 0 && historyPos >= 0 && comparePos >= 0 && mapPos >= 0);
  assert.ok(listPos < detailPos);
  assert.ok(detailPos < historyPos);
  assert.ok(historyPos < comparePos);
  assert.ok(comparePos < mapPos);
});

test("W9: old/forbidden copy does not reappear in watchlist page", () => {
  const source = fs.readFileSync(WATCHLIST_PAGE, "utf8");
  assert.equal(source.includes("Lista inteligente de vuelos"), false);
  for (const snippet of FORBIDDEN_EN_COPY) {
    assert.equal(source.includes(snippet), false, `watchlist page still contains forbidden EN copy: ${snippet}`);
  }
});

test("W9: history keeps single selected-route model without editable route filters", () => {
  const source = fs.readFileSync(HISTORY_PANEL, "utf8");
  assert.match(source, /watchlist\.history\.selectedRouteLabel/);
  assert.doesNotMatch(source, /Origen/);
  assert.doesNotMatch(source, /Destino/);
  assert.doesNotMatch(source, /Fechas de vuelo/);
});

test("W9: bulk toolbar remains contextual and hidden with zero selection", () => {
  const source = fs.readFileSync(SMART_PANEL, "utf8");
  assert.match(source, /const hasSelection = selectedIds\.length > 0;/);
  assert.match(source, /\{hasSelection \? \(/);
  assert.match(source, /data-testid="watchlist-bulk-toolbar"/);
});

test("W9: historical confidence and actionable freshness remain visible in detail/list flow", () => {
  const detailSource = fs.readFileSync(DETAIL_PANEL, "utf8");
  const smartSource = fs.readFileSync(SMART_PANEL, "utf8");
  const summarySource = fs.readFileSync(SUMMARY, "utf8");

  assert.match(detailSource, /getHistoryConfidence\(summary\?\.count \?\? 0\)/);
  assert.match(summarySource, /watchlist\.summary\.historyConfidence\.initialTitle/);
  assert.match(summarySource, /watchlist\.summary\.historyConfidence\.limitedTitle/);
  assert.match(summarySource, /watchlist\.summary\.historyConfidence\.sufficientTitle/);
  assert.match(summarySource, /watchlist\.freshness\.updatedAgo/);
  assert.match(summarySource, /watchlist\.freshness\.lastUpdatedAgo/);
  assert.match(smartSource, /watchlist\.detail\.freshness/);
});

test("W9: map and compare keep non-contradictory and reactive states", () => {
  const mapSource = fs.readFileSync(MAP_PANEL, "utf8");
  const compareSource = fs.readFileSync(COMPARE_PANEL, "utf8");

  assert.doesNotMatch(mapSource, /No hay rutas activas para mostrar en el mapa\./);
  assert.match(mapSource, /watchlist\.map\.unavailableTitle/);
  assert.match(compareSource, /selectedCount === 0/);
  assert.match(compareSource, /selectedCount === 1/);
  assert.match(compareSource, /selectedCount > 4/);
  assert.match(compareSource, /watchlist\.compare\.mixedCurrencyWarning/);
});
