import assert from "node:assert/strict";
import test from "node:test";

import type { FareMemoryHealth } from "../src/modules/admin/fareMemoryHealth";
import { buildFareMemorySummary, countFrom } from "../src/modules/admin/fareMemoryHealth";

const snapshot: FareMemoryHealth = {
  generated_at: "2026-07-11T10:00:00",
  search_cache: {
    total_entries: 12,
    freshness: { fresh: 7, stale: 5 },
    status: { hit: 10, miss: 2 },
    expired_entries: 3,
  },
  negative_cache: {
    total_entries: 4,
    active_entries: 2,
    freshness: { negative_fresh: 2 },
    reasons: { provider_timeout: 2 },
  },
  popularity: {
    total_routes: 5,
    top_routes: [],
  },
  refresh_signals: {
    top_routes: [
      {
        route: "AGP-FCO",
        origin_iata: "AGP",
        destination_iata: "FCO",
        travel_date: "2026-07-30",
        active_watch_count: 2,
        enabled_alert_count: 1,
        recent_search_count: 6,
        days_until_departure: 19,
        priority_score: 77,
        suggested_job_priority: 423,
        reasons: ["active_watchlist", "recent_searches"],
      },
    ],
  },
  offer_memory: {
    offer_entries: 8,
    price_observations: 21,
    observations_last_24h: 9,
    changed_observations_last_24h: 4,
    validation_status: { revalidated: 17, inferred: 4 },
  },
  historical_aggregates: {
    mode: "dynamic_read_only",
    top_routes: [
      {
        route: "AGP-FCO",
        origin_iata: "AGP",
        destination_iata: "FCO",
        departure_date: "2026-07-30",
        currency: "EUR",
        observation_count: 3,
        min_price: 51,
        max_price: 82,
        latest_price: 61,
        latest_observed_at: "2026-07-10T12:00:00",
        compaction_candidate: false,
      },
      {
        route: "MAD-DUB",
        origin_iata: "MAD",
        destination_iata: "DUB",
        departure_date: "2026-06-20",
        currency: "EUR",
        observation_count: 5,
        min_price: 44,
        max_price: 109,
        latest_price: 88,
        latest_observed_at: "2026-07-09T12:00:00",
        compaction_candidate: true,
      },
    ],
  },
  revalidation_jobs: {
    total_entries: 10,
    status: { queued: 4, running: 1, failed: 2, done: 3 },
    job_type: { boot_warmup: 6, manual: 4 },
    overdue_queued: 2,
    failed_last_24h: 1,
  },
};

test("fare memory summary preserves admin health counters", () => {
  assert.deepEqual(buildFareMemorySummary(snapshot), {
    cacheEntries: 12,
    expiredEntries: 3,
    negativeActiveEntries: 2,
    trackedRoutes: 5,
    offerEntries: 8,
    priceObservations: 21,
    observationsLast24h: 9,
    changedLast24h: 4,
    queuedJobs: 4,
    runningJobs: 1,
    failedJobs: 2,
    overdueQueued: 2,
    failedLast24h: 1,
    refreshSignalCount: 1,
    historicalRouteCount: 2,
    compactionCandidateCount: 1,
  });
});

test("countFrom treats missing status buckets as zero", () => {
  assert.equal(countFrom(snapshot.revalidation_jobs.status, "skipped"), 0);
});
