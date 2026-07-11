export type FareMemoryCountMap = Readonly<Record<string, number>>;

export type FareMemoryPopularRoute = {
  readonly route: string;
  readonly origin_iata: string;
  readonly destination_iata: string;
  readonly travel_date: string;
  readonly currency: string;
  readonly search_count: number;
  readonly last_searched_at: string;
};

export type FareMemoryRefreshSignal = {
  readonly route: string;
  readonly origin_iata: string;
  readonly destination_iata: string;
  readonly travel_date: string;
  readonly active_watch_count: number;
  readonly enabled_alert_count: number;
  readonly recent_search_count: number;
  readonly days_until_departure: number;
  readonly priority_score: number;
  readonly suggested_job_priority: number;
  readonly reasons: readonly string[];
};

export type FareMemoryHistoricalAggregate = {
  readonly route: string;
  readonly origin_iata: string;
  readonly destination_iata: string;
  readonly departure_date: string;
  readonly currency: string;
  readonly observation_count: number;
  readonly min_price: number;
  readonly max_price: number;
  readonly latest_price: number;
  readonly latest_observed_at: string;
  readonly compaction_candidate: boolean;
};

export type FareMemoryHealth = {
  readonly generated_at: string;
  readonly search_cache: {
    readonly total_entries: number;
    readonly freshness: FareMemoryCountMap;
    readonly status: FareMemoryCountMap;
    readonly expired_entries: number;
  };
  readonly negative_cache: {
    readonly total_entries: number;
    readonly active_entries: number;
    readonly freshness: FareMemoryCountMap;
    readonly reasons: FareMemoryCountMap;
  };
  readonly popularity: {
    readonly total_routes: number;
    readonly top_routes: readonly FareMemoryPopularRoute[];
  };
  readonly refresh_signals: {
    readonly top_routes: readonly FareMemoryRefreshSignal[];
  };
  readonly offer_memory: {
    readonly offer_entries: number;
    readonly price_observations: number;
    readonly observations_last_24h: number;
    readonly changed_observations_last_24h: number;
    readonly validation_status: FareMemoryCountMap;
  };
  readonly historical_aggregates: {
    readonly mode: "dynamic_read_only" | string;
    readonly top_routes: readonly FareMemoryHistoricalAggregate[];
  };
  readonly revalidation_jobs: {
    readonly total_entries: number;
    readonly status: FareMemoryCountMap;
    readonly job_type: FareMemoryCountMap;
    readonly overdue_queued: number;
    readonly failed_last_24h: number;
  };
};

export type FareMemorySummary = {
  readonly cacheEntries: number;
  readonly expiredEntries: number;
  readonly negativeActiveEntries: number;
  readonly trackedRoutes: number;
  readonly offerEntries: number;
  readonly priceObservations: number;
  readonly observationsLast24h: number;
  readonly changedLast24h: number;
  readonly queuedJobs: number;
  readonly runningJobs: number;
  readonly failedJobs: number;
  readonly overdueQueued: number;
  readonly failedLast24h: number;
  readonly refreshSignalCount: number;
  readonly historicalRouteCount: number;
  readonly compactionCandidateCount: number;
};

export function countFrom(map: FareMemoryCountMap, key: string): number {
  return map[key] ?? 0;
}

export function buildFareMemorySummary(snapshot: FareMemoryHealth): FareMemorySummary {
  return {
    cacheEntries: snapshot.search_cache.total_entries,
    expiredEntries: snapshot.search_cache.expired_entries,
    negativeActiveEntries: snapshot.negative_cache.active_entries,
    trackedRoutes: snapshot.popularity.total_routes,
    offerEntries: snapshot.offer_memory.offer_entries,
    priceObservations: snapshot.offer_memory.price_observations,
    observationsLast24h: snapshot.offer_memory.observations_last_24h,
    changedLast24h: snapshot.offer_memory.changed_observations_last_24h,
    queuedJobs: countFrom(snapshot.revalidation_jobs.status, "queued"),
    runningJobs: countFrom(snapshot.revalidation_jobs.status, "running"),
    failedJobs: countFrom(snapshot.revalidation_jobs.status, "failed"),
    overdueQueued: snapshot.revalidation_jobs.overdue_queued,
    failedLast24h: snapshot.revalidation_jobs.failed_last_24h,
    refreshSignalCount: snapshot.refresh_signals.top_routes.length,
    historicalRouteCount: snapshot.historical_aggregates.top_routes.length,
    compactionCandidateCount: snapshot.historical_aggregates.top_routes.filter((route) => route.compaction_candidate).length,
  };
}
