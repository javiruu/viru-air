import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const SUMMARY_FILE = path.join(process.cwd(), "src", "modules", "watchlist", "summary.ts");
const SMART_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "SmartWatchListPanel.tsx");
const DETAIL_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "WatchDetailPanel.tsx");
const WATCHLIST_I18N = path.join(process.cwd(), "src", "i18n", "domains", "watchlist.ts");
const WATCHLIST_PAGE = path.join(process.cwd(), "src", "app", "(private)", "watchlist", "page.tsx");

const FORBIDDEN_EN_COPY = ["Back", "Flight Watchlist", "Add flight", "Quick start", "Last update", "Min", "Max"];

test("W6: helper de frescura devuelve tiempo accionable en reciente y antiguo", () => {
  const source = fs.readFileSync(SUMMARY_FILE, "utf8");
  assert.match(source, /function getFreshnessPresentation/);
  assert.match(source, /watchlist\.freshness\.updatedAgo/);
  assert.match(source, /watchlist\.freshness\.lastUpdatedAgo/);
  assert.match(source, /if \(diffHours > 24\)/);
});

test("W6: helper de frescura cubre caso sin timestamp ni snapshot", () => {
  const source = fs.readFileSync(SUMMARY_FILE, "utf8");
  assert.match(source, /watchlist\.freshness\.noDataLabel/);
  assert.match(source, /watchlist\.freshness\.noDataDetail/);
  assert.match(source, /Sin datos todavÃ­a|watchlist\.freshness\.noDataLabel/);
});

test("W6: lista muestra frescura accionable y no deja En observacion aislado", () => {
  const source = fs.readFileSync(SMART_PANEL, "utf8");
  assert.match(source, /getFreshnessPresentation/);
  assert.match(source, /freshness\.fullText/);
});

test("W6: detalle usa una sola linea de frescura y evita duplicidad absurda", () => {
  const source = fs.readFileSync(DETAIL_PANEL, "utf8");
  assert.match(source, /getFreshnessPresentation/);
  assert.match(source, /watchlist\.detail\.freshness/);
  assert.match(source, /freshness\.fullText/);
  assert.doesNotMatch(source, /watchlist\.detail\.lastUpdateRelative/);
});

test("W6: i18n agrega copy de frescura accionable en ES", () => {
  const source = fs.readFileSync(WATCHLIST_I18N, "utf8");
  assert.match(source, /noDataLabel:\s*"/);
  assert.match(source, /noDataDetail:\s*"actualiza para crear el primer snapshot"/);
  assert.match(source, /needsReviewLabel:\s*"/);
  assert.match(source, /lastUpdatedAgo:\s*"hace \{time\}"/);
  assert.match(source, /updatedAgo:\s*"hace \{time\}"/);
  assert.match(source, /observingLabel:\s*"/);
});

test("W6: watchlist mantiene bloqueo de copy EN", () => {
  const source = fs.readFileSync(WATCHLIST_PAGE, "utf8");
  for (const snippet of FORBIDDEN_EN_COPY) {
    assert.equal(source.includes(snippet), false, `watchlist page still contains forbidden EN copy: ${snippet}`);
  }
});

