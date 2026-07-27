import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

test("watchlist delay prediction stays inside the operational panel and explains its evidence", () => {
  // Given: the existing Watchlist operational surface.
  const livePanel = fs.readFileSync(
    path.join(process.cwd(), "src", "modules", "watchlist", "components", "WatchLiveFlightPanel.tsx"),
    "utf8",
  );
  const predictionPanel = fs.readFileSync(
    path.join(process.cwd(), "src", "modules", "watchlist", "components", "WatchDelayPrediction.tsx"),
    "utf8",
  );

  // When: the incoming-aircraft prediction is rendered.
  // Then: it is nested in live tracking and exposes model, confidence, and evidence copy.
  assert.match(livePanel, /<WatchDelayPrediction/);
  assert.match(predictionPanel, /watchlist\.live\.prediction\.model/);
  assert.match(predictionPanel, /watchlist\.live\.prediction\.confidence/);
  assert.match(predictionPanel, /prediction\.factor_codes/);
  assert.match(predictionPanel, /prediction\.incoming_aircraft/);
  assert.doesNotMatch(predictionPanel, /Math\.random|fetch\(/);
});
