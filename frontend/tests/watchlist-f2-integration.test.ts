import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const DETAIL_LOADER_FILE = path.join(
  process.cwd(),
  "src",
  "modules",
  "watchlist",
  "useWatchlistDetail.ts",
);
const MUTATIONS_FILE = path.join(
  process.cwd(),
  "src",
  "modules",
  "watchlist",
  "useWatchlistMutations.ts",
);
const DETAIL_PANEL_FILE = path.join(
  process.cwd(),
  "src",
  "modules",
  "watchlist",
  "components",
  "WatchDetailPanel.tsx",
);

test("watchlist selected route loads detail and prices summary endpoints", () => {
  const source = fs.readFileSync(DETAIL_LOADER_FILE, "utf8");
  assert.match(source, /getWatchDetailApiV1WatchlistWatchIdGet\(selectedWatchId\)/);
  assert.match(
    source,
    /summaryApiV1PricesSummaryGet\(\{ watch_id: selectedWatchId \}\)/,
  );
  assert.match(source, /normalizeWatchDetailApiResponse\(detail/);
});

test("watchlist bulk refresh uses refresh-bulk endpoint", () => {
  const source = fs.readFileSync(MUTATIONS_FILE, "utf8");
  assert.match(source, /refreshWatchBulkApiV1WatchlistRefreshBulkPost/);
  assert.doesNotMatch(
    source,
    /Promise\.allSettled\(\s*targets\.map\(\(item\) => \(?\w*\)?\s*`\/watchlist\/\$\{item\.id\}\/refresh-now`/,
  );
});

test("watchlist bulk status uses status-bulk endpoint with a single request", () => {
  const source = fs.readFileSync(MUTATIONS_FILE, "utf8");
  assert.match(source, /updateWatchStatusBulkApiV1WatchlistStatusBulkPost/);
  assert.doesNotMatch(
    source,
    /Promise\.allSettled\(\s*ids\.map\(\(id\) =>\s*\(?\w*\)?\s*`\/watchlist\/\$\{id\}`/,
  );
});

test("watchlist bulk delete uses delete-bulk endpoint with a single request", () => {
  const source = fs.readFileSync(MUTATIONS_FILE, "utf8");
  assert.match(source, /deleteWatchBulkApiV1WatchlistDeleteBulkPost/);
  assert.doesNotMatch(
    source,
    /Promise\.allSettled\(\s*ids\.map\(\(id\) =>\s*\(?\w*\)?\s*`\/watchlist\/\$\{id\}`/,
  );
});

test("watch detail panel contains required empty state keys", () => {
  const source = fs.readFileSync(DETAIL_PANEL_FILE, "utf8");
  assert.match(source, /watchlist\.detail\.empty/);
  assert.match(source, /watchlist\.summary\.empty/);
});

test("watch detail uses only detail that belongs to the selected watch", () => {
  const panelSource = fs.readFileSync(DETAIL_PANEL_FILE, "utf8");

  assert.match(panelSource, /resolveCurrentWatchDetail\(selectedWatch, detail\)/);
  assert.match(panelSource, /selectedWatch\?\.fare_profile \?\?\s*currentDetail\?\.fare_profile/);
});
