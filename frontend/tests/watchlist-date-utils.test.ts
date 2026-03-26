import assert from "node:assert/strict";
import test from "node:test";

import { monthDays, monthLabel, shiftMonth, toIsoMonth } from "../src/modules/watchlist/dateUtils";

test("toIsoMonth extracts YYYY-MM", () => {
  assert.equal(toIsoMonth("2026-08-17"), "2026-08");
});

test("shiftMonth moves month with year rollover", () => {
  assert.equal(shiftMonth("2026-01", -1), "2025-12");
  assert.equal(shiftMonth("2026-12", 1), "2027-01");
});

test("monthDays pads to full weeks", () => {
  const days = monthDays("2026-02");
  assert.ok(days.length % 7 === 0);
  assert.ok(days.includes("2026-02-01"));
  assert.ok(days.includes("2026-02-28"));
});

test("monthLabel returns localized label", () => {
  assert.match(monthLabel("2026-02"), /2026/);
});
