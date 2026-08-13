import assert from "node:assert/strict";
import test from "node:test";

import {
  buildHotelSearchQuery,
  buildRestoredHotelSearchQuery,
  canonicalizeHotelSearchQuery,
  hasHotelSearchIntent,
  isHotelDateRangeValid,
  readHotelSearchUrlState,
} from "../src/modules/hotels/hotelSearchUrlState";

test("hotel URL state round-trips area search context and selected hotel", () => {
  const query = buildHotelSearchQuery({
    mode: "area",
    query: "",
    city: "",
    areaQuery: "Madrid Centro",
    areaResolved: {
      area_label: "Madrid Centro",
      latitude: 40.4168,
      longitude: -3.7038,
      country_code: "ES",
      confidence: "high",
      source: "internal",
    },
    checkIn: "2026-09-12",
    checkOut: "2026-09-15",
    guests: 4,
    radiusKm: 20,
    useProvider: true,
    hasSearched: true,
    selectedHotelId: "hotel-123",
  });

  const state = readHotelSearchUrlState(new URLSearchParams(query));
  assert.equal(state.mode, "area");
  assert.equal(state.areaQuery, "Madrid Centro");
  assert.deepEqual(state.areaResolved, {
    area_label: "Madrid Centro",
    latitude: 40.4168,
    longitude: -3.7038,
    country_code: "ES",
    confidence: "high",
    source: "internal",
  });
  assert.equal(state.checkIn, "2026-09-12");
  assert.equal(state.checkOut, "2026-09-15");
  assert.equal(state.guests, 4);
  assert.equal(state.radiusKm, 20);
  assert.equal(state.useProvider, true);
  assert.equal(state.hasSearched, true);
  assert.equal(state.selectedHotelId, "hotel-123");
  assert.equal(hasHotelSearchIntent(state), true);
});

test("hotel URL state omits defaults and preserves name/city intent", () => {
  const query = buildHotelSearchQuery({
    mode: "name",
    query: "Royal",
    city: "Madrid",
    areaQuery: "",
    areaResolved: null,
    checkIn: "",
    checkOut: "",
    guests: 2,
    radiusKm: 10,
    useProvider: false,
    hasSearched: false,
    selectedHotelId: null,
  });

  assert.equal(query, "q=Royal&city=Madrid");
  const state = readHotelSearchUrlState(new URLSearchParams(query));
  assert.equal(state.query, "Royal");
  assert.equal(state.city, "Madrid");
  assert.equal(state.hasSearched, false);
  assert.equal(hasHotelSearchIntent(state), true);
});

test("hotel URL state does not treat incomplete area context as a searchable intent", () => {
  const state = readHotelSearchUrlState(
    new URLSearchParams({
      mode: "area",
      area: "Madrid",
      check_in: "2026-09-12",
      check_out: "2026-09-15",
      searched: "1",
    }),
  );

  assert.equal(state.areaResolved, null);
  assert.equal(state.guests, 2);
  assert.equal(state.radiusKm, 10);
  assert.equal(hasHotelSearchIntent(state), false);
});

test("hotel URL state canonicalizes reordered and equivalently encoded queries", () => {
  assert.equal(
    canonicalizeHotelSearchQuery("city=Madrid&q=Royal&searched=1"),
    canonicalizeHotelSearchQuery("searched=1&q=Royal&city=Madrid"),
  );
  assert.equal(
    canonicalizeHotelSearchQuery("q=Royal+Hotel"),
    canonicalizeHotelSearchQuery("q=Royal%20Hotel"),
  );
});

test("hotel URL state drops area-only dimensions when mode is name", () => {
  const query = buildHotelSearchQuery({
    mode: "name",
    query: "Royal",
    city: "Madrid",
    areaQuery: "Madrid Centro",
    areaResolved: {
      area_label: "Madrid Centro",
      latitude: 40.4168,
      longitude: -3.7038,
      country_code: "ES",
      confidence: "high",
      source: "internal",
    },
    checkIn: "",
    checkOut: "",
    guests: 2,
    radiusKm: 10,
    useProvider: false,
    hasSearched: false,
    selectedHotelId: null,
  });

  assert.equal(query, "q=Royal&city=Madrid");
});

test("hotel URL state sanitizes area metadata from untrusted URL values", () => {
  const state = readHotelSearchUrlState(
    new URLSearchParams({
      mode: "area",
      area: "Madrid",
      area_lat: "40.4168",
      area_lng: "-3.7038",
      area_country: "../../",
      area_confidence: "secret",
      area_source: "https://evil.test",
      check_in: "2026-09-12",
      check_out: "2026-09-15",
    }),
  );

  assert.deepEqual(state.areaResolved, {
    area_label: "Madrid",
    latitude: 40.4168,
    longitude: -3.7038,
    country_code: "ES",
    confidence: "medium",
    source: "url",
  });
});

test("hotel URL state restore rejects unknown schemas", () => {
  assert.equal(
    buildRestoredHotelSearchQuery({ schema: "hotel-search-v2", params: { q: "Royal" } }),
    null,
  );
});

test("hotel URL state restore blocks invalid area dates without building navigation", () => {
  assert.equal(
    buildRestoredHotelSearchQuery({
      params: {
        mode: "area",
        area: "Madrid",
        area_lat: "40.4168",
        area_lng: "-3.7038",
        area_country: "ES",
        check_in: "2026-09-15",
        check_out: "2026-09-12",
      },
    }),
    null,
  );
});

test("hotel URL state restore ignores private and unknown parameters", () => {
  const restored = readHotelSearchUrlState(
    new URLSearchParams({
      mode: "name",
      q: "Royal",
      user_id: "user-a",
      tracked_offer_id: "offer-private",
      rule_id: "rule-private",
      returnUrl: "https://example.test/account",
      unknown: "discard-me",
      searched: "1",
      hotel_id: "hotel-private",
    }),
  );

  const rebuilt = buildHotelSearchQuery({
    ...restored,
    hasSearched: false,
    selectedHotelId: null,
  });
  assert.equal(rebuilt, "q=Royal");
  assert.equal(rebuilt.includes("user_id"), false);
  assert.equal(rebuilt.includes("tracked_offer_id"), false);
  assert.equal(rebuilt.includes("returnUrl"), false);
});

test("hotel URL state rejects invalid area date ranges before search intent", () => {
  const state = readHotelSearchUrlState(
    new URLSearchParams({
      mode: "area",
      area: "Madrid",
      area_lat: "40.4168",
      area_lng: "-3.7038",
      area_country: "ES",
      check_in: "2026-09-15",
      check_out: "2026-09-12",
    }),
  );

  assert.ok(state.areaResolved);
  assert.equal(isHotelDateRangeValid(state.checkIn, state.checkOut), false);
  assert.equal(hasHotelSearchIntent(state), false);
});

test("hotel URL state falls back safely for invalid values", () => {
  const state = readHotelSearchUrlState(
    new URLSearchParams({
      mode: "unexpected",
      guests: "999",
      radius: "-4",
      check_in: "not-a-date",
      check_out: "2026-09-15",
      area: "Madrid",
      area_lat: "999",
      area_lng: "-3.7",
    }),
  );

  assert.equal(state.mode, "name");
  assert.equal(state.guests, 20);
  assert.equal(state.radiusKm, 1);
  assert.equal(state.checkIn, "");
  assert.equal(state.checkOut, "2026-09-15");
  assert.equal(state.areaResolved, null);
  assert.equal(hasHotelSearchIntent(state), false);
  assert.equal(isHotelDateRangeValid("2026-09-15", "2026-09-12"), false);
  assert.equal(isHotelDateRangeValid("2026-09-12", "2026-09-15"), true);
  assert.equal(isHotelDateRangeValid("2026-02-30", "2026-03-02"), false);
  assert.equal(isHotelDateRangeValid("2026-04-31", "2026-05-01"), false);
});
