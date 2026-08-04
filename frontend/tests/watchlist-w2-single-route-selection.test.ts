import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const WATCHLIST_PAGE = path.join(process.cwd(), "src", "app", "(private)", "watchlist", "page.tsx");
const HISTORY_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "HistoryIntegratedPanel.tsx");
const DETAIL_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "WatchDetailPanel.tsx");

const FORBIDDEN_WATCHLIST_COPY = ["Back", "Flight Watchlist", "Add flight", "Quick start", "Last update", "Min", "Max"];

test("W2: history panel keeps the selected date without repeating the route", () => {
  const source = fs.readFileSync(HISTORY_PANEL, "utf8");

  assert.match(source, /history-route-line-text/);
  assert.match(source, /selectedWatch\.travel_date_local/);
  assert.doesNotMatch(source, /selectedWatch\.origin_iata\}\s*→\s*\$\{selectedWatch\.destination_iata\}/);

  assert.doesNotMatch(source, /name="history_origin"/);
  assert.doesNotMatch(source, /name="history_destination"/);
  assert.doesNotMatch(source, /name="history_dates"/);

  assert.doesNotMatch(source, /name="history_range"/);
  assert.doesNotMatch(source, /name="history_point"/);
  assert.match(source, /watchlist\.history\.viewCalendar|watchlist\.history\.viewChart/);
});

test("W2: history panel shows empty state when no selected route", () => {
  const source = fs.readFileSync(HISTORY_PANEL, "utf8");
  assert.match(source, /watchlist\.history\.selectedRouteEmpty/);
  assert.match(source, /!hasSelectedWatch/);
});

test("W2: page wires the same selected route into detail and history panels", () => {
  const pageSource = fs.readFileSync(WATCHLIST_PAGE, "utf8");
  const detailSource = fs.readFileSync(DETAIL_PANEL, "utf8");

  assert.match(pageSource, /<WatchDetailPanel[\s\S]*selectedWatch=\{derived\.selectedWatch\}/);
  assert.match(pageSource, /<HistoryIntegratedPanel[\s\S]*selectedWatch=\{derived\.selectedWatch\}/);
  assert.match(detailSource, /selectedWatch:/);
  assert.match(detailSource, /watch-detail-route[\s\S]*focus\.travel_date_local/);
  assert.doesNotMatch(detailSource, /<strong>\{focus\.origin_iata\}[\s\S]*focus\.destination_iata/);
});

test("W2: watchlist page keeps forbidden EN literals blocked", () => {
  const source = fs.readFileSync(WATCHLIST_PAGE, "utf8");
  for (const snippet of FORBIDDEN_WATCHLIST_COPY) {
    assert.equal(source.includes(snippet), false, `watchlist page still contains forbidden EN copy: ${snippet}`);
  }
});

