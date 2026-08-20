import assert from "node:assert/strict";
import test from "node:test";

import { buildQuickSearchCanonicalPayload, prepareQuickSearchRequest } from "../src/modules/quick-search/api/buildQuickSearchRequest";

test("Quick Search preserves selected sparse dates as exact travel dates", () => {
  const prepared = prepareQuickSearchRequest({
    origin_iata: "MAD",
    destination_iata: "DUB",
    travel_date: "2026-09-03",
    date: "2026-09-03",
    travel_dates: ["2026-09-12", "2026-09-03", "2026-09-18", "2026-09-12"],
    flex_days_before: 3,
    flex_days_after: 3,
    radius_km: 150,
    include_stops: false,
    include_nearby_origins: false,
    include_nearby_destinations: false,
    max_stops: 0,
    exclude_origins: [],
    exclude_destinations: [],
    strict_filters: true,
    soft_filters_weight: 0.6,
  });

  assert.deepEqual(prepared.issues, []);
  assert.deepEqual(buildQuickSearchCanonicalPayload(prepared.params).travel.dates, [
    "2026-09-03",
    "2026-09-12",
    "2026-09-18",
  ]);
  assert.equal(prepared.params.flex_days_before, 0);
  assert.equal(prepared.params.flex_days_after, 0);
});
