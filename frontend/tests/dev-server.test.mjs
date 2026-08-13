import assert from "node:assert/strict";
import { once } from "node:events";
import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";

import {
  buildNextDevArguments,
  discoverStaticRoutes,
  resolveDevDistDir,
  isRouteWarmupEnabled,
  resolveDevPort,
  warmStaticRoutes,
} from "../scripts/dev-server.mjs";

async function createPage(appDirectory, relativePagePath) {
  const pagePath = path.join(appDirectory, relativePagePath);
  await mkdir(path.dirname(pagePath), { recursive: true });
  await writeFile(pagePath, "export default function Page() { return null; }\n");
}

test("discovers every static App Router page in Viru priority order", async () => {
  const fixtureRoot = await mkdtemp(path.join(tmpdir(), "viru-routes-"));
  const appDirectory = path.join(fixtureRoot, "app");

  try {
    await Promise.all([
      createPage(appDirectory, "(public)/page.tsx"),
      createPage(appDirectory, "(marketing)/page.tsx"),
      createPage(appDirectory, "(private)/watchlist/page.tsx"),
      createPage(appDirectory, "(private)/quick-search/page.tsx"),
      createPage(appDirectory, "(private)/dashboard/page.tsx"),
      createPage(appDirectory, "(private)/admin/page.tsx"),
      createPage(appDirectory, "(private)/preferencias/region/page.tsx"),
      createPage(appDirectory, "(private)/watchlist/[watchId]/page.tsx"),
      createPage(appDirectory, "(private)/@modal/login/page.tsx"),
    ]);
    await writeFile(path.join(appDirectory, "route.ts"), "export const GET = () => null;\n");

    const routes = await discoverStaticRoutes(appDirectory);

    assert.deepEqual(routes, [
      "/",
      "/dashboard",
      "/quick-search",
      "/watchlist",
      "/admin",
      "/preferencias/region",
    ]);
  } finally {
    await rm(fixtureRoot, { recursive: true, force: true });
  }
});

test("uses an isolated development dist directory for non-default ports", () => {
  assert.equal(resolveDevDistDir({}, 3000), ".next");
  assert.equal(resolveDevDistDir({}, 3100), ".next-dev-3100");
  assert.equal(resolveDevDistDir({ NEXT_DIST_DIR: "custom-next" }, 3100), "custom-next");
});

test("resolves the effective Next development port from supported CLI forms", () => {
  assert.equal(resolveDevPort([]), 3000);
  assert.equal(resolveDevPort(["--port", "4100"]), 4100);
  assert.equal(resolveDevPort(["-p", "4101"]), 4101);
  assert.equal(resolveDevPort(["--port=4102"]), 4102);
  assert.equal(resolveDevPort(["-p", "4101", "--port", "4103"]), 4103);
});

test("forwards one effective port to Next and preserves unrelated arguments", () => {
  assert.deepEqual(
    buildNextDevArguments(["--hostname", "0.0.0.0", "-p", "4101", "--port=4102"]),
    ["dev", "--turbopack", "-p", "4102", "--hostname", "0.0.0.0"],
  );
});

test("allows route warmup to be disabled explicitly", () => {
  assert.equal(isRouteWarmupEnabled({}), true);
  assert.equal(isRouteWarmupEnabled({ VIRU_ROUTE_WARMUP: "1" }), true);
  assert.equal(isRouteWarmupEnabled({ VIRU_ROUTE_WARMUP: "true" }), true);
  assert.equal(isRouteWarmupEnabled({ VIRU_ROUTE_WARMUP: "0" }), false);
  assert.equal(isRouteWarmupEnabled({ VIRU_ROUTE_WARMUP: "false" }), false);
});

test("warms routes sequentially and isolates a failing route", async () => {
  const requestOrder = [];
  let activeRequests = 0;
  let maximumActiveRequests = 0;
  const server = createServer((request, response) => {
    activeRequests += 1;
    maximumActiveRequests = Math.max(maximumActiveRequests, activeRequests);
    requestOrder.push(request.url);
    setTimeout(() => {
      response.statusCode = request.url === "/broken" ? 500 : 200;
      response.end("compiled");
      activeRequests -= 1;
    }, 10);
  });
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const address = server.address();
  assert.notEqual(address, null);
  assert.equal(typeof address, "object");

  try {
    const summary = await warmStaticRoutes({
      origin: `http://127.0.0.1:${address.port}`,
      routes: ["/dashboard", "/broken", "/watchlist"],
      pauseMs: 0,
      requestTimeoutMs: 1_000,
      log: () => {},
    });

    assert.deepEqual(requestOrder, ["/dashboard", "/broken", "/watchlist"]);
    assert.equal(maximumActiveRequests, 1);
    assert.deepEqual(summary, {
      total: 3,
      succeeded: 2,
      failed: ["/broken"],
    });
  } finally {
    server.close();
    await once(server, "close");
  }
});

test("cancels an active warmup request when the development server exits", async () => {
  const server = createServer(() => {});
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const address = server.address();
  assert.notEqual(address, null);
  assert.equal(typeof address, "object");
  const abortController = new AbortController();
  const startedAt = Date.now();

  try {
    const warmup = warmStaticRoutes({
      origin: `http://127.0.0.1:${address.port}`,
      routes: ["/never-responds"],
      pauseMs: 0,
      requestTimeoutMs: 10_000,
      log: () => {},
      signal: abortController.signal,
    });
    setTimeout(() => abortController.abort(), 25);

    const summary = await warmup;

    assert.ok(Date.now() - startedAt < 1_000);
    assert.deepEqual(summary, {
      total: 1,
      succeeded: 0,
      failed: [],
    });
  } finally {
    server.closeAllConnections();
    server.close();
    await once(server, "close");
  }
});
