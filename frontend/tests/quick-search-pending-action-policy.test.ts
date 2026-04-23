import assert from "node:assert/strict";
import test from "node:test";

import { getPendingActionVisibility } from "../src/modules/quick-search/state/pendingActionPolicy";

test("pending action policy keeps a single actionable CTA in the filter console", () => {
  const hidden = getPendingActionVisibility(false);
  assert.deepEqual(hidden, {
    consoleAction: false,
    toolbarAction: false,
    contextRailNotice: false,
    contextRailAction: false,
  });

  const visible = getPendingActionVisibility(true);
  assert.deepEqual(visible, {
    consoleAction: true,
    toolbarAction: false,
    contextRailNotice: true,
    contextRailAction: false,
  });
});
