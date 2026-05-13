import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const DETAIL_PANEL_FILE = path.join(process.cwd(), "src", "modules", "watchlist", "components", "WatchDetailPanel.tsx");
const SUMMARY_FILE = path.join(process.cwd(), "src", "modules", "watchlist", "summary.ts");
const WATCHLIST_I18N = path.join(process.cwd(), "src", "i18n", "domains", "watchlist.ts");
const WATCHLIST_PAGE = path.join(process.cwd(), "src", "app", "(private)", "watchlist", "page.tsx");

const FORBIDDEN_EN_COPY = ["Back", "Flight Watchlist", "Add flight", "Quick start", "Last update", "Min", "Max"];

test("W5: helper de confianza clasifica snapshot_count segun reglas", () => {
  const source = fs.readFileSync(SUMMARY_FILE, "utf8");
  assert.match(source, /if \(snapshotCount <= 0\)/);
  assert.match(source, /level: "none"/);
  assert.match(source, /if \(snapshotCount <= 1\)/);
  assert.match(source, /level: "initial"/);
  assert.match(source, /if \(snapshotCount <= 3\)/);
  assert.match(source, /level: "limited"/);
  assert.match(source, /level: "sufficient"/);
});

test("W5: con 0 snapshots se mantiene empty state y no se duplica aviso", () => {
  const source = fs.readFileSync(DETAIL_PANEL_FILE, "utf8");
  assert.match(source, /watchlist\.summary\.empty/);
  assert.match(source, /confidence\.level !== "none"/);
});

test("W5: con 1 snapshot muestra histórico inicial y mantiene KPIs", () => {
  const source = fs.readFileSync(DETAIL_PANEL_FILE, "utf8");
  const i18nSource = fs.readFileSync(WATCHLIST_I18N, "utf8");

  assert.match(source, /t\(confidence\.titleKey\)/);
  assert.match(i18nSource, /initialTitle:\s*"Histórico inicial"/);
  assert.match(i18nSource, /initialMessage:\s*"Solo hay 1 captura\. Todavía no hay suficiente tendencia para decidir\."/);
  assert.match(source, /watchlist\.summary\.latest/);
  assert.match(source, /watchlist\.summary\.min/);
  assert.match(source, /watchlist\.summary\.max/);
  assert.match(source, /watchlist\.summary\.avg/);
  assert.match(source, /watchlist\.summary\.delta/);
  assert.match(source, /watchlist\.summary\.count/);
});

test("W5: con 2 o 3 snapshots muestra histórico limitado", () => {
  const i18nSource = fs.readFileSync(WATCHLIST_I18N, "utf8");
  assert.match(i18nSource, /limitedTitle:\s*"Histórico limitado"/);
  assert.match(i18nSource, /limitedMessage:\s*"Hay pocas capturas\. Interpreta la tendencia con cautela\."/);
});

test("W5: con 4 o más snapshots muestra histórico suficiente", () => {
  const i18nSource = fs.readFileSync(WATCHLIST_I18N, "utf8");
  assert.match(i18nSource, /sufficientTitle:\s*"Histórico suficiente"/);
  assert.match(i18nSource, /sufficientMessage:\s*"Ya hay varias capturas para comparar la evolución\."/);
});

test("W5: se mantiene formateo de KPIs y se bloquea copy EN en watchlist", () => {
  const source = fs.readFileSync(DETAIL_PANEL_FILE, "utf8");
  const pageSource = fs.readFileSync(WATCHLIST_PAGE, "utf8");

  assert.match(source, /formatCurrency\(summary\.latest_price, "EUR"\)/);
  assert.match(source, /formatCurrency\(summary\.min_price, "EUR"\)/);
  assert.match(source, /formatCurrency\(summary\.max_price, "EUR"\)/);
  assert.match(source, /formatCurrency\(summary\.avg_price, "EUR"\)/);
  assert.match(source, /formatPercent\(summary\.delta_pct\)/);

  for (const snippet of FORBIDDEN_EN_COPY) {
    assert.equal(pageSource.includes(snippet), false, `watchlist page still contains forbidden EN copy: ${snippet}`);
  }
});
