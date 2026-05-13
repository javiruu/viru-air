import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const WATCHLIST_PAGE = path.join(process.cwd(), "src", "app", "(private)", "watchlist", "page.tsx");
const COMPARE_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "ComparePanels.tsx");
const MAP_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "WatchlistMapDecisionPanel.tsx");

const FORBIDDEN_WATCHLIST_COPY = ["Back", "Flight Watchlist", "Add flight", "Quick start", "Last update"];

test("W1: watchlist layout renders decision workspace before history", () => {
  const source = fs.readFileSync(WATCHLIST_PAGE, "utf8");

  const listPos = source.indexOf("<SmartWatchListPanel");
  const detailPos = source.indexOf("<WatchDetailPanel");
  const historyPos = source.indexOf("<HistoryIntegratedPanel");
  const comparePos = source.indexOf("<ComparePanels");
  const mapPos = source.indexOf("<WatchlistMapDecisionPanel");

  assert.ok(listPos >= 0, "SmartWatchListPanel must render");
  assert.ok(detailPos >= 0, "WatchDetailPanel must render");
  assert.ok(historyPos >= 0, "HistoryIntegratedPanel must render");
  assert.ok(comparePos >= 0, "ComparePanels must render");
  assert.ok(mapPos >= 0, "WatchlistMapDecisionPanel must render");

  assert.ok(listPos < historyPos, "list must appear before history in page composition");
  assert.ok(detailPos < historyPos, "detail must appear before history in page composition");
  assert.ok(historyPos < comparePos, "history must appear before compare");
  assert.ok(comparePos < mapPos, "compare must appear before map");
});

test("W1: watchlist route source keeps EN blocked literals out", () => {
  const source = fs.readFileSync(WATCHLIST_PAGE, "utf8");
  for (const snippet of FORBIDDEN_WATCHLIST_COPY) {
    assert.equal(source.includes(snippet), false, `watchlist page still contains forbidden EN copy: ${snippet}`);
  }
});

test("W1: compare and map feature blocks keep required labels", () => {
  const compareSource = fs.readFileSync(COMPARE_PANEL, "utf8");
  const mapSource = fs.readFileSync(MAP_PANEL, "utf8");

  assert.match(compareSource, /watchlist\.compare\.title/);
  assert.match(mapSource, /watchlist\.map\.title|Mapa de rutas/);
});
