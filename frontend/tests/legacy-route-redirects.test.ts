import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

import { resolveBridgeRoute } from "../src/modules/shared/routeBridges";

const HISTORY_PAGE = path.join(process.cwd(), "src", "app", "(private)", "history", "page.tsx");
const PREFERENCES_PAGE = path.join(process.cwd(), "src", "app", "(private)", "preferences", "page.tsx");
const SUGGESTIONS_PAGE = path.join(process.cwd(), "src", "app", "(private)", "suggestions", "page.tsx");

test("legacy bridges resolve to canonical routes", () => {
  assert.equal(resolveBridgeRoute("/history"), "/watchlist");
  assert.equal(resolveBridgeRoute("/preferences"), "/preferencias");
  assert.equal(resolveBridgeRoute("/suggestions"), "/soporte/feedback?type=idea");
});

test("history and preferences routes use server redirect pages", () => {
  const historySource = fs.readFileSync(HISTORY_PAGE, "utf8");
  const preferencesSource = fs.readFileSync(PREFERENCES_PAGE, "utf8");

  assert.match(historySource, /redirect\("\/watchlist"\)/);
  assert.match(preferencesSource, /redirect\("\/preferencias"\)/);
  assert.doesNotMatch(historySource, /useEffect|router\.replace/);
  assert.doesNotMatch(preferencesSource, /useEffect|router\.replace/);
  assert.doesNotMatch(historySource, /Redirecting|History is now part of/);
  assert.doesNotMatch(preferencesSource, /Redirecting to the unified panel|History is now part of Flight Watchlist/);
});

test("suggestions legacy route redirects to feedback idea flow", () => {
  const source = fs.readFileSync(SUGGESTIONS_PAGE, "utf8");
  assert.match(source, /redirect\("\/soporte\/feedback\?type=idea"\)/);
});
