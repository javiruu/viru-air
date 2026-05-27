import assert from "node:assert/strict";
import test from "node:test";

import {
  clampViewBox,
  panViewBox,
  zoomViewBoxAtPoint,
} from "../src/modules/watchlist/useChartViewport";

const BASE = { x: 0, y: 0, width: 920, height: 420 };

test("zoomViewBoxAtPoint clamps to max zoom and keeps center anchored", () => {
  const center = { x: 460, y: 210 };
  const zoomed = zoomViewBoxAtPoint({
    viewBox: BASE,
    baseViewBox: BASE,
    maxZoom: 6,
    zoomFactor: 1 / 3,
    center,
  });

  assert.ok(Math.abs(zoomed.width - BASE.width / 3) < 1e-9);
  assert.ok(Math.abs(zoomed.height - BASE.height / 3) < 1e-9);
  assert.ok(Math.abs(zoomed.x + zoomed.width / 2 - center.x) < 1e-9);
  assert.ok(Math.abs(zoomed.y + zoomed.height / 2 - center.y) < 1e-9);

  const clamped = zoomViewBoxAtPoint({
    viewBox: zoomed,
    baseViewBox: BASE,
    maxZoom: 6,
    zoomFactor: 1 / 100,
    center,
  });
  assert.equal(clamped.width, BASE.width / 6);
  assert.equal(clamped.height, BASE.height / 6);
});

test("panViewBox clamps viewport to chart bounds", () => {
  const zoomed = zoomViewBoxAtPoint({
    viewBox: BASE,
    baseViewBox: BASE,
    maxZoom: 6,
    zoomFactor: 1 / 2,
    center: { x: 460, y: 210 },
  });

  const moved = panViewBox({
    viewBox: zoomed,
    baseViewBox: BASE,
    deltaX: 2000,
    deltaY: 2000,
  });

  assert.equal(moved.x, BASE.width - zoomed.width);
  assert.equal(moved.y, BASE.height - zoomed.height);
});

test("clampViewBox never allows oversized viewBox", () => {
  const clamped = clampViewBox(BASE, {
    x: -100,
    y: -40,
    width: BASE.width * 2,
    height: BASE.height * 2,
  });

  assert.deepEqual(clamped, BASE);
});
