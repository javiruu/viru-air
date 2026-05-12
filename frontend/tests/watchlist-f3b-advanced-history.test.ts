import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const DETAIL_PANEL_FILE = path.join(process.cwd(), "src", "modules", "watchlist", "components", "WatchDetailPanel.tsx");
const COMPARE_PANEL_FILE = path.join(process.cwd(), "src", "modules", "watchlist", "components", "ComparePanels.tsx");
const VIEW_STATE_FILE = path.join(process.cwd(), "src", "modules", "watchlist", "useWatchlistViewState.ts");

test("watch detail panel consumes prices calendar and renders empty/data copy", () => {
  const source = fs.readFileSync(DETAIL_PANEL_FILE, "utf8");
  assert.match(source, /apiFetch<PriceCalendarResponse>\(`\/prices\/calendar\?watch_id=\$\{selectedWatch\.id\}`\)/);
  assert.match(source, /Aún no hay suficientes capturas para crear un calendario\./);
  assert.match(source, /Los precios son orientativos y dependen de la frescura del proveedor\./);
});

test("compare panel consumes compare endpoint and uses required states", () => {
  const source = fs.readFileSync(COMPARE_PANEL_FILE, "utf8");
  assert.match(source, /apiFetch<PriceCompareResponse>\(`\/prices\/compare\?watch_ids=\$\{compareQuery\}`\)/);
  assert.match(source, /Selecciona entre 2 y 4 rutas para comparar\./);
  assert.match(source, /Hay monedas distintas; compara con cuidado\./);
  assert.doesNotMatch(source, />Min</);
  assert.doesNotMatch(source, />Max</);
  assert.match(source, /Mínimo|MÃ­nimo/);
  assert.match(source, /Máximo|MÃ¡ximo/);
  assert.match(source, /Volatilidad: \{volatilityLabel\(card\.volatility_hint\)\}/);
  assert.match(source, /compareBadgesFromResponse/);
  assert.doesNotMatch(source, /compareBadges\?\.bestPriceId === card\.watch_id/);
  assert.doesNotMatch(source, /compareBadges\?\.stableId === card\.watch_id/);
});

test("compare selection keeps max 4 guard", () => {
  const source = fs.readFileSync(VIEW_STATE_FILE, "utf8");
  assert.match(source, /if \(prev\.length >= 4\)/);
  assert.match(source, /Puedes comparar hasta 4 vuelos a la vez\./);
});
