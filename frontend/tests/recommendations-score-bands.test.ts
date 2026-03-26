import assert from "node:assert/strict";
import test from "node:test";

import { getScoreBand } from "../src/modules/recommendations/scoreBands";

test("getScoreBand maps score ranges", () => {
  assert.equal(getScoreBand(75), "high");
  assert.equal(getScoreBand(55), "midHigh");
  assert.equal(getScoreBand(40), "midLow");
  assert.equal(getScoreBand(20), "low");
});
