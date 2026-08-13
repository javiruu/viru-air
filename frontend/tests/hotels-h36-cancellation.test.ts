import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

import { areaResolve, getTrackedOfferHistoryV2, HotelsRequestError, searchHotels } from "@/modules/hotels/api";
import { apiFetchWithStatus } from "@/modules/shared/api";

const SEARCH_HOOK = path.join(process.cwd(), "src", "modules", "hotels", "hooks", "useHotelSearch.ts");
const DETAIL_HOOK = path.join(process.cwd(), "src", "modules", "hotels", "hooks", "useHotelDetail.ts");
const SNAPSHOTS_COMPONENT = path.join(process.cwd(), "src", "modules", "hotels", "components", "HotelTrackedOfferSnapshots.tsx");
const HOTELS_I18N = path.join(process.cwd(), "src", "i18n", "domains", "hotels.ts");
const SHARED_API = path.join(process.cwd(), "src", "modules", "shared", "api.ts");

function abortableFetch(signalRef: { current: AbortSignal | null }) {
  return async (_input: RequestInfo | URL, init?: RequestInit) => {
    signalRef.current = init?.signal ?? null;
    return new Promise<Response>((_resolve, reject) => {
      if (init?.signal?.aborted) {
        reject(new DOMException("aborted", "AbortError"));
        return;
      }
      init?.signal?.addEventListener("abort", () => {
        reject(new DOMException("aborted", "AbortError"));
      }, { once: true });
    });
  };
}

test("H36: hotel API propagates caller AbortSignal and normalizes cancellation", async () => {
  const originalFetch = globalThis.fetch;
  const signalRef: { current: AbortSignal | null } = { current: null };
  globalThis.fetch = abortableFetch(signalRef);
  const controller = new AbortController();

  try {
    const request = searchHotels({ q: "Madrid", limit: 30 }, controller.signal);
    controller.abort();
    await assert.rejects(request, (error: unknown) => {
      assert.ok(error instanceof HotelsRequestError);
      assert.equal(error.status, 0);
      return true;
    });
    assert.equal(signalRef.current, controller.signal);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("H36: caller abort remains distinguishable when timeout composition is enabled", async () => {
  const originalFetch = globalThis.fetch;
  let receivedSignal: AbortSignal | null = null;
  globalThis.fetch = async (_input, init) => {
    receivedSignal = init?.signal ?? null;
    return new Promise<Response>((_resolve, reject) => {
      init?.signal?.addEventListener("abort", () => {
        reject(new DOMException("aborted", "AbortError"));
      }, { once: true });
    });
  };
  const caller = new AbortController();

  try {
    const request = apiFetchWithStatus("/hotels/search", { signal: caller.signal }, { timeoutMs: 1000 });
    caller.abort();
    const result = await request;
    assert.equal(result.ok, false);
    if (result.ok) throw new Error("expected_abort");
    assert.equal(result.error.code, "ABORTED");
    assert.notEqual(receivedSignal, caller.signal);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("H36: tracked snapshot history accepts a caller signal", async () => {
  const originalFetch = globalThis.fetch;
  const signalRef: { current: AbortSignal | null } = { current: null };
  globalThis.fetch = abortableFetch(signalRef);
  const controller = new AbortController();

  try {
    const request = getTrackedOfferHistoryV2("offer-1", controller.signal);
    controller.abort();
    await assert.rejects(request, (error: unknown) => error instanceof HotelsRequestError && error.status === 0);
    assert.equal(signalRef.current, controller.signal);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("H36: snapshot network failures remain distinguishable from cancellation", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    throw new TypeError("network down");
  };

  try {
    await assert.rejects(getTrackedOfferHistoryV2("offer-1"), (error: unknown) => {
      assert.ok(error instanceof HotelsRequestError);
      assert.equal(error.status, 0);
      assert.equal(error.message.length > 0, true);
      return true;
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("H36: area resolve accepts a caller signal", async () => {
  const originalFetch = globalThis.fetch;
  const signalRef: { current: AbortSignal | null } = { current: null };
  globalThis.fetch = abortableFetch(signalRef);
  const controller = new AbortController();

  try {
    const request = areaResolve("Madrid", controller.signal);
    controller.abort();
    await assert.rejects(request, (error: unknown) => error instanceof HotelsRequestError && error.status === 0);
    assert.equal(signalRef.current, controller.signal);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("H36: hotel hooks cancel obsolete search, resolve, and detail work", () => {
  const searchHook = fs.readFileSync(SEARCH_HOOK, "utf8");
  const detailHook = fs.readFileSync(DETAIL_HOOK, "utf8");
  const snapshotsComponent = fs.readFileSync(SNAPSHOTS_COMPONENT, "utf8");
  const hotelsI18n = fs.readFileSync(HOTELS_I18N, "utf8");
  const sharedApi = fs.readFileSync(SHARED_API, "utf8");

  assert.match(searchHook, /searchAbortRef\.current\?\.abort\(\)/);
  assert.match(searchHook, /areaResolveAbortRef\.current\?\.abort\(\)/);
  assert.match(searchHook, /searchRequestIdRef\.current/);
  assert.match(searchHook, /request\.requestId !== searchRequestIdRef\.current/);
  assert.match(searchHook, /areaResolveRequestIdRef\.current/);
  assert.match(searchHook, /areaResolve\(requestedQuery, controller\.signal\)/);
  assert.match(searchHook, /handleSearchModeChange[\s\S]*?areaResolveAbortRef\.current\?\.abort\(\)/);
  assert.match(searchHook, /areaSearchV2\([\s\S]*?request\.controller\.signal/);
  assert.match(detailHook, /getHotelDetail\(selectedHotelId, controller\.signal, intentId \?\? undefined\)/);
  assert.match(detailHook, /getHotelRates\(selectedHotelId, undefined, controller\.signal, intentId \?\? undefined\)/);
  assert.match(detailHook, /getHotelParity\(selectedHotelId, controller\.signal, intentId \?\? undefined\)/);
  assert.match(detailHook, /controller\.abort\(\)/);
  assert.match(detailHook, /setLoadingRates\(false\);/);
  assert.match(snapshotsComponent, /getTrackedOfferHistoryV2\(offerId, controller\.signal\)/);
  assert.match(snapshotsComponent, /snapshotsLoadError/);
  assert.match(snapshotsComponent, /setHasError\(true\)/);
  assert.match(snapshotsComponent, /controller\.signal\.aborted/);
  assert.match(snapshotsComponent, /controller\.abort\(\)/);
  assert.match(hotelsI18n, /snapshotsLoadError: "No se pudo cargar el historial/);
  assert.match(hotelsI18n, /snapshotsLoadError: "Could not load the history/);
  assert.match(sharedApi, /signal: timeoutController\?\.signal \?\? callerSignal/);
});
