import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { Skeleton, SkeletonForm, SkeletonList, SkeletonOverlay, SkeletonPanel } from "../src/modules/shared/Skeleton";

test("Skeleton renders primitive variants with the shimmer class", () => {
  const html = renderToStaticMarkup(
    <div>
      <Skeleton variant="line" width="70%" />
      <Skeleton variant="pill" width={120} height={18} />
      <Skeleton variant="block" height={42} />
      <Skeleton variant="circle" width={32} height={32} />
      <Skeleton variant="card" />
    </div>,
  );

  assert.match(html, /vt-skeleton--line/);
  assert.match(html, /vt-skeleton--pill/);
  assert.match(html, /vt-skeleton--block/);
  assert.match(html, /vt-skeleton--circle/);
  assert.match(html, /vt-skeleton--card/);
});

test("Skeleton containers expose accessible loading semantics", () => {
  const html = renderToStaticMarkup(
    <div>
      <SkeletonPanel ariaLabel="loading panel" />
      <SkeletonForm ariaLabel="loading form" />
      <SkeletonList ariaLabel="loading list" rows={2} />
      <SkeletonOverlay ariaLabel="loading overlay" />
    </div>,
  );

  assert.match(html, /aria-label="loading panel"/);
  assert.match(html, /aria-label="loading form"/);
  assert.match(html, /aria-label="loading list"/);
  assert.match(html, /aria-label="loading overlay"/);
  assert.match(html, /aria-busy="true"/);
  assert.match(html, /loading-skeleton-overlay/);
});
