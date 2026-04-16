import assert from "node:assert/strict";
import test from "node:test";

import {
  clampQuickSearchFlexDays,
  formatQuickSearchFlexSummary,
  getQuickSearchFlexPreset,
} from "../src/modules/quick-search/flexibility";

test("quick search flexibility maps symmetric presets and custom values", () => {
  assert.equal(getQuickSearchFlexPreset(0, 0), "exact");
  assert.equal(getQuickSearchFlexPreset(1, 1), "plus-1");
  assert.equal(getQuickSearchFlexPreset(2, 2), "plus-2");
  assert.equal(getQuickSearchFlexPreset(3, 3), "plus-3");
  assert.equal(getQuickSearchFlexPreset(2, 1), "custom");
});

test("quick search flexibility clamps stepper values into supported range", () => {
  assert.equal(clampQuickSearchFlexDays(-3), 0);
  assert.equal(clampQuickSearchFlexDays(4), 4);
  assert.equal(clampQuickSearchFlexDays(12), 7);
});

test("quick search flexibility formats human summary labels", () => {
  const labels = {
    exact: "Fecha exacta",
    plusOne: "±1 dia",
    plusTwo: "±2 dias",
    plusThree: "±3 dias",
    customTemplate: "Personalizado · -{before} / +{after} dias",
  };

  assert.equal(formatQuickSearchFlexSummary(0, 0, labels), "Fecha exacta");
  assert.equal(formatQuickSearchFlexSummary(2, 2, labels), "±2 dias");
  assert.equal(formatQuickSearchFlexSummary(2, 1, labels), "Personalizado · -2 / +1 dias");
});
