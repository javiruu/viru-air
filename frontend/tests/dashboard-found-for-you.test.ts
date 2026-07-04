import assert from "node:assert/strict";
import test from "node:test";

import { getFoundForYouSuggestion } from "@/modules/dashboard/found-for-you";
import type { DashboardHistoryRow, DashboardWatch } from "@/modules/dashboard/next-best-action-types";
import type { ResumeSearchSnapshot } from "@/modules/quick-search/resume-search";

function watch(partial: Partial<DashboardWatch> = {}): DashboardWatch {
  return {
    id: partial.id ?? "watch-1",
    origin_iata: partial.origin_iata ?? "MAD",
    destination_iata: partial.destination_iata ?? "BGY",
    travel_date_local: partial.travel_date_local ?? "2026-08-20",
  };
}

function row(partial: Partial<DashboardHistoryRow> = {}): DashboardHistoryRow {
  return {
    watch_id: partial.watch_id ?? "watch-1",
    captured_at_utc: partial.captured_at_utc ?? "2026-07-04T10:00:00.000Z",
    raw_price: partial.raw_price ?? 19,
    raw_currency: partial.raw_currency ?? "EUR",
  };
}

function resume(partial: Partial<ResumeSearchSnapshot> = {}): ResumeSearchSnapshot {
  return {
    key: partial.key ?? "resume-1",
    ownerTokenHint: partial.ownerTokenHint ?? "token",
    savedAt: partial.savedAt ?? "2026-07-04T09:00:00.000Z",
    href: partial.href ?? "/quick-search?resume=1",
    summary: partial.summary ?? "Te quedaste mirando MAD -> BGY.",
    detail: partial.detail ?? "Tus ajustes siguen guardados para retomar.",
    origin: partial.origin ?? "MAD",
    destination: partial.destination ?? "MXP",
    travelDate: partial.travelDate ?? "2026-08-20",
    returnDate: partial.returnDate ?? "",
    isReturn: partial.isReturn ?? false,
    adults: partial.adults ?? 1,
    daysBefore: partial.daysBefore ?? 0,
    daysAfter: partial.daysAfter ?? 0,
    radiusKm: partial.radiusKm ?? 150,
    strictFilters: partial.strictFilters ?? true,
    departAfter: partial.departAfter ?? "07:00",
    departBefore: partial.departBefore ?? "22:00",
    includeStops: partial.includeStops ?? false,
    maxStops: partial.maxStops ?? 1,
    bufferMin: partial.bufferMin ?? "",
    includeNearbyOrigins: partial.includeNearbyOrigins ?? false,
    includeNearbyDestinations: partial.includeNearbyDestinations ?? true,
    excludeOrigins: partial.excludeOrigins ?? [],
    excludeDestinations: partial.excludeDestinations ?? [],
    priceMin: partial.priceMin ?? "",
    priceMax: partial.priceMax ?? "",
    durationMax: partial.durationMax ?? "",
    sortBy: partial.sortBy ?? "ranking",
    resultsCount: partial.resultsCount ?? 12,
  };
}

test("found-for-you shows only for a very cheap aligned route", () => {
  const suggestion = getFoundForYouSuggestion({
    watches: [watch({ destination_iata: "BGY" })],
    historyRows: [
      row({ captured_at_utc: "2026-07-02T10:00:00.000Z", raw_price: 61 }),
      row({ captured_at_utc: "2026-07-04T10:00:00.000Z", raw_price: 19 }),
    ],
    resumeSnapshot: resume(),
    now: new Date("2026-07-04T12:00:00.000Z"),
  });

  assert.ok(suggestion);
  assert.equal(suggestion.destination, "BGY");
  assert.equal(suggestion.currentPrice, 19);
  assert.equal(suggestion.matchedCountry, "Italia");
});

test("found-for-you stays hidden for mediocre or unrelated offers", () => {
  const suggestion = getFoundForYouSuggestion({
    watches: [watch({ destination_iata: "DUB" })],
    historyRows: [
      row({ watch_id: "watch-1", captured_at_utc: "2026-07-02T10:00:00.000Z", raw_price: 64 }),
      row({ watch_id: "watch-1", captured_at_utc: "2026-07-04T10:00:00.000Z", raw_price: 54 }),
    ],
    resumeSnapshot: resume({ destination: "MXP" }),
    now: new Date("2026-07-04T12:00:00.000Z"),
  });

  assert.equal(suggestion, null);
});

test("found-for-you honors dismissal of the same candidate", () => {
  const active = getFoundForYouSuggestion({
    watches: [watch()],
    historyRows: [
      row({ captured_at_utc: "2026-07-02T10:00:00.000Z", raw_price: 59 }),
      row({ captured_at_utc: "2026-07-04T10:00:00.000Z", raw_price: 21 }),
    ],
    resumeSnapshot: resume(),
    now: new Date("2026-07-04T12:00:00.000Z"),
  });

  assert.ok(active);

  const dismissed = getFoundForYouSuggestion({
    watches: [watch()],
    historyRows: [
      row({ captured_at_utc: "2026-07-02T10:00:00.000Z", raw_price: 59 }),
      row({ captured_at_utc: "2026-07-04T10:00:00.000Z", raw_price: 21 }),
    ],
    resumeSnapshot: resume(),
    dismissedKey: active.key,
    now: new Date("2026-07-04T12:00:00.000Z"),
  });

  assert.equal(dismissed, null);
});
