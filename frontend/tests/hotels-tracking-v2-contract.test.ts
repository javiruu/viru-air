import assert from "node:assert/strict";
import test from "node:test";

import {
  createTrackedOfferV2,
  HotelsRequestError,
  parseTrackedOfferV2CreateResponse,
  parseTrackedOfferHistoryV2Response,
  parseTrackedOfferV2LifecycleResponse,
  parseTrackedOffersV2Response,
} from "@/modules/hotels/api";

const trackingFixture = {
  id: "tracking-1",
  hotel_id: "hotel-1",
  state: "active",
  state_version: 1,
  stay_context: {
    check_in: "2026-10-10",
    check_out: "2026-10-13",
    guests: 2,
    currency: "EUR",
  },
  latest_observation: {
    snapshot_id: "snapshot-1",
    legacy_collected_at: "2026-08-11T12:00:00Z",
    observed_at: "2026-08-11T11:59:00Z",
    provider: "mock",
    room_label: "Doble superior",
    meal_plan: "BB",
    cancellation_policy: "Reembolsable",
    availability_status: "available",
    conditions_completeness: "complete",
    canonical_stay_offer_id: "stay-offer-1",
    price: {
      amount: 240,
      currency: "EUR",
      basis: "total_stay",
      status: "observed",
      observed_at: null,
    },
    freshness: {
      state: "recent",
      observed_at: "2026-08-11T11:59:00Z",
      age_seconds: 60,
      expires_at: "2026-08-11T17:59:00Z",
      mixed: false,
      requires_revalidation: false,
      policy_version: "hotel-freshness-v1",
      provenance_kind: "provider_observed",
    },
  },
  capabilities: { pause: "supported" },
  warnings: [],
};

const listFixture = {
  data: [trackingFixture],
  meta: {
    contract_version: "hotels.tracking.v2",
    request_id: "hotels-tracking-v2-client-001",
    generated_at: "2026-08-11T12:00:00Z",
    result_state: "success",
    query: {},
    pagination: {
      mode: "none",
      returned: 1,
      total: 1,
      has_next: false,
      next_cursor: null,
      previous_cursor: null,
      sort: "created_at_desc",
    },
    freshness: {
      state: "recent",
      observed_at: "2026-08-11T12:00:00Z",
      age_seconds: 0,
      expires_at: null,
      mixed: false,
      requires_revalidation: false,
      policy_version: "hotel-freshness-v1",
      provenance_kind: "provider_observed",
    },
    capabilities: { tracking_creation: "supported" },
    warnings: [],
  },
};

const historyFixture = {
  tracked_offer_id: "tracking-1",
  series: {
    identity: {
      comparability_key: "offer-fingerprint-1",
      status: "comparable",
      check_in: "2026-10-10",
      check_out: "2026-10-13",
      guests: 2,
      currency: "EUR",
      provider_scope: "mock",
    },
    points: [{
      snapshot_id: "snapshot-1",
      observed_at: "2026-08-11T12:00:00Z",
      observation_time_source: "provider_observed",
      provider: "mock",
      availability_status: "available",
      conditions_completeness: "complete",
      canonical_stay_offer_id: "stay-offer-1",
      price_semantics: "total",
      price: trackingFixture.latest_observation.price,
      eligibility: "eligible",
      excluded_reason: null,
    }],
    gaps: [],
    segments: [],
  },
  aggregates: {
    sample_size_total: 1,
    sample_size_eligible: 1,
    min_price: 240,
    max_price: 240,
    median_price: null,
    average_price: null,
    currency: "EUR",
    price_semantics: "total",
    exclusions: {},
  },
  comparisons: { vs_initial: null, vs_previous: null, vs_minimum: null },
  freshness: listFixture.meta.freshness,
  capabilities: { raw_series: "supported", window: "supported" },
};

test("V2 tracking accepts only the declared list and creation contracts", () => {
  const parsed = parseTrackedOffersV2Response(listFixture);
  assert.equal(parsed.data[0]?.latest_observation?.price.basis, "total_stay");

  const created = parseTrackedOfferV2CreateResponse({
    tracking: trackingFixture,
    creation: { outcome: "created", semantic_dedupe: false },
  });
  assert.equal(created.creation.outcome, "created");
  assert.equal(
    parseTrackedOfferV2LifecycleResponse({ tracking: trackingFixture, outcome: "applied" }).tracking.state_version,
    1,
  );
  assert.equal(
    parseTrackedOfferV2LifecycleResponse({
      tracking: { ...trackingFixture, state: "archived" },
      outcome: "applied",
    }).tracking.state,
    "archived",
  );

  assert.throws(
    () => parseTrackedOffersV2Response({ data: [], meta: { contract_version: "wrong" } }),
    (error: unknown) => error instanceof HotelsRequestError && error.status === 502,
  );
  assert.throws(
    () => parseTrackedOfferV2LifecycleResponse({ tracking: { ...trackingFixture, state: "expired" }, outcome: "applied" }),
    (error: unknown) => error instanceof HotelsRequestError && error.status === 502,
  );
  assert.throws(
    () => parseTrackedOfferV2CreateResponse({ tracking: trackingFixture, creation: { outcome: "other" } }),
    (error: unknown) => error instanceof HotelsRequestError && error.status === 502,
  );
  assert.throws(
    () => parseTrackedOffersV2Response({
      ...listFixture,
      data: [{ ...trackingFixture, latest_observation: null }],
    }),
    (error: unknown) => error instanceof HotelsRequestError && error.status === 502,
  );
  assert.throws(
    () => parseTrackedOffersV2Response({
      ...listFixture,
      data: [{
        ...trackingFixture,
        stay_context: { ...trackingFixture.stay_context, check_in: null, check_out: null },
      }],
    }),
    (error: unknown) => error instanceof HotelsRequestError && error.status === 502,
  );
  assert.throws(
    () => parseTrackedOfferV2CreateResponse({
      tracking: trackingFixture,
      creation: { outcome: "created", semantic_dedupe: true },
    }),
    (error: unknown) => error instanceof HotelsRequestError && error.status === 502,
  );
  assert.throws(
    () => parseTrackedOffersV2Response({
      ...listFixture,
      data: [{
        ...trackingFixture,
        state: "unavailable",
      }],
    }),
    (error: unknown) => error instanceof HotelsRequestError && error.status === 502,
  );
  assert.throws(
    () => parseTrackedOffersV2Response({
      ...listFixture,
      data: [{ ...trackingFixture, state_version: 0 }],
    }),
    (error: unknown) => error instanceof HotelsRequestError && error.status === 502,
  );
});

test("V2 tracking creation posts only its canonical source rate identifier", async () => {
  const originalFetch = globalThis.fetch;
  let path = "";
  let body = "";

  globalThis.fetch = async (input, init) => {
    path = String(input);
    body = String(init?.body);
    return new Response(JSON.stringify({
      tracking: trackingFixture,
      creation: { outcome: "created", semantic_dedupe: false },
    }), {
      status: 201,
      headers: { "content-type": "application/json" },
    });
  };

  try {
    const payload = await createTrackedOfferV2("source-rate-1");
    assert.equal(payload.tracking.id, "tracking-1");
    assert.match(path, /\/api\/v1\/hotels\/v2\/tracked-offers$/);
    assert.equal(body, JSON.stringify({ source_rate_id: "source-rate-1" }));
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("V2 history accepts only chronological private observations with declared exclusions", () => {
  const parsed = parseTrackedOfferHistoryV2Response(historyFixture);
  assert.equal(parsed.series.points[0]?.price.basis, "total_stay");
  assert.throws(
    () => parseTrackedOfferHistoryV2Response({
      ...historyFixture,
      aggregates: { ...historyFixture.aggregates, sample_size_total: 2 },
    }),
    (error: unknown) => error instanceof HotelsRequestError && error.status === 502,
  );
  assert.throws(
    () => parseTrackedOfferHistoryV2Response({
      ...historyFixture,
      series: { ...historyFixture.series, points: [{ ...historyFixture.series.points[0], eligibility: "other" }] },
    }),
    (error: unknown) => error instanceof HotelsRequestError && error.status === 502,
  );
});
