import assert from "node:assert/strict";
import { once } from "node:events";
import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";

import nextConfig from "../next.config.js";
import {
  buildNextDevArguments,
  discoverStaticRoutes,
  resolveDevDistDir,
  isRouteWarmupEnabled,
  resolveRouteWarmupProfile,
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

test("uses an isolated development dist directory for every port", () => {
  assert.equal(resolveDevDistDir({}, 3000), ".next-dev-3000");
  assert.equal(resolveDevDistDir({}, 3100), ".next-dev-3100");
  assert.equal(resolveDevDistDir({ NEXT_DIST_DIR: "custom-next" }, 3100), "custom-next");
});

test("allows the local origins used by the development server", () => {
  assert.deepEqual(nextConfig.allowedDevOrigins, ["localhost", "127.0.0.1"]);
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
    buildNextDevArguments(["--warmup=fast", "--hostname", "0.0.0.0", "-p", "4101", "--port=4102"]),
    ["dev", "--turbopack", "-p", "4102", "--hostname", "0.0.0.0"],
  );
});

test("warms routes slowly by default and honors explicit warmup profiles", () => {
  assert.deepEqual(resolveRouteWarmupProfile({}), {
    mode: "slow",
    initialDelayMs: 8_000,
    pauseMs: 1_500,
    batchSize: 2,
    batchPauseMs: 4_000,
  });
  assert.equal(isRouteWarmupEnabled({}), true);
  assert.equal(resolveRouteWarmupProfile({}, ["--warmup=fast"])?.mode, "fast");
  assert.equal(resolveRouteWarmupProfile({ VIRU_ROUTE_WARMUP: "fast" })?.mode, "fast");
  assert.equal(resolveRouteWarmupProfile({ VIRU_ROUTE_WARMUP: "0" }), null);
  assert.equal(resolveRouteWarmupProfile({ VIRU_ROUTE_WARMUP: "false" }, ["--warmup=fast"]), null);
  assert.equal(resolveRouteWarmupProfile({ VIRU_ROUTE_WARMUP: "unknown" }), null);
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

test("paces warmup routes with a longer pause after each batch", async () => {
  const pauses = [];
  const server = createServer((_request, response) => {
    response.statusCode = 200;
    response.end("compiled");
  });
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const address = server.address();
  assert.notEqual(address, null);
  assert.equal(typeof address, "object");

  try {
    const summary = await warmStaticRoutes({
      origin: `http://127.0.0.1:${address.port}`,
      routes: ["/dashboard", "/quick-search", "/watchlist"],
      pauseMs: 10,
      batchSize: 2,
      batchPauseMs: 25,
      delayFn: async (milliseconds) => pauses.push(milliseconds),
      log: () => {},
    });

    assert.deepEqual(summary, { total: 3, succeeded: 3, failed: [] });
    assert.deepEqual(pauses, [10, 25]);
  } finally {
    server.close();
    await once(server, "close");
  }
});

test("waits between real warmup requests instead of sending a burst", async () => {
  const requestTimes = [];
  const server = createServer((_request, response) => {
    requestTimes.push(Date.now());
    response.statusCode = 200;
    response.end("compiled");
  });
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const address = server.address();
  assert.notEqual(address, null);
  assert.equal(typeof address, "object");

  try {
    await warmStaticRoutes({
      origin: `http://127.0.0.1:${address.port}`,
      routes: ["/dashboard", "/quick-search", "/watchlist"],
      pauseMs: 30,
      batchSize: 2,
      batchPauseMs: 60,
      log: () => {},
    });

    assert.equal(requestTimes.length, 3);
    assert.ok(requestTimes[1] - requestTimes[0] >= 25);
    assert.ok(requestTimes[2] - requestTimes[1] >= 55);
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
