import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const SIGNALS_PAGE = path.join(process.cwd(), "src", "app", "(private)", "notifications", "page.tsx");
const ALERTS_ALIAS_PAGE = path.join(process.cwd(), "src", "app", "(private)", "alerts", "page.tsx");
const DASHBOARD_PAGE = path.join(process.cwd(), "src", "app", "(private)", "dashboard", "page.tsx");
const SIGNALS_RULES = path.join(process.cwd(), "src", "modules", "signals", "AlertRulesWorkspace.tsx");

test("signals page owns both inbox and rules views", () => {
  const source = fs.readFileSync(SIGNALS_PAGE, "utf8");

  assert.match(source, /AlertRulesWorkspace/);
  assert.match(source, /searchParams\.get\("view"\) === "rules"/);
  assert.match(source, /requestedWatchId=\{searchParams\.get\("watch_id"\)\}/);
  assert.match(source, /SignalsSectionNav activeSection="inbox"/);
});

test("legacy alerts route redirects into signals rules without losing query parameters", () => {
  const source = fs.readFileSync(ALERTS_ALIAS_PAGE, "utf8");

  assert.match(source, /redirect\(`\/notifications\?\$\{nextSearchParams\.toString\(\)\}`\)/);
  assert.match(source, /nextSearchParams\.set\("view", "rules"\)/);
});

test("alert management lives in signals and exposes the shared section navigation", () => {
  const source = fs.readFileSync(SIGNALS_RULES, "utf8");

  assert.match(source, /SignalsSectionNav activeSection="rules"/);
  assert.match(source, /apiFetch<AlertRule\[\]>\(`\/alerts\/rules/);
  assert.match(source, /AlertRulesWorkspace\(\{ requestedWatchId \}/);
});

test("dashboard actions use the canonical signals rules view", () => {
  const source = fs.readFileSync(DASHBOARD_PAGE, "utf8");

  assert.doesNotMatch(source, /href="\/alerts"/);
  assert.match(source, /href="\/notifications\?view=rules"/);
});
