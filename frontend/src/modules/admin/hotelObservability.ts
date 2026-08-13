export const HOTEL_METRIC_NAMES = ["sweep_run", "alert_event", "hotel_delivery"] as const;
export type HotelMetricName = (typeof HOTEL_METRIC_NAMES)[number];

export const HOTEL_PROVIDERS = ["mock", "makcorps", "local", "unknown"] as const;
export type HotelProvider = (typeof HOTEL_PROVIDERS)[number];

export const HOTEL_OUTCOMES = ["completed", "partial", "failed", "skipped", "created", "delivered", "retried"] as const;
export type HotelOutcome = (typeof HOTEL_OUTCOMES)[number];

const HOTEL_OUTCOMES_BY_METRIC: Record<HotelMetricName, readonly HotelOutcome[]> = {
  sweep_run: ["completed", "partial", "failed", "skipped"],
  alert_event: ["created"],
  hotel_delivery: ["delivered", "retried", "failed"],
};

export type HotelDailyMetric = {
  readonly metric_date: string;
  readonly metric_name: HotelMetricName;
  readonly provider: HotelProvider;
  readonly outcome: HotelOutcome;
  readonly count: number;
  readonly updated_at: string;
};

export type HotelObservabilityResponse = {
  readonly days: number;
  readonly metrics: readonly HotelDailyMetric[];
};

export const HOTEL_HEALTH_STATUSES = ["unknown", "not_configured", "ok", "degraded", "critical"] as const;
export type HotelHealthStatus = (typeof HOTEL_HEALTH_STATUSES)[number];

export type HotelHealthRun = {
  readonly provider: HotelProvider;
  readonly status: "running" | "completed" | "partial" | "failed" | "skipped" | "unknown";
  readonly started_at: string;
  readonly finished_at: string | null;
  readonly age_seconds: number;
};

export type HotelHealthProvider = {
  readonly provider: HotelProvider;
  readonly status: HotelHealthStatus;
  readonly runs: number;
  readonly running: number;
  readonly completed: number;
  readonly partial: number;
  readonly failed: number;
  readonly skipped: number;
  readonly deliveries_failed: number;
  readonly last_run_at: string | null;
  readonly last_run_status: HotelHealthRun["status"] | null;
  readonly last_finished_at: string | null;
  readonly age_seconds: number | null;
};

export type HotelHealthResponse = {
  readonly status: HotelHealthStatus;
  readonly generated_at: string;
  readonly window_hours: number;
  readonly latest_run: HotelHealthRun | null;
  readonly providers: readonly HotelHealthProvider[];
};

export type HotelRunDiagnosticStatus = "running" | "completed" | "partial" | "failed" | "skipped" | "unknown";
export type HotelRunDiagnostic = {
  readonly provider: HotelProvider;
  readonly status: HotelRunDiagnosticStatus;
  readonly started_at: string;
  readonly finished_at: string | null;
  readonly duration_seconds: number | null;
  readonly items_processed: number;
  readonly has_error: boolean;
  readonly outcomes: Readonly<Record<string, number>>;
};

export type HotelRunDiagnosticsResponse = {
  readonly limit: number;
  readonly runs: readonly HotelRunDiagnostic[];
};

export type HotelProviderControlOperation = "ingestion" | "revalidation" | "area_search" | "unknown";
export type HotelProviderBudget = {
  readonly provider: HotelProvider;
  readonly operation: HotelProviderControlOperation;
  readonly window_key: string;
  readonly hard_limit: number;
  readonly units_reserved: number;
  readonly units_used: number;
  readonly units_released: number;
  readonly units_remaining: number;
  readonly window_expires_at: string;
  readonly source: "local_config" | "unknown";
};
export type HotelProviderCircuit = {
  readonly provider: HotelProvider;
  readonly operation: HotelProviderControlOperation;
  readonly status: "closed" | "open" | "half_open" | "unknown";
  readonly consecutive_failures: number;
  readonly failure_threshold: number;
  readonly opened_at: string | null;
  readonly next_probe_at: string | null;
  readonly last_error_code: string | null;
  readonly updated_at: string;
};
export type HotelProviderControlsResponse = {
  readonly limit: number;
  readonly budgets: readonly HotelProviderBudget[];
  readonly circuits: readonly HotelProviderCircuit[];
};

export type HotelSweepLeaseState = "queued" | "running" | "expired" | "done" | "partial" | "skipped" | "failed" | "unknown";
export type HotelSweepLeaseDiagnostic = {
  readonly state: HotelSweepLeaseState;
  readonly attempt_count: number;
  readonly lease_expires_at: string | null;
  readonly finished_at: string | null;
  readonly last_error_code: string | null;
  readonly has_provider_run: boolean;
  readonly attention: boolean;
  readonly updated_at: string;
};
export type HotelSweepLeaseDiagnosticsResponse = {
  readonly limit: number;
  readonly generated_at: string;
  readonly sample_size: number;
  readonly attention_count: number;
  readonly counts: Readonly<Record<HotelSweepLeaseState, number>>;
  readonly leases: readonly HotelSweepLeaseDiagnostic[];
};

export type HotelProviderOutcomeDiagnostics = {
  readonly limit: number;
  readonly generated_at: string;
  readonly sample_size: number;
  readonly providers: readonly {
    readonly provider: HotelProvider;
    readonly runs: number;
    readonly statuses: Readonly<Record<HotelRunDiagnosticStatus, number>>;
    readonly outcomes: Readonly<Record<string, number>>;
  }[];
  readonly totals: Readonly<Record<string, number>>;
};

export function getHotelLeaseTone(state: HotelSweepLeaseState): "success" | "warning" | "error" | "info" {
  if (state === "done") return "success";
  if (state === "expired" || state === "partial" || state === "skipped" || state === "running") return "warning";
  if (state === "failed") return "error";
  return "info";
}

export function getHotelCircuitTone(status: HotelProviderCircuit["status"]): "success" | "warning" | "error" | "info" {
  if (status === "closed") return "success";
  if (status === "open") return "error";
  if (status === "half_open") return "warning";
  return "info";
}

export function getHotelRunTone(status: HotelRunDiagnosticStatus): "success" | "warning" | "error" | "info" {
  if (status === "completed") return "success";
  if (status === "partial" || status === "running" || status === "skipped") return "warning";
  if (status === "failed") return "error";
  return "info";
}

export function getHotelHealthTone(status: HotelHealthStatus): "success" | "warning" | "error" | "info" {
  if (status === "ok") return "success";
  if (status === "degraded" || status === "not_configured") return "warning";
  if (status === "critical") return "error";
  return "info";
}

export type HotelObservabilityFilters = {
  readonly days: number;
  readonly provider: HotelProvider | "";
  readonly metricName: HotelMetricName | "";
  readonly outcome: HotelOutcome | "";
};

export type HotelObservabilitySummary = {
  readonly total: number;
  readonly dates: number;
  readonly providers: number;
  readonly metricNames: number;
  readonly latestDate: string | null;
  readonly attentionCount: number;
};

export function getHotelOutcomesForMetric(metricName: HotelMetricName | ""): readonly HotelOutcome[] {
  if (!metricName) return HOTEL_OUTCOMES;
  return HOTEL_OUTCOMES_BY_METRIC[metricName];
}

export function buildHotelObservabilityPath(filters: HotelObservabilityFilters): string {
  const query = new URLSearchParams({ days: String(filters.days) });
  if (filters.provider) query.set("provider", filters.provider);
  if (filters.metricName) query.set("metric_name", filters.metricName);
  if (filters.outcome) query.set("outcome", filters.outcome);
  return `/admin/hotels/observability?${query.toString()}`;
}

export function buildHotelObservabilitySummary(metrics: readonly HotelDailyMetric[]): HotelObservabilitySummary {
  const dates = new Set(metrics.map((metric) => metric.metric_date));
  const providers = new Set(metrics.map((metric) => metric.provider));
  const metricNames = new Set(metrics.map((metric) => metric.metric_name));
  const latestDate = metrics.reduce<string | null>((latest, metric) => {
    if (!latest || metric.metric_date > latest) return metric.metric_date;
    return latest;
  }, null);

  return {
    total: metrics.reduce((sum, metric) => sum + metric.count, 0),
    dates: dates.size,
    providers: providers.size,
    metricNames: metricNames.size,
    latestDate,
    attentionCount: metrics
      .filter((metric) => metric.outcome === "failed" || metric.outcome === "partial" || metric.outcome === "retried")
      .reduce((sum, metric) => sum + metric.count, 0),
  };
}

export function getHotelMetricBarWidth(count: number, maxCount: number): number {
  if (count <= 0 || maxCount <= 0) return 0;
  return Math.max(4, Math.min(100, (count / maxCount) * 100));
}

export function formatHotelMetricDate(value: string, localeTag: string): string {
  const date = new Date(`${value}T12:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(localeTag, { day: "2-digit", month: "short", year: "numeric" }).format(date);
}

export function formatHotelMetricTimestamp(value: string, localeTag: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(localeTag, { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(date);
}
