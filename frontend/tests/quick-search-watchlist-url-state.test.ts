import assert from "node:assert/strict";
import test from "node:test";

import {
  // Sanitization helpers
  sanitizeIata,
  sanitizeIsoDate,
  sanitizeIsoMonth,
  sanitizeWatchId,
  sanitizePositiveInt,
  sanitizeClampedInt,
  sanitizeFlag,
  sanitizeViewMode,
  sanitizeRangeParam,

  // QuickSearch → Watchlist navigation
  buildWatchlistUrl,
  readWatchlistNavigationParams,
  readWatchlistViewParams,
  buildWatchlistViewSearchParams,

  // QuickSearch URL persistence
  readQuickSearchUrlState,
  buildQuickSearchSearchParams,

  // Param constants (used to verify contract consistency)
  WL_PARAM_ORIGIN,
  WL_PARAM_DESTINATION,
  WL_PARAM_TRAVEL_DATE,
  WL_PARAM_WATCH_ID,
  WL_PARAM_VIEW,
  WL_PARAM_RANGE,
  QS_PARAM_ORIGIN,
  QS_PARAM_DESTINATION,
  QS_PARAM_TRAVEL_DATE,
  QS_PARAM_RETURN_DATE,
  QS_PARAM_IS_RETURN,
  QS_PARAM_ADULTS,
  QS_PARAM_FLEX_BEFORE,
  QS_PARAM_FLEX_AFTER,
  QS_PARAM_RADIUS,
  QS_PARAM_STRICT,
} from "../src/modules/shared/useRouteState";

// ─── Sanitization ───────────────────────────────────────────────────

test("sanitizeIata returns uppercase valid code", () => {
  assert.equal(sanitizeIata("mad"), "MAD");
  assert.equal(sanitizeIata("  dub "), "DUB");
  assert.equal(sanitizeIata("BCN"), "BCN");
});

test("sanitizeIata rejects invalid codes", () => {
  assert.equal(sanitizeIata(""), "");
  assert.equal(sanitizeIata("M"), "");
  assert.equal(sanitizeIata("MADR"), "");
  assert.equal(sanitizeIata("12A"), "");
  assert.equal(sanitizeIata(null), "");
  assert.equal(sanitizeIata(undefined), "");
});

test("sanitizeIsoDate accepts valid ISO dates", () => {
  assert.equal(sanitizeIsoDate("2026-07-15"), "2026-07-15");
  assert.equal(sanitizeIsoDate(" 2026-01-01 "), "2026-01-01");
});

test("sanitizeIsoDate rejects invalid dates", () => {
  assert.equal(sanitizeIsoDate(""), "");
  assert.equal(sanitizeIsoDate("07-15-2026"), "");
  assert.equal(sanitizeIsoDate("2026/07/15"), "");
  assert.equal(sanitizeIsoDate("2026-13-01"), "2026-13-01"); // validates format, not calendar
  assert.equal(sanitizeIsoDate(null), "");
});

test("sanitizeWatchId accepts URL-safe ids", () => {
  assert.equal(sanitizeWatchId("watch_12345"), "watch_12345");
  assert.equal(sanitizeWatchId("abc-def_123"), "abc-def_123");
});

test("sanitizeWatchId rejects unsafe ids", () => {
  assert.equal(sanitizeWatchId(""), "");
  assert.equal(sanitizeWatchId("abc"), "");
  assert.equal(sanitizeWatchId("bad/id"), "");
  assert.equal(sanitizeWatchId(null), "");
});

test("sanitizeIsoMonth accepts valid ISO months", () => {
  assert.equal(sanitizeIsoMonth("2026-07"), "2026-07");
  assert.equal(sanitizeIsoMonth("2030-12"), "2030-12");
});

test("sanitizeIsoMonth rejects invalid months", () => {
  assert.equal(sanitizeIsoMonth(""), "");
  assert.equal(sanitizeIsoMonth("2026-7"), "");
  assert.equal(sanitizeIsoMonth("07-2026"), "");
});

test("sanitizePositiveInt parses valid integers", () => {
  assert.equal(sanitizePositiveInt("5"), 5);
  assert.equal(sanitizePositiveInt("1", 1, 9), 1);
  assert.equal(sanitizePositiveInt("9", 1, 9), 9);
});

test("sanitizePositiveInt returns null for invalid input", () => {
  assert.equal(sanitizePositiveInt(""), null);
  assert.equal(sanitizePositiveInt("abc"), null);
  assert.equal(sanitizePositiveInt("0", 1), null);
  assert.equal(sanitizePositiveInt("10", 1, 9), null);
  assert.equal(sanitizePositiveInt(null), null);
});

test("sanitizeClampedInt clamps values to range", () => {
  assert.equal(sanitizeClampedInt("5", 0, 3, 0), 3);
  assert.equal(sanitizeClampedInt("-1", 0, 3, 0), 0);
  assert.equal(sanitizeClampedInt("2", 0, 3, 0), 2);
});

test("sanitizeClampedInt falls back for invalid input", () => {
  assert.equal(sanitizeClampedInt("", 0, 3, 1), 1);
  assert.equal(sanitizeClampedInt("abc", 0, 3, 1), 1);
  assert.equal(sanitizeClampedInt(null, 0, 3, 1), 1);
});

test("sanitizeFlag parses true values", () => {
  assert.equal(sanitizeFlag("1"), true);
  assert.equal(sanitizeFlag("true"), true);
  assert.equal(sanitizeFlag("TRUE"), true);
});

test("sanitizeFlag parses false values", () => {
  assert.equal(sanitizeFlag("0"), false);
  assert.equal(sanitizeFlag("false"), false);
});

test("sanitizeFlag returns null for ambiguous values", () => {
  assert.equal(sanitizeFlag(""), null);
  assert.equal(sanitizeFlag("yes"), null);
  assert.equal(sanitizeFlag(null), null);
});

test("sanitizeViewMode respects valid modes", () => {
  assert.equal(sanitizeViewMode("chart"), "chart");
  assert.equal(sanitizeViewMode("calendar"), "calendar");
});

test("sanitizeViewMode falls back for invalid modes", () => {
  assert.equal(sanitizeViewMode("map"), "chart");
  assert.equal(sanitizeViewMode(""), "chart");
  assert.equal(sanitizeViewMode(null), "chart");
  assert.equal(sanitizeViewMode("list", "calendar"), "calendar");
});

test("sanitizeRangeParam respects valid ranges", () => {
  assert.equal(sanitizeRangeParam("30"), "30");
  assert.equal(sanitizeRangeParam("all"), "all");
});

test("sanitizeRangeParam falls back for invalid ranges", () => {
  assert.equal(sanitizeRangeParam("90"), "30");
  assert.equal(sanitizeRangeParam(""), "30");
  assert.equal(sanitizeRangeParam(null, "all"), "all");
});

// ─── QuickSearch → Watchlist navigation ────────────────────────────

test("buildWatchlistUrl builds URL with valid params", () => {
  const url = buildWatchlistUrl({
    origin: "MAD",
    destination: "DUB",
    travelDate: "2026-07-15",
  });
  assert.equal(url, "/watchlist?origin=MAD&destination=DUB&travelDate=2026-07-15");
});

test("buildWatchlistUrl includes watchId before route params", () => {
  const url = buildWatchlistUrl({
    origin: "MAD",
    destination: "DUB",
    travelDate: "2026-07-15",
    watchId: "watch_12345",
  });
  assert.equal(url, "/watchlist?watchId=watch_12345&origin=MAD&destination=DUB&travelDate=2026-07-15");
});

test("buildWatchlistUrl sanitizes lowercase and whitespace", () => {
  const url = buildWatchlistUrl({
    origin: "  mad ",
    destination: "dub",
    travelDate: "2026-07-15",
  });
  assert.equal(url, "/watchlist?origin=MAD&destination=DUB&travelDate=2026-07-15");
});

test("buildWatchlistUrl omits invalid params", () => {
  const url = buildWatchlistUrl({
    origin: "",
    destination: "DUB",
    travelDate: "bad-date",
  });
  assert.equal(url, "/watchlist?destination=DUB");
});

test("buildWatchlistUrl returns bare path when no valid params", () => {
  const url = buildWatchlistUrl({
    origin: "",
    destination: "",
    travelDate: "",
  });
  assert.equal(url, "/watchlist");
});

test("buildWatchlistUrl handles nullish/empty travelDate", () => {
  const url = buildWatchlistUrl({
    origin: "MAD",
    destination: "DUB",
    travelDate: "",
  });
  assert.equal(url, "/watchlist?origin=MAD&destination=DUB");
});

// ─── Watchlist URL param reading ───────────────────────────────────

test("readWatchlistNavigationParams reads valid params", () => {
  const sp = new URLSearchParams("?origin=MAD&destination=DUB&travelDate=2026-07-15");
  const nav = readWatchlistNavigationParams(sp);
  assert.deepEqual(nav, {
    origin: "MAD",
    destination: "DUB",
    travelDate: "2026-07-15",
    watchId: "",
  });
});

test("readWatchlistNavigationParams reads watchId", () => {
  const sp = new URLSearchParams("?watchId=watch_12345&origin=MAD&destination=DUB&travelDate=2026-07-15");
  const nav = readWatchlistNavigationParams(sp);
  assert.deepEqual(nav, {
    origin: "MAD",
    destination: "DUB",
    travelDate: "2026-07-15",
    watchId: "watch_12345",
  });
});

test("readWatchlistNavigationParams sanitizes invalid params", () => {
  const sp = new URLSearchParams("?origin=INVALID&destination=X&travelDate=not-a-date");
  const nav = readWatchlistNavigationParams(sp);
  assert.deepEqual(nav, {
    origin: "",
    destination: "",
    travelDate: "",
    watchId: "",
  });
});

test("readWatchlistNavigationParams returns empty for missing params", () => {
  const sp = new URLSearchParams("?unrelated=1");
  const nav = readWatchlistNavigationParams(sp);
  assert.deepEqual(nav, {
    origin: "",
    destination: "",
    travelDate: "",
    watchId: "",
  });
});

test("readWatchlistNavigationParams handles empty URLSearchParams", () => {
  const sp = new URLSearchParams("");
  const nav = readWatchlistNavigationParams(sp);
  assert.deepEqual(nav, {
    origin: "",
    destination: "",
    travelDate: "",
    watchId: "",
  });
});

test("readWatchlistViewParams reads valid params", () => {
  const sp = new URLSearchParams("?view=calendar&range=all");
  const { view, range } = readWatchlistViewParams(sp);
  assert.equal(view, "calendar");
  assert.equal(range, "all");
});

test("readWatchlistViewParams falls back for invalid params", () => {
  const sp = new URLSearchParams("?view=map&range=90");
  const { view, range } = readWatchlistViewParams(sp);
  assert.equal(view, "chart");
  assert.equal(range, "30");
});

test("buildWatchlistViewSearchParams omits default values", () => {
  const qs = buildWatchlistViewSearchParams({
    origin: "MAD",
    destination: "DUB",
    view: "chart",
    range: "30",
  });
  // default view="chart" and range="30" should be omitted
  assert.equal(qs, "origin=MAD&destination=DUB");
});

test("buildWatchlistViewSearchParams includes non-default values", () => {
  const qs = buildWatchlistViewSearchParams({
    origin: "MAD",
    destination: "DUB",
    travelDate: "2026-07-15",
    watchId: "watch_12345",
    view: "calendar",
    range: "all",
  });
  assert.equal(qs, "watchId=watch_12345&origin=MAD&destination=DUB&travelDate=2026-07-15&view=calendar&range=all");
});

test("buildWatchlistViewSearchParams returns empty for all defaults", () => {
  const qs = buildWatchlistViewSearchParams({});
  assert.equal(qs, "");
});

// ─── QuickSearch URL persistence ───────────────────────────────────

test("readQuickSearchUrlState reads all params", () => {
  const sp = new URLSearchParams(
    "?origin=MAD&destination=DUB&travelDate=2026-07-15&returnDate=2026-07-22" +
    "&isReturn=1&adults=2&flexB=1&flexA=2&radius=250&strict=0"
  );
  const state = readQuickSearchUrlState(sp);
  assert.deepEqual(state, {
    origin: "MAD",
    destination: "DUB",
    travelDate: "2026-07-15",
    returnDate: "2026-07-22",
    isReturn: true,
    adults: 2,
    flexBefore: 1,
    flexAfter: 2,
    radius: 250,
    strict: false,
  });
});

test("readQuickSearchUrlState returns defaults for missing params", () => {
  const sp = new URLSearchParams("");
  const state = readQuickSearchUrlState(sp);
  assert.equal(state.origin, "");
  assert.equal(state.destination, "");
  assert.equal(state.travelDate, "");
  assert.equal(state.returnDate, "");
  assert.equal(state.isReturn, false);
  assert.equal(state.adults, 1);
  assert.equal(state.flexBefore, 0);
  assert.equal(state.flexAfter, 0);
  assert.equal(state.radius, 150);
  assert.equal(state.strict, true);
});

test("readQuickSearchUrlState sanitizes invalid values", () => {
  const sp = new URLSearchParams(
    "?origin=12&destination=X&travelDate=not-date&adults=0&flexB=-1&radius=999&strict=maybe"
  );
  const state = readQuickSearchUrlState(sp);
  assert.equal(state.origin, "");
  assert.equal(state.destination, "");
  assert.equal(state.travelDate, "");
  assert.equal(state.adults, 1);   // clamped to default (min 1)
  assert.equal(state.flexBefore, 0);
  // radius=999 clamped to [10, 500] → 500
  assert.equal(state.radius, 500);
  // strict="maybe" → null → default true
  assert.equal(state.strict, true);
});

test("buildQuickSearchSearchParams includes non-default params", () => {
  const qs = buildQuickSearchSearchParams({
    origin: "MAD",
    destination: "DUB",
    travelDate: "2026-07-15",
    returnDate: "2026-07-22",
    isReturn: true,
    adults: 2,
    flexBefore: 1,
    flexAfter: 2,
    radius: 250,
    strict: false,
  });
  assert(qs.includes("origin=MAD"));
  assert(qs.includes("destination=DUB"));
  assert(qs.includes("travelDate=2026-07-15"));
  assert(qs.includes("returnDate=2026-07-22"));
  assert(qs.includes("isReturn=1"));
  assert(qs.includes("adults=2"));
  assert(qs.includes("flexB=1"));
  assert(qs.includes("flexA=2"));
  assert(qs.includes("radius=250"));
  assert(qs.includes("strict=0"));
});

test("buildQuickSearchSearchParams omits defaults", () => {
  const qs = buildQuickSearchSearchParams({
    origin: "MAD",
    destination: "DUB",
    travelDate: "2026-07-15",
  });
  // adults=1 (default), radius=150 (default), strict=true (default) should be omitted
  assert.equal(qs, "origin=MAD&destination=DUB&travelDate=2026-07-15");
});

test("buildQuickSearchSearchParams returns empty for no values", () => {
  const qs = buildQuickSearchSearchParams({});
  assert.equal(qs, "");
});

test("buildQuickSearchSearchParams sanitizes values", () => {
  const qs = buildQuickSearchSearchParams({
    origin: "  mad ",
    destination: "dub",
    travelDate: "2026-07-15",
  });
  assert.equal(qs, "origin=MAD&destination=DUB&travelDate=2026-07-15");
});

// ─── Round-trip consistency ────────────────────────────────────────

test("QuickSearch URL round-trip: state → build → read preserves values", () => {
  const input = {
    origin: "MAD",
    destination: "DUB",
    travelDate: "2026-07-15",
    returnDate: "2026-07-22",
    isReturn: true,
    adults: 2,
    flexBefore: 1,
    flexAfter: 2,
    radius: 250,
    strict: false,
  };
  const qs = buildQuickSearchSearchParams(input);
  const sp = new URLSearchParams(qs);
  const output = readQuickSearchUrlState(sp);

  assert.equal(output.origin, input.origin);
  assert.equal(output.destination, input.destination);
  assert.equal(output.travelDate, input.travelDate);
  assert.equal(output.returnDate, input.returnDate);
  assert.equal(output.isReturn, input.isReturn);
  assert.equal(output.adults, input.adults);
  assert.equal(output.flexBefore, input.flexBefore);
  assert.equal(output.flexAfter, input.flexAfter);
  assert.equal(output.radius, input.radius);
  assert.equal(output.strict, input.strict);
});

test("Watchlist navigation round-trip: buildWatchlistUrl → readWatchlistNavigationParams", () => {
  const url = buildWatchlistUrl({
    origin: "BCN",
    destination: "LIS",
    travelDate: "2026-08-01",
  });
  // Extract query string from URL
  const qs = url.startsWith("/watchlist?") ? url.slice("/watchlist?".length) : "";
  const sp = new URLSearchParams(qs);
  const nav = readWatchlistNavigationParams(sp);

  assert.equal(nav.origin, "BCN");
  assert.equal(nav.destination, "LIS");
  assert.equal(nav.travelDate, "2026-08-01");
});

test("Watchlist view round-trip: buildWatchlistViewSearchParams → read", () => {
  const qs = buildWatchlistViewSearchParams({
    origin: "MAD",
    destination: "DUB",
    travelDate: "2026-07-15",
    view: "calendar",
    range: "all",
  });
  const sp = new URLSearchParams(qs);
  const nav = readWatchlistNavigationParams(sp);
  const { view, range } = readWatchlistViewParams(sp);

  assert.equal(nav.origin, "MAD");
  assert.equal(nav.destination, "DUB");
  assert.equal(nav.travelDate, "2026-07-15");
  assert.equal(view, "calendar");
  assert.equal(range, "all");
});

test("buildWatchlistUrl with defaults is readable as empty", () => {
  const url = buildWatchlistUrl({ origin: "", destination: "", travelDate: "" });
  assert.equal(url, "/watchlist");
});

// ─── Shared contract consistency ──────────────────────────────────

test("QuickSearch and Watchlist share same origin param name", () => {
  // The contract must use the same param name for origin across both routes
  assert.equal(QS_PARAM_ORIGIN, WL_PARAM_ORIGIN);
});

test("QuickSearch and Watchlist share same destination param name", () => {
  assert.equal(QS_PARAM_DESTINATION, WL_PARAM_DESTINATION);
});

test("QuickSearch and Watchlist share same travelDate param name", () => {
  assert.equal(QS_PARAM_TRAVEL_DATE, WL_PARAM_TRAVEL_DATE);
});

test("Watchlist has a dedicated watchId param", () => {
  assert.equal(WL_PARAM_WATCH_ID, "watchId");
});

// ─── Edge cases ───────────────────────────────────────────────────

test("buildWatchlistUrl handles all invalid params gracefully", () => {
  const url = buildWatchlistUrl({
    origin: null as unknown as string,
    destination: undefined as unknown as string,
    travelDate: null as unknown as string,
  });
  // sanitizeIata(null) returns "", sanitizeIsoDate(null) returns ""
  assert.equal(url, "/watchlist");
});

test("readQuickSearchUrlState handles empty/nullish search params gracefully", () => {
  const sp = new URLSearchParams();
  const state = readQuickSearchUrlState(sp);
  assert.equal(state.origin, "");
  assert.equal(state.destination, "");
  assert.equal(state.flexBefore, 0);
  assert.equal(state.flexAfter, 0);
});

test("partial quick-search state can contain only origin and destination", () => {
  const qs = buildQuickSearchSearchParams({ origin: "MAD", destination: "BCN" });
  assert.equal(qs, "origin=MAD&destination=BCN");
  const sp = new URLSearchParams(qs);
  const state = readQuickSearchUrlState(sp);
  assert.equal(state.origin, "MAD");
  assert.equal(state.destination, "BCN");
  assert.equal(state.travelDate, "");
  assert.equal(state.isReturn, false);
});
