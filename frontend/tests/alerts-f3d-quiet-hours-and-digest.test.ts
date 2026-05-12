import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const ALERTS_PAGE = path.join(process.cwd(), "src", "app", "(private)", "alerts", "page.tsx");
const ALERTS_I18N = path.join(process.cwd(), "src", "i18n", "domains", "alerts.ts");

test("alerts page renders quiet hours controls and persists payload", () => {
  const source = fs.readFileSync(ALERTS_PAGE, "utf8");
  assert.match(source, /alerts\.form\.quietHoursTitle/);
  assert.match(source, /alerts\.form\.quietHoursEnabled/);
  assert.match(source, /quiet_hours_enabled: quietHoursEnabled/);
  assert.match(source, /quiet_hours_start: quietHoursStart/);
  assert.match(source, /quiet_hours_end: quietHoursEnd/);
});

test("alerts page renders grouped and quiet hours pending event copies", () => {
  const source = fs.readFileSync(ALERTS_PAGE, "utf8");
  assert.match(source, /alerts\.history\.groupedLabel/);
  assert.match(source, /alerts\.history\.digestSummary/);
  assert.match(source, /alerts\.history\.quietHoursPending/);
});

test("spanish alerts copy includes grouped and quiet hours messaging", () => {
  const source = fs.readFileSync(ALERTS_I18N, "utf8");
  assert.match(source, /groupedLabel: "Agrupada"/);
  assert.match(source, /quietHoursPending: "Pendiente hasta que terminen tus horas tranquilas"/);
});
