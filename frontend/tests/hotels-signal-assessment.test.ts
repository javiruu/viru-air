import assert from "node:assert/strict";
import test from "node:test";

import { assessHotelSignal } from "../src/modules/hotels/signalAssessment";
import type { HotelParityOut, HotelRateOut } from "../src/modules/hotels/types";

function rate(overrides: Partial<HotelRateOut> = {}): HotelRateOut {
  return {
    id: "rate-1",
    hotel_id: "hotel-1",
    tracked_offer_id: null,
    provider_run_id: null,
    provider: "mock",
    check_in: "2026-07-10",
    check_out: "2026-07-12",
    guests: 2,
    room_label: null,
    meal_plan: null,
    cancellation_policy: null,
    currency: "EUR",
    amount: 100,
    availability_status: "available",
    deep_link: null,
    collected_at: "2026-06-21T08:00:00Z",
    ...overrides,
  };
}

function parity(overrides: Partial<HotelParityOut> = {}): HotelParityOut {
  return {
    check_in: "2026-07-10",
    check_out: "2026-07-12",
    guests: 2,
    currency: "EUR",
    provider_count: 2,
    lowest_price: 100,
    highest_price: 112,
    average_price: 106,
    spread_amount: 12,
    spread_percent: 12,
    is_parity_broken: true,
    status: "warning",
    label: "tensioned",
    ...overrides,
  };
}

test("hotel signal: no observations yields insufficient data state", () => {
  const result = assessHotelSignal([], null);
  assert.equal(result.level, "none");
  assert.equal(result.providerLabelKey, "hotels.provider.noObservations");
  assert.equal(result.detailKey, "hotels.parity.insufficientData");
});

test("hotel signal: single-provider observations stay limited", () => {
  const result = assessHotelSignal(
    [rate()],
    parity({
      provider_count: 1,
      lowest_price: null,
      highest_price: null,
      spread_percent: null,
      label: "limited",
      status: "info",
    }),
  );
  assert.equal(result.level, "limited");
  assert.equal(result.providerLabelKey, "hotels.provider.noSignal");
  assert.equal(result.parityBadgeKey, "hotels.parity.limited");
});

test("hotel signal: comparable provider data becomes scored", () => {
  const result = assessHotelSignal(
    [rate(), rate({ id: "rate-2", provider: "provider-b", amount: 112 })],
    parity({ label: "stable", status: "success", spread_percent: 5, is_parity_broken: false }),
  );
  assert.equal(result.level, "scored");
  assert.equal(result.providerLabelKey, "hotels.provider.active");
  assert.equal(result.parityBadgeKey, "hotels.parity.stable");
});
