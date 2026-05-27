import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const WATCHLIST_PAGE = path.join(process.cwd(), "src", "app", "(private)", "watchlist", "page.tsx");
const HISTORY_PANEL = path.join(process.cwd(), "src", "modules", "watchlist", "components", "HistoryIntegratedPanel.tsx");
const CONTROLLER = path.join(process.cwd(), "src", "modules", "watchlist", "useWatchlistController.ts");

test("watchlist page wires chart viewport props and handlers into history panel", () => {
  const source = fs.readFileSync(WATCHLIST_PAGE, "utf8");
  assert.match(source, /chartViewBox=\{viewport\.viewBox\}/);
  assert.match(source, /chartIsZoomed=\{viewport\.isZoomed\}/);
  assert.match(source, /chartIsDragging=\{viewport\.isDragging\}/);
  assert.match(source, /onChartWheel=\{viewport\.onWheel\}/);
  assert.match(source, /onChartPointerDown=\{viewport\.onPointerDown\}/);
  assert.match(source, /onChartPointerMove=\{viewport\.onPointerMove\}/);
  assert.match(source, /onChartPointerUp=\{viewport\.onPointerUp\}/);
  assert.match(source, /onChartPointerCancel=\{viewport\.onPointerCancel\}/);
  assert.match(source, /onChartPointerLeave=\{viewport\.onPointerLeave\}/);
  assert.match(source, /onResetChartZoom=\{viewport\.resetZoom\}/);
});

test("history panel exposes zoom reset CTA and pointer plus wheel interaction wiring", () => {
  const source = fs.readFileSync(HISTORY_PANEL, "utf8");
  assert.match(source, /watchlist\.history\.resetZoom/);
  assert.match(source, /addEventListener\("wheel", handleWheel, \{ passive: false \}\)/);
  assert.match(source, /onChartWheel\(event\)/);
  assert.match(source, /onPointerDown=\{onChartPointerDown\}/);
  assert.match(source, /onPointerMove=\{onChartPointerMove\}/);
  assert.match(source, /onPointerUp=\{onChartPointerUp\}/);
  assert.match(source, /onPointerCancel=\{onChartPointerCancel\}/);
  assert.match(source, /onPointerLeave=\{\(event\) => \{/);
});

test("controller composes viewport hook with hover coordinate resolver", () => {
  const source = fs.readFileSync(CONTROLLER, "utf8");
  assert.match(source, /useChartViewport/);
  assert.match(source, /resetKey:/);
  assert.match(source, /resolveChartCoordinates: viewport\.resolveChartCoordinates/);
});
