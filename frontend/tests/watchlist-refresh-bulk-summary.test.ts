import assert from "node:assert/strict";
import test from "node:test";

import { summarizeRefreshBulkResult } from "../src/modules/watchlist/summary";

test("refresh bulk summary splits updated, cooldown, failed, degraded", () => {
  const summary = summarizeRefreshBulkResult({
    status: "ok",
    requested: 4,
    refreshed: ["a", "b"],
    failed: [
      { watch_id: "c", code: "refresh_cooldown_active" },
      { watch_id: "d", code: "provider_degraded" },
    ],
  });

  assert.deepEqual(summary, {
    updated: 2,
    skippedCooldown: 1,
    failed: 1,
    degradedOrStale: 1,
  });
});
