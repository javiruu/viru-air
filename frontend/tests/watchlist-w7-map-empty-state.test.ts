import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const WATCHLIST_PAGE = path.join(process.cwd(), "src", "app", "(private)", "watchlist", "page.tsx");
const MAP_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "WatchlistMapDecisionPanel.tsx");
const DERIVED = path.join(process.cwd(), "src", "modules", "watchlist", "useWatchlistDerived.ts");
const WATCHLIST_I18N = path.join(process.cwd(), "src", "i18n", "domains", "watchlist.ts");

const FORBIDDEN_EN_COPY = ["Back", "Flight Watchlist", "Add flight", "Quick start", "Last update", "Min", "Max"];

test("W7: con rutas pero sin geodatos utiles no aparece copy contradictorio", () => {
  const derived = fs.readFileSync(DERIVED, "utf8");
  const i18n = fs.readFileSync(WATCHLIST_I18N, "utf8");

  assert.doesNotMatch(derived, /No hay rutas activas para mostrar en el mapa\./);
  assert.match(i18n, /unavailableTitle:\s*"Mapa no disponible para estas rutas\."/);
  assert.match(i18n, /unavailableBody:/);
});

test("W7: sin rutas muestra empty state correcto y no contradictorio", () => {
  const derived = fs.readFileSync(DERIVED, "utf8");
  const panel = fs.readFileSync(MAP_PANEL, "utf8");
  const i18n = fs.readFileSync(WATCHLIST_I18N, "utf8");

  assert.match(panel, /hasWatchItems \? t\("watchlist\.map\.unavailableTitle"\) : t\("watchlist\.map\.emptyTitle"\)/);
  assert.match(derived, /watchlist\.map\.emptyTitle/);
  assert.match(i18n, /emptyTitle:/);
});

test("W7: cuando hay datos de mapa el panel sigue operativo", () => {
  const panel = fs.readFileSync(MAP_PANEL, "utf8");

  assert.match(panel, /if \(!hasMapData\)/);
  assert.match(panel, /<Map ref=\{mapRef\}/);
  assert.match(panel, /visibleRoutes\.map\(\(route\) =>/);
});

test("W7: mapa sigue en zona secundaria despues de comparativa (W1)", () => {
  const source = fs.readFileSync(WATCHLIST_PAGE, "utf8");
  const comparePos = source.indexOf("<ComparePanels");
  const mapPos = source.indexOf("<WatchlistMapDecisionPanel");
  assert.ok(comparePos >= 0 && mapPos >= 0 && comparePos < mapPos);
});

test("W7: watchlist mantiene bloqueo de copy EN", () => {
  const source = fs.readFileSync(WATCHLIST_PAGE, "utf8");
  for (const snippet of FORBIDDEN_EN_COPY) {
    assert.equal(source.includes(snippet), false, `watchlist page still contains forbidden EN copy: ${snippet}`);
  }
});