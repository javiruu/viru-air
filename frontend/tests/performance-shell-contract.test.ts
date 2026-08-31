import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const ROOT = path.resolve(__dirname, "..");
const read = (rel: string) => fs.readFileSync(path.join(ROOT, rel), "utf8");

test("MapLibre styles load only with the Watchlist route", () => {
  const rootLayout = read("src/app/layout.tsx");
  const watchlistLayout = read("src/app/(private)/watchlist/layout.tsx");

  assert.doesNotMatch(rootLayout, /maplibre-gl\/dist\/maplibre-gl\.css/);
  assert.match(watchlistLayout, /import "maplibre-gl\/dist\/maplibre-gl\.css"/);
});

test("persistent navigation disables eager viewport prefetching", () => {
  const privateNav = read("src/modules/shared/PrivateNav.tsx");
  const mobileNav = read("src/modules/shared/MobileBottomNav.tsx");

  assert.match(privateNav, /href=\{item\.href\}\s+prefetch=\{false\}/);
  assert.match(privateNav, /href="\/dashboard"\s+prefetch=\{false\}/);
  assert.match(mobileNav, /href=\{item\.href\}\s+prefetch=\{false\}/);
});

test("scrollbar proximity work is frame-limited and cleans up its scheduled frame", () => {
  const scrollbar = read("src/modules/shared/ScrollActivityScrollbar.tsx");

  assert.match(scrollbar, /window\.requestAnimationFrame/);
  assert.match(scrollbar, /if \(pointerFrameId !== null\) return/);
  assert.match(scrollbar, /window\.cancelAnimationFrame\(pointerFrameId\)/);
});
