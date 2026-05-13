import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const DETAIL_PANEL_FILE = path.join(process.cwd(), "src", "modules", "watchlist", "components", "WatchDetailPanel.tsx");
const COMPARE_PANEL_FILE = path.join(process.cwd(), "src", "modules", "watchlist", "components", "ComparePanels.tsx");
const VIEW_STATE_FILE = path.join(process.cwd(), "src", "modules", "watchlist", "useWatchlistViewState.ts");

test("watch detail panel removes tabular calendar block and calendar fetch", () => {
  const source = fs.readFileSync(DETAIL_PANEL_FILE, "utf8");
  assert.doesNotMatch(source, /prices\/calendar/);
  assert.doesNotMatch(source, /Calendario/);
  assert.doesNotMatch(source, /Los precios son orientativos y dependen de la frescura del proveedor\./);
  assert.doesNotMatch(source, /Día|Mín|Máx|Media|Capturas|Señal/);
});

test("compare panel consumes compare endpoint and uses required states", () => {
  const source = fs.readFileSync(COMPARE_PANEL_FILE, "utf8");
  assert.match(source, /apiFetch<PriceCompareResponse>\(`\/prices\/compare\?watch_ids=\$\{compareQuery\}`\)/);
  assert.match(source, /watchlist\.compare\.emptySelectionMessage/);
  assert.match(source, /watchlist\.compare\.oneSelectionMessage/);
  assert.match(source, /watchlist\.compare\.mixedCurrencyWarning/);
  assert.match(source, /watchlist\.compare\.volatility/);
  assert.match(source, /compareBadgesFromResponse/);
  assert.doesNotMatch(source, /compareBadges\?\.bestPriceId === card\.watch_id/);
  assert.doesNotMatch(source, /compareBadges\?\.stableId === card\.watch_id/);
});

test("compare selection keeps max 4 guard", () => {
  const source = fs.readFileSync(VIEW_STATE_FILE, "utf8");
  assert.match(source, /if \(prev\.length >= 4\)/);
  assert.match(source, /watchlist\.compare\.maxSelectionMessage/);
});
