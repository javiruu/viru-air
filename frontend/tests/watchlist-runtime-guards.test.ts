import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const DETAIL_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "WatchDetailPanel.tsx");
const MAP_COMPONENT = path.join(process.cwd(), "src", "components", "ui", "map.tsx");

test("watchlist detail omits empty snapshot metadata while preserving valid detail copy", () => {
  const source = fs.readFileSync(DETAIL_PANEL, "utf8");

  assert.doesNotMatch(source, /watchlist\.freshness\.noDataLabel/);
  assert.doesNotMatch(source, /watchlist\.freshness\.noDataDetail/);
  assert.doesNotMatch(source, /watchlist\.noDataLabel/);
  assert.doesNotMatch(source, /watchlist\.noDataDetail/);
  assert.match(source, /watchlist\.detail\.freshnessLabel/);
});

test("map runtime waits for style readiness before exposing controls and viewport actions", () => {
  const source = fs.readFileSync(MAP_COMPONENT, "utf8");

  assert.match(source, /function runWhenMapStyleReady\(map: MapLibreMap, action: \(\) => void\)/);
  assert.match(source, /runWhenMapStyleReady\(map, \(\) => \{\s*setReadyMap\(map\);/);
  assert.match(source, /runWhenMapStyleReady\(map, \(\) => \{\s*map\.fitBounds\(bounds, options\);/);
  assert.match(source, /runWhenMapStyleReady\(map, \(\) => \{\s*map\.easeTo\(options\);/);
});
