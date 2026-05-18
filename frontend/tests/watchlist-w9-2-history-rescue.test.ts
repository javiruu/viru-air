import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const SUMMARY = path.join(process.cwd(), "src", "modules", "watchlist", "summary.ts");
const FORMAT = path.join(process.cwd(), "src", "modules", "shared", "format.ts");
const HISTORY_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "HistoryIntegratedPanel.tsx");
const DERIVED = path.join(process.cwd(), "src", "modules", "watchlist", "useWatchlistDerived.ts");
const PAGE = path.join(process.cwd(), "src", "app", "(private)", "watchlist", "page.tsx");
const I18N = path.join(process.cwd(), "src", "i18n", "domains", "watchlist.ts");

const FORBIDDEN_EN_COPY = ["Back", "Flight Watchlist", "Add flight", "Quick start", "Last update", "Min", "Max"];

test("W9.2: frescura no genera 'hace hace'", () => {
  const summary = fs.readFileSync(SUMMARY, "utf8");
  const format = fs.readFileSync(FORMAT, "utf8");
  const i18n = fs.readFileSync(I18N, "utf8");

  assert.match(format, /new Intl\.RelativeTimeFormat/);
  assert.match(summary, /watchlist\.freshness\.updatedAgo/);
  assert.match(summary, /watchlist\.freshness\.lastUpdatedAgo/);
  assert.match(i18n, /lastUpdatedAgo:\s*"\{time\}"/);
  assert.match(i18n, /updatedAgo:\s*"\{time\}"/);
});

test("W9.2: comparativa usa copy ES y bloquea copy EN", () => {
  const i18n = fs.readFileSync(I18N, "utf8");
  assert.match(i18n, /subtitle:\s*"Compara hasta 4 rutas"/);
  assert.match(i18n, /emptySelectionMessage:\s*"Selecciona 2–4 rutas para comparar"/);
  assert.match(i18n, /oneSelectionMessage:\s*"Elige otra ruta para comparar"/);
  assert.match(i18n, /maxSelectionMessage:\s*"Puedes comparar hasta 4 rutas\."/);
});

test("W9.2: elimina duplicidad 'Rango temporal RANGO' en histórico", () => {
  const source = fs.readFileSync(HISTORY_PANEL, "utf8");
  assert.match(source, /watchlist\.history\.rangeTitle/);
  assert.match(source, /aria-label=\{t\("watchlist\.history\.rangeLabel"\)\}/);
  assert.doesNotMatch(source, /history-range-label/);
  assert.doesNotMatch(source, /Rango temporal RANGO|Rango RANGO/);
});

test("W9.2: histórico integrado mantiene ruta con separador correcto y gráfico principal", () => {
  const source = fs.readFileSync(HISTORY_PANEL, "utf8");
  const page = fs.readFileSync(PAGE, "utf8");
  assert.match(source, /selectedWatch\.origin_iata} → \$\{selectedWatch\.destination_iata/);
  assert.match(source, /viewMode === "chart"/);
  assert.match(page, /<HistoryIntegratedPanel/);
});

test("W9.2: calendario toma mes coherente del filtro activo y no de otra ruta", () => {
  const source = fs.readFileSync(DERIVED, "utf8");
  assert.match(source, /if \(selectedDates\.length > 0\) return toIsoMonth\(selectedDates\[0\]\)/);
  assert.match(source, /const latestRow = filteredRows\[filteredRows\.length - 1\]/);
  assert.match(source, /return filteredRows\.reduce/);
  assert.doesNotMatch(source, /const source = filteredRows\.length > 0 \? filteredRows : historyRows/);
});

test("W9.2: si calendario no aporta, usa estado compacto y evita grid vacía dominante", () => {
  const source = fs.readFileSync(HISTORY_PANEL, "utf8");
  const i18n = fs.readFileSync(I18N, "utf8");
  assert.match(source, /calendarHasUsefulData/);
  assert.match(source, /history-compact-note--calendar/);
  assert.match(i18n, /Calendario no disponible para este rango\./);
  assert.match(i18n, /Usa el gráfico para revisar las capturas disponibles\./);
});

test("W9.2: copy EN bloqueado en watchlist", () => {
  const source = fs.readFileSync(PAGE, "utf8");
  for (const snippet of FORBIDDEN_EN_COPY) {
    assert.equal(source.includes(snippet), false, `watchlist page still contains forbidden EN copy: ${snippet}`);
  }
});
