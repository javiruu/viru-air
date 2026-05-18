import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

import { resolveSelectedWatchId } from "../src/modules/watchlist/useWatchlistDataLoader";

const ACTIONS_FILE = path.join(process.cwd(), "src", "modules", "watchlist", "useWatchlistActions.ts");
const HISTORY_PANEL_FILE = path.join(process.cwd(), "src", "modules", "watchlist", "components", "HistoryIntegratedPanel.tsx");
const PRESENTATION_FILE = path.join(process.cwd(), "src", "modules", "watchlist", "presentation.ts");

test("F1A: resolveSelectedWatchId preserves user selection when still present", () => {
  const rows = [{ id: "A" }, { id: "B" }];
  assert.equal(resolveSelectedWatchId(rows, "B"), "B");
});

test("F1A: resolveSelectedWatchId falls back to first row when selected id is missing", () => {
  const rows = [{ id: "A" }, { id: "B" }];
  assert.equal(resolveSelectedWatchId(rows, "Z"), "A");
});

test("F1A: resolveSelectedWatchId returns empty string when there are no rows", () => {
  assert.equal(resolveSelectedWatchId([], "B"), "");
});

test("F1B: initial load error is not duplicated through generic message channel", () => {
  const source = fs.readFileSync(ACTIONS_FILE, "utf8");
  assert.doesNotMatch(source, /watchlist\.messages\.loadError/);
  assert.match(source, /load\(\)\s*\.catch\(\(\) => \{\}\);/);
});

test("F1C: calendar action stays visible but disabled when data is insufficient", () => {
  const source = fs.readFileSync(HISTORY_PANEL_FILE, "utf8");
  assert.match(source, /const canToggleCalendar = hasCalendarData && calendarHasUsefulData/);
  assert.match(source, /disabled=\{!canToggleCalendar\}/);
  assert.match(source, /watchlist\.history\.calendarUnavailableBody/);
});

test("F1D: deprecated freshnessLabel export was removed from watchlist presentation", () => {
  const source = fs.readFileSync(PRESENTATION_FILE, "utf8");
  assert.doesNotMatch(source, /export function freshnessLabel\(/);
  assert.doesNotMatch(source, /Reciente|En observación|Desactualizado/);
});
