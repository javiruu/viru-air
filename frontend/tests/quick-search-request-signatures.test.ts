import assert from "node:assert/strict";
import test from "node:test";

import {
  buildQuickSearchCanonicalPayload,
  buildQuickSearchExpectedSignatures,
  buildQuickSearchQuerySignature,
  type QuickSearchQueryParams,
} from "../src/modules/quick-search/api/buildQuickSearchRequest";

function createParams(): QuickSearchQueryParams {
  return {
    origin_iata: "MAD",
    destination_iata: "DUB",
    travel_date: "2026-06-14",
    date: "2026-06-14",
    flex_days_before: 1,
    flex_days_after: 2,
    radius_km: 150,
    include_stops: false,
    include_nearby_origins: true,
    include_nearby_destinations: false,
    depart_after: "06:00",
    depart_before: "22:00",
    max_stops: 0,
    exclude_origins: [],
    exclude_destinations: [],
    strict_filters: true,
    soft_filters_weight: 0.6,
    page: 1,
    page_size: 10,
  };
}

test("buildQuickSearchQuerySignature degrades safely when Web Crypto is unavailable in the browser", async () => {
  const originalCrypto = globalThis.crypto;
  const originalWindow = (globalThis as typeof globalThis & { window?: Window }).window;
  Object.defineProperty(globalThis, "crypto", {
    configurable: true,
    value: { subtle: undefined },
  });
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: {},
  });

  try {
    const payload = buildQuickSearchCanonicalPayload(createParams());
    const signature = await buildQuickSearchQuerySignature({ payload, winningStep: "pass_1_exact" });
    const expected = await buildQuickSearchExpectedSignatures(payload);

    assert.equal(signature, null);
    assert.equal(expected, null);
  } finally {
    Object.defineProperty(globalThis, "crypto", {
      configurable: true,
      value: originalCrypto,
    });
    if (typeof originalWindow === "undefined") {
      // @ts-expect-error TS2790 — delete on non-optional property used to clean up test env
      delete (globalThis as typeof globalThis & { window?: Window }).window;
    } else {
      Object.defineProperty(globalThis, "window", {
        configurable: true,
        value: originalWindow,
      });
    }
  }
});
