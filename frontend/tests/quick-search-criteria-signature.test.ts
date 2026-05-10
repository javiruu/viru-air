import assert from "node:assert/strict";
import test from "node:test";

import { buildCriteriaSignature, type CriteriaSignatureInput } from "../src/modules/quick-search/searchCriteria";

function createBaseInput(): CriteriaSignatureInput {
  return {
    origin: "MAD",
    destination: "BCN",
    originCountryCode: null,
    destinationCountryCode: null,
    travelDate: "2026-06-01",
    returnDate: "",
    isReturn: false,
    adults: 1,
    daysBefore: 0,
    daysAfter: 0,
    applyFlexReturn: false,
    includeStops: true,
    maxStops: 1,
    durationMax: "",
    riskFilter: "all",
    radiusKm: 150,
    includeNearbyOrigins: false,
    includeNearbyDestinations: false,
    excludeOrigins: [],
    excludeDestinations: [],
    excludeOriginInput: "",
    excludeDestinationInput: "",
    strictFilters: false,
    priceMin: "",
    priceMax: "",
    departAfter: "",
    departBefore: "",
    bufferMin: "",
  };
}

test("criteria signature stays stable after applying exclusion draft tokens", () => {
  const preSubmit = buildCriteriaSignature({
    ...createBaseInput(),
    excludeOriginInput: "agp, lis",
  });
  const postSubmit = buildCriteriaSignature({
    ...createBaseInput(),
    excludeOrigins: ["AGP", "LIS"],
    excludeOriginInput: "",
  });

  assert.equal(preSubmit, postSubmit);
});

