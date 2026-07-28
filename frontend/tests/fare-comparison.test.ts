import assert from "node:assert/strict";
import test from "node:test";

import {
  calculateComparableFare,
  createEmptyFareComparisonProfile,
  type FareComparisonProfile,
} from "../src/modules/shared/fareComparison";

test("comparable fare adds selected extras for every traveler", () => {
  const profile: FareComparisonProfile = {
    travelers: 2,
    extras: [
      { kind: "cabin_bag_10kg", selected: true, amount_per_person: 18 },
      { kind: "insurance", selected: true, amount_per_person: 9.5 },
      { kind: "fast_track", selected: false, amount_per_person: null },
    ],
  };

  assert.deepEqual(calculateComparableFare(80, profile), {
    base_total: 80,
    extras_total: 55,
    comparable_total: 135,
    is_complete: true,
    missing_kinds: [],
  });
});

test("comparable fare stays incomplete when a selected extra has no price", () => {
  const profile = createEmptyFareComparisonProfile(1);
  const withMissingInsurance: FareComparisonProfile = {
    ...profile,
    extras: profile.extras.map((extra) => (
      extra.kind === "insurance"
        ? { ...extra, selected: true }
        : extra
    )),
  };

  const result = calculateComparableFare(49.99, withMissingInsurance);

  assert.equal(result.comparable_total, null);
  assert.equal(result.is_complete, false);
  assert.deepEqual(result.missing_kinds, ["insurance"]);
});
