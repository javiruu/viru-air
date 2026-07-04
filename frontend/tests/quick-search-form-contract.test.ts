import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const QUICK_SEARCH_VIEW = path.join(
  process.cwd(),
  "src",
  "modules",
  "quick-search",
  "QuickSearchView.tsx",
);

test("quick-search clears round-trip-specific state when round trip is turned off", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");

  assert.match(source, /setReturnDate\(""\);/);
  assert.match(source, /setApplyFlexReturn\(false\);/);
  assert.match(source, /setReturnDateTouched\(false\);/);
});

test("quick-search clears invalid return date after outbound moves forward", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");

  assert.match(source, /if \(isReturn && returnDate && value && returnDate < value\)/);
  assert.match(source, /setReturnDate\(""\);/);
  assert.match(source, /returnResetAfterOutboundChange/);
});

test("quick-search passenger stepper exposes adult-specific accessibility copy", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");

  assert.match(source, /passengersStepperDecrease/);
  assert.match(source, /passengersStepperIncrease/);
  assert.match(source, /passengersStepperAria/);
});

test("quick-search does not let preference defaults overwrite a restored resume snapshot", () => {
  const source = fs.readFileSync(QUICK_SEARCH_VIEW, "utf8");

  assert.match(source, /const hasRestoredResumeSnapshot = useRef\(false\);/);
  assert.match(source, /hasRestoredResumeSnapshot\.current = true;/);
  assert.match(source, /if \(hasRestoredResumeSnapshot\.current\) \{/);
  assert.match(source, /setPrefBadge\(true\);/);
});
