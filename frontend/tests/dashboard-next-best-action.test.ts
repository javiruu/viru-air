import assert from "node:assert/strict";
import test from "node:test";

import {
  getDashboardNextActionCandidates,
  pickDashboardNextBestAction,
  type DashboardHistoryRow,
  type DashboardNotificationSummary,
  type DashboardWatch,
} from "@/modules/dashboard/next-best-action";

function buildWatch(partial: Partial<DashboardWatch> = {}): DashboardWatch {
  return {
    id: partial.id ?? "watch-1",
    origin_iata: partial.origin_iata ?? "MAD",
    destination_iata: partial.destination_iata ?? "BGY",
    travel_date_local: partial.travel_date_local ?? "2026-08-10",
  };
}

function buildRow(partial: Partial<DashboardHistoryRow> = {}): DashboardHistoryRow {
  return {
    watch_id: partial.watch_id ?? "watch-1",
    captured_at_utc: partial.captured_at_utc ?? "2026-07-04T10:00:00.000Z",
    raw_price: partial.raw_price ?? 80,
    raw_currency: partial.raw_currency ?? "EUR",
  };
}

function buildSummary(partial: Partial<DashboardNotificationSummary> = {}): DashboardNotificationSummary {
  return {
    total: partial.total ?? 0,
    unread: partial.unread ?? 0,
    price: partial.price ?? 0,
    security: partial.security ?? 0,
    digest: partial.digest ?? 0,
    worker: partial.worker ?? 0,
  };
}

test("dashboard picks a strong drop before any weaker signal", () => {
  const action = pickDashboardNextBestAction({
    watches: [buildWatch()],
    historyRows: [
      buildRow({ captured_at_utc: "2026-07-04T08:00:00.000Z", raw_price: 92 }),
      buildRow({ captured_at_utc: "2026-07-04T10:00:00.000Z", raw_price: 74 }),
    ],
    notificationSummary: buildSummary({ unread: 3, total: 3, price: 3 }),
    now: new Date("2026-07-04T12:00:00.000Z"),
  });

  assert.equal(action.kind, "strong_drop");
  assert.equal(action.dropAmount, 18);
  assert.equal(action.routeLabel, "MAD -> BGY");
});

test("dashboard marks a fresh new low when latest beats all prior prices", () => {
  const action = pickDashboardNextBestAction({
    watches: [buildWatch()],
    historyRows: [
      buildRow({ captured_at_utc: "2026-07-02T10:00:00.000Z", raw_price: 95 }),
      buildRow({ captured_at_utc: "2026-07-03T10:00:00.000Z", raw_price: 82 }),
      buildRow({ captured_at_utc: "2026-07-04T10:00:00.000Z", raw_price: 79 }),
    ],
    notificationSummary: buildSummary(),
    now: new Date("2026-07-04T12:00:00.000Z"),
  });

  assert.equal(action.kind, "new_low");
  assert.equal(action.latestPrice, 79);
  assert.equal(action.previousLowPrice, 82);
});

test("dashboard uses best price of month only with enough monthly observations", () => {
  const action = pickDashboardNextBestAction({
    watches: [buildWatch()],
    historyRows: [
      buildRow({ captured_at_utc: "2026-06-20T10:00:00.000Z", raw_price: 110 }),
      buildRow({ captured_at_utc: "2026-06-28T10:00:00.000Z", raw_price: 88 }),
      buildRow({ captured_at_utc: "2026-07-01T10:00:00.000Z", raw_price: 86 }),
      buildRow({ captured_at_utc: "2026-07-04T10:00:00.000Z", raw_price: 86 }),
    ],
    notificationSummary: buildSummary(),
    now: new Date("2026-07-04T12:00:00.000Z"),
  });

  assert.equal(action.kind, "best_month");
  assert.equal(action.monthlyObservationCount, 4);
});

test("dashboard falls back to unread alerts before stale watch when no price signal exists", () => {
  const action = pickDashboardNextBestAction({
    watches: [buildWatch()],
    historyRows: [buildRow({ captured_at_utc: "2026-07-02T10:00:00.000Z", raw_price: 80 })],
    notificationSummary: buildSummary({ unread: 2, total: 2, price: 2 }),
    now: new Date("2026-07-04T12:00:00.000Z"),
  });

  assert.equal(action.kind, "unread_alerts");
  assert.equal(action.unreadCount, 2);
});

test("dashboard exposes a calm state instead of an empty block when nothing urgent exists", () => {
  const action = pickDashboardNextBestAction({
    watches: [buildWatch()],
    historyRows: [
      buildRow({ captured_at_utc: "2026-07-04T08:00:00.000Z", raw_price: 80 }),
      buildRow({ captured_at_utc: "2026-07-04T10:00:00.000Z", raw_price: 80 }),
    ],
    notificationSummary: buildSummary(),
    now: new Date("2026-07-04T12:00:00.000Z"),
  });

  assert.equal(action.kind, "calm");
  assert.equal(action.trackedCount, 1);
});

test("dashboard returns onboarding when no watchlist exists", () => {
  const action = pickDashboardNextBestAction({
    watches: [],
    historyRows: [],
    notificationSummary: buildSummary(),
    now: new Date("2026-07-04T12:00:00.000Z"),
  });

  assert.equal(action.kind, "onboarding");
});

test("dashboard suppresses a repeated weak action when another candidate exists", () => {
  const candidates = getDashboardNextActionCandidates({
    watches: [buildWatch()],
    historyRows: [
      buildRow({ captured_at_utc: "2026-06-29T10:00:00.000Z", raw_price: 93 }),
      buildRow({ captured_at_utc: "2026-07-01T10:00:00.000Z", raw_price: 89 }),
      buildRow({ captured_at_utc: "2026-07-04T10:00:00.000Z", raw_price: 89 }),
    ],
    notificationSummary: buildSummary({ unread: 1, total: 1, price: 1 }),
    now: new Date("2026-07-04T12:00:00.000Z"),
  });

  const action = pickDashboardNextBestAction({
    watches: [buildWatch()],
    historyRows: [
      buildRow({ captured_at_utc: "2026-06-29T10:00:00.000Z", raw_price: 93 }),
      buildRow({ captured_at_utc: "2026-07-01T10:00:00.000Z", raw_price: 89 }),
      buildRow({ captured_at_utc: "2026-07-04T10:00:00.000Z", raw_price: 89 }),
    ],
    notificationSummary: buildSummary({ unread: 1, total: 1, price: 1 }),
    now: new Date("2026-07-04T12:00:00.000Z"),
    seenActionKey: candidates[0]?.key ?? null,
  });

  assert.equal(candidates[0]?.kind, "best_month");
  assert.equal(action.kind, "unread_alerts");
});
