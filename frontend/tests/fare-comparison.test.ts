import assert from "node:assert/strict";
import test from "node:test";

import {
  attachFareAirline,
  calculateComparableFare,
  createEmptyFareComparisonProfile,
  resolveFareAirline,
  type FareComparisonProfile,
} from "../src/modules/shared/fareComparison";

test("Ryanair estimate applies official ranges per traveler and deduplicates Priority bundle", () => {
  const profile: FareComparisonProfile = {
    travelers: 2,
    extras: [
      { kind: "cabin_bag_10kg", selected: true },
      { kind: "priority_boarding", selected: true },
      { kind: "checked_bag_20kg", selected: true },
    ],
  };

  assert.deepEqual(calculateComparableFare(80, "EUR", profile, "ryanair-public-fares"), {
    base_total: 80,
    extras_min_total: 49.98,
    extras_max_total: 191.98,
    comparable_min_total: 129.98,
    comparable_max_total: 271.98,
    is_complete: true,
    unavailable_kinds: [],
    airline_id: "ryanair",
    airline_label: "Ryanair",
    source_url: "https://www.ryanair.com/no/no/nyttig-info/hjelpesenter/gebyrer",
    source_checked_on: "2026-07-28",
  });
});

test("Vueling applies per-flight seats and per-booking Flex Pack on multi-leg trips", () => {
  const profile: FareComparisonProfile = {
    travelers: 1,
    extras: [
      { kind: "seat_selection", selected: true },
      { kind: "flexible_ticket", selected: true },
    ],
  };

  const result = calculateComparableFare(49.99, "EUR", profile, "VY", [], 2);

  assert.equal(result.extras_min_total, 20);
  assert.equal(result.extras_max_total, 110);
  assert.equal(result.comparable_min_total, 69.99);
  assert.equal(result.comparable_max_total, 159.99);
  assert.equal(result.is_complete, true);
  assert.deepEqual(result.unavailable_kinds, []);
});

test("per-flight offers multiply by both travelers and itinerary legs", () => {
  const profile: FareComparisonProfile = {
    travelers: 2,
    extras: [
      { kind: "cabin_bag_10kg", selected: true },
      { kind: "priority_boarding", selected: true },
      { kind: "checked_bag_20kg", selected: true },
    ],
  };

  const result = calculateComparableFare(80, "EUR", profile, "FR", [], 2);

  assert.equal(result.extras_min_total, 99.96);
  assert.equal(result.extras_max_total, 383.96);
  assert.equal(result.comparable_min_total, 179.96);
  assert.equal(result.comparable_max_total, 463.96);
});

test("selected extras without a public calculable tariff remain explicit", () => {
  const profile = createEmptyFareComparisonProfile(1);
  const withFastTrack: FareComparisonProfile = {
    ...profile,
    extras: profile.extras.map((extra) => (
      extra.kind === "fast_track" ? { ...extra, selected: true } : extra
    )),
  };

  const result = calculateComparableFare(49.99, "EUR", withFastTrack, "ryanair");

  assert.equal(result.comparable_min_total, 49.99);
  assert.equal(result.comparable_max_total, null);
  assert.equal(result.is_complete, false);
  assert.deepEqual(result.unavailable_kinds, ["fast_track"]);
});

test("Vueling insurance remains explicit because its public table omits a billing unit", () => {
  const profile: FareComparisonProfile = {
    travelers: 1,
    extras: [{ kind: "insurance", selected: true }],
  };

  const result = calculateComparableFare(49.99, "EUR", profile, "VY");

  assert.equal(result.comparable_min_total, 49.99);
  assert.equal(result.is_complete, false);
  assert.deepEqual(result.unavailable_kinds, ["insurance"]);
});

test("airline resolution prefers carrier codes and supports provider aliases", () => {
  assert.equal(resolveFareAirline("amadeus", ["VY"]), "vueling");
  assert.equal(resolveFareAirline("wizzair-public-fares"), "wizzair");
  assert.equal(resolveFareAirline("unknown-provider", ["U2"]), "easyjet");
  assert.equal(resolveFareAirline("amadeus", ["VY", "FR"]), null);
  assert.equal(resolveFareAirline("amadeus", ["VY", "IB"]), null);
});

test("Watchlist-ready profiles persist the resolved airline and itinerary size", () => {
  const profile = createEmptyFareComparisonProfile(2);

  assert.deepEqual(
    attachFareAirline(profile, "amadeus", ["VY", "VY"], 2),
    {
      ...profile,
      airline_id: "vueling",
      flight_count: 2,
    },
  );
});

test("mixed-airline itineraries remain unpriced instead of borrowing one catalog", () => {
  const profile: FareComparisonProfile = {
    travelers: 1,
    extras: [{ kind: "checked_bag_20kg", selected: true }],
  };

  const result = calculateComparableFare(90, "EUR", profile, "amadeus", ["VY", "FR"], 2);

  assert.equal(result.airline_id, null);
  assert.equal(result.comparable_min_total, 90);
  assert.equal(result.comparable_max_total, null);
  assert.deepEqual(result.unavailable_kinds, ["checked_bag_20kg"]);
  assert.equal(result.source_url, null);
});

test("easyJet remains sourced but marks selected extras unavailable", () => {
  const profile: FareComparisonProfile = {
    ...createEmptyFareComparisonProfile(1),
    airline_id: "easyjet",
    extras: [{ kind: "cabin_bag_10kg", selected: true }],
  };

  const result = calculateComparableFare(55, "EUR", profile, null);

  assert.equal(result.comparable_min_total, 55);
  assert.equal(result.is_complete, false);
  assert.deepEqual(result.unavailable_kinds, ["cabin_bag_10kg"]);
  assert.equal(result.airline_label, "easyJet");
  assert.equal(result.source_url, "https://www.easyjet.com/en/terms-and-conditions/fees");
});

test("unknown airlines never invent a tariff or official source", () => {
  const profile: FareComparisonProfile = {
    ...createEmptyFareComparisonProfile(1),
    extras: [{ kind: "checked_bag_20kg", selected: true }],
  };

  const result = calculateComparableFare(70, "EUR", profile, "unknown-provider");

  assert.equal(result.comparable_min_total, 70);
  assert.equal(result.is_complete, false);
  assert.deepEqual(result.unavailable_kinds, ["checked_bag_20kg"]);
  assert.equal(result.airline_id, null);
  assert.equal(result.source_url, null);
});

test("catalog prices are not converted into an unsupported currency", () => {
  const profile: FareComparisonProfile = {
    ...createEmptyFareComparisonProfile(1),
    airline_id: "vueling",
    extras: [{ kind: "checked_bag_20kg", selected: true }],
  };

  const result = calculateComparableFare(60, "USD", profile, null);

  assert.equal(result.comparable_min_total, 60);
  assert.equal(result.is_complete, false);
  assert.deepEqual(result.unavailable_kinds, ["checked_bag_20kg"]);
  assert.equal(result.source_url, "https://www.vueling.com/en/vueling-services/supplementary-service-rates/");
});
