import assert from "node:assert/strict";
import test from "node:test";

import { formatCurrency, formatPercent, formatRelativeTime } from "../src/modules/shared/format";
import { monthLabel } from "../src/modules/watchlist/dateUtils";
import { formatDateTime } from "../src/modules/watchlist/presentation";

test("F2: month label changes with locale", () => {
  const es = monthLabel("2026-04", "es-ES");
  const en = monthLabel("2026-04", "en-US");
  assert.notEqual(es, en);
});

test("F2: currency formatting changes with locale", () => {
  const es = formatCurrency(1234.56, "EUR", "es-ES");
  const en = formatCurrency(1234.56, "EUR", "en-US");
  assert.notEqual(es, en);
});

test("F2: percent formatting changes with locale", () => {
  const es = formatPercent(12.5, "es-ES");
  const en = formatPercent(12.5, "en-US");
  assert.notEqual(es, en);
});

test("F2: relative time uses active locale", () => {
  const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000).toISOString();
  const es = formatRelativeTime(oneHourAgo, "es-ES");
  const en = formatRelativeTime(oneHourAgo, "en-US");
  assert.notEqual(es, en);
});

test("F2: watchlist datetime formatter uses explicit locale", () => {
  const iso = "2026-04-15T10:30:00.000Z";
  const es = formatDateTime(iso, "es-ES");
  const en = formatDateTime(iso, "en-US");
  assert.notEqual(es, en);
});
