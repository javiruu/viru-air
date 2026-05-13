import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const WATCHLIST_PAGE = path.join(process.cwd(), "src", "app", "(private)", "watchlist", "page.tsx");
const SMART_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "SmartWatchListPanel.tsx");
const DETAIL_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "WatchDetailPanel.tsx");
const HISTORY_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "HistoryIntegratedPanel.tsx");
const COMPARE_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "ComparePanels.tsx");
const WATCHLIST_I18N = path.join(process.cwd(), "src", "i18n", "domains", "watchlist.ts");

const FORBIDDEN_EN_COPY = ["Back", "Flight Watchlist", "Add flight", "Quick start", "Last update", "Min", "Max"];

test("W9.1: watchlist keeps main surfaces and removes detail calendar table", () => {
  const page = fs.readFileSync(WATCHLIST_PAGE, "utf8");
  const detail = fs.readFileSync(DETAIL_PANEL, "utf8");

  assert.match(page, /<HistoryIntegratedPanel/);
  assert.match(page, /<ComparePanels/);
  assert.match(page, /<WatchlistMapDecisionPanel/);

  assert.doesNotMatch(detail, /Calendario/);
  assert.doesNotMatch(detail, /Los precios son orientativos y dependen de la frescura del proveedor\./);
  assert.doesNotMatch(detail, /Día|Mín|Máx|Media|Capturas|Señal/);
  assert.doesNotMatch(detail, /prices\/calendar/);
});

test("W9.1: route separators use arrows and never question marks", () => {
  const detail = fs.readFileSync(DETAIL_PANEL, "utf8");
  const smart = fs.readFileSync(SMART_PANEL, "utf8");
  const history = fs.readFileSync(HISTORY_PANEL, "utf8");
  const compare = fs.readFileSync(COMPARE_PANEL, "utf8");

  assert.match(detail, /origin_iata\} \{"→"\} \{focus\.destination_iata\}/);
  assert.match(smart, /\{" → "\}/);
  assert.match(history, /origin_iata\} → \$\{selectedWatch\.destination_iata\}/);
  assert.match(compare, /\{option\.origin\} \{"->"\} \{option\.destination\}/);
  assert.match(compare, /<strong>\{origin\} \{"->"\} \{destination\}<\/strong>/);

  assert.doesNotMatch(history, /\$\{selectedWatch\.origin_iata\} \? \$/);
  assert.doesNotMatch(compare, /\{option\.origin\} \? \{option\.destination\}/);
  assert.doesNotMatch(compare, /<strong>\{origin\} \? \{destination\}<\/strong>/);
});

test("W9.1: no duplicate 'Rango RANGO' and confidence copy remains intact", () => {
  const history = fs.readFileSync(HISTORY_PANEL, "utf8");
  const detail = fs.readFileSync(DETAIL_PANEL, "utf8");
  const i18n = fs.readFileSync(WATCHLIST_I18N, "utf8");

  assert.match(history, /watchlist\.history\.rangeTitle/);
  assert.match(history, /aria-label=\{t\("watchlist\.history\.rangeLabel"\)\}/);
  assert.doesNotMatch(history, /history-range-label/);

  assert.match(detail, /history-confidence-notice/);
  assert.match(i18n, /limitedTitle:\s*"Histórico limitado"/);
  assert.match(i18n, /limitedMessage:\s*"Hay pocas capturas\. Interpreta la tendencia con cautela\."/);
});

test("W9.1: watchlist remains free of blocked EN copy", () => {
  const page = fs.readFileSync(WATCHLIST_PAGE, "utf8");
  for (const snippet of FORBIDDEN_EN_COPY) {
    assert.equal(page.includes(snippet), false, `watchlist page still contains forbidden EN copy: ${snippet}`);
  }
});
