"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { useI18n } from "@/i18n";
import { apiFetch } from "@/modules/shared/api";
import { BoneyardLoad, BoneyardPanel, LoadReference } from "@/modules/shared/BoneyardLoad";
import {
  HOTEL_METRIC_NAMES,
  HOTEL_PROVIDERS,
  buildHotelObservabilityPath,
  buildHotelObservabilitySummary,
  formatHotelMetricDate,
  formatHotelMetricTimestamp,
  getHotelMetricBarWidth,
  getHotelOutcomesForMetric,
  getHotelCircuitTone,
  getHotelHealthTone,
  getHotelLeaseTone,
  getHotelRunTone,
  type HotelDailyMetric,
  type HotelHealthResponse,
  type HotelProviderControlsResponse,
  type HotelProviderOutcomeDiagnostics,
  type HotelRunDiagnosticsResponse,
  type HotelSweepLeaseDiagnosticsResponse,
  type HotelMetricName,
  type HotelObservabilityFilters,
  type HotelObservabilityResponse,
  type HotelOutcome,
  type HotelProvider,
} from "@/modules/admin/hotelObservability";

type Me = { readonly is_admin: boolean };

const DEFAULT_FILTERS: HotelObservabilityFilters = {
  days: 7,
  provider: "",
  metricName: "",
  outcome: "",
};

function getMetricLabel(metricName: HotelMetricName, translate: (key: string) => string): string {
  const keyByMetric: Record<HotelMetricName, string> = {
    sweep_run: "admin.hotelObservability.sweepRun",
    alert_event: "admin.hotelObservability.alertEvent",
    hotel_delivery: "admin.hotelObservability.hotelDelivery",
  };
  return translate(keyByMetric[metricName]);
}

function getOutcomeLabel(outcome: HotelOutcome, translate: (key: string) => string): string {
  return translate(`admin.hotelObservability.${outcome}`);
}

const PROVIDER_OUTCOME_LABEL_KEYS = {
  offers_scanned: "admin.hotelObservability.providerOutcome.offersScanned",
  snapshots_created: "admin.hotelObservability.providerOutcome.snapshotsCreated",
  provider_fetch_attempted: "admin.hotelObservability.providerOutcome.providerFetchAttempted",
  provider_fetch_completed: "admin.hotelObservability.providerOutcome.providerFetchCompleted",
  provider_fetch_empty: "admin.hotelObservability.providerOutcome.providerFetchEmpty",
  provider_fetch_failed: "admin.hotelObservability.providerOutcome.providerFetchFailed",
  provider_fetch_skipped: "admin.hotelObservability.providerOutcome.providerFetchSkipped",
  provider_fetch_budget_denied: "admin.hotelObservability.providerOutcome.providerFetchBudgetDenied",
} as const;

function getProviderOutcomeLabel(outcome: string, translate: (key: string) => string): string {
  const key = PROVIDER_OUTCOME_LABEL_KEYS[outcome as keyof typeof PROVIDER_OUTCOME_LABEL_KEYS];
  return key ? translate(key) : translate("admin.hotelObservability.providerOutcome.unknown");
}

function metricTone(metric: HotelDailyMetric): "success" | "warning" | "error" | "info" {
  if (metric.outcome === "failed") return "error";
  if (metric.outcome === "partial" || metric.outcome === "retried") return "warning";
  if (metric.outcome === "completed" || metric.outcome === "delivered") return "success";
  return "info";
}

export default function HotelObservabilityPage() {
  const router = useRouter();
  const { t, localeTag } = useI18n();
  const [me, setMe] = useState<Me | null>(null);
  const [filters, setFilters] = useState<HotelObservabilityFilters>(DEFAULT_FILTERS);
  const [data, setData] = useState<HotelObservabilityResponse | null>(null);
  const [health, setHealth] = useState<HotelHealthResponse | null>(null);
  const [runDiagnostics, setRunDiagnostics] = useState<HotelRunDiagnosticsResponse | null>(null);
  const [providerControls, setProviderControls] = useState<HotelProviderControlsResponse | null>(null);
  const [leaseDiagnostics, setLeaseDiagnostics] = useState<HotelSweepLeaseDiagnosticsResponse | null>(null);
  const [providerOutcomes, setProviderOutcomes] = useState<HotelProviderOutcomeDiagnostics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [authAttempt, setAuthAttempt] = useState(0);
  const requestVersion = useRef(0);
  const mounted = useRef(true);

  const load = useCallback(async (nextFilters: HotelObservabilityFilters) => {
    const version = requestVersion.current + 1;
    requestVersion.current = version;
    setLoading(true);
    setError("");
    try {
      const [payload, healthPayload, runsPayload, controlsPayload, leasesPayload, outcomesPayload] = await Promise.all([
        apiFetch<HotelObservabilityResponse>(buildHotelObservabilityPath(nextFilters)),
        apiFetch<HotelHealthResponse>("/admin/hotels/health?window_hours=24"),
        apiFetch<HotelRunDiagnosticsResponse>("/admin/hotels/runs?limit=8"),
        apiFetch<HotelProviderControlsResponse>("/admin/hotels/provider-controls?limit=50"),
        apiFetch<HotelSweepLeaseDiagnosticsResponse>("/admin/hotels/sweep-leases?limit=20"),
        apiFetch<HotelProviderOutcomeDiagnostics>("/admin/hotels/provider-outcomes?limit=20"),
      ]);
      if (mounted.current && requestVersion.current === version) {
        setData(payload);
        setHealth(healthPayload);
        setRunDiagnostics(runsPayload);
        setProviderControls(controlsPayload);
        setLeaseDiagnostics(leasesPayload);
        setProviderOutcomes(outcomesPayload);
      }
    } catch {
      if (mounted.current && requestVersion.current === version) setError(t("admin.hotelObservability.loadError"));
    } finally {
      if (mounted.current && requestVersion.current === version) setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    let active = true;
    mounted.current = true;
    async function authenticateAndLoad() {
      try {
        const meData = await apiFetch<Me>("/auth/me");
        if (!active) return;
        setMe(meData);
        if (!meData.is_admin) {
          router.replace("/dashboard");
          return;
        }
        await load(DEFAULT_FILTERS);
      } catch {
        if (active) {
          setError(t("admin.hotelObservability.authError"));
          setLoading(false);
        }
      }
    }
    void authenticateAndLoad();
    return () => {
      active = false;
      // Invalidate any in-flight ledger/health load before a retry or locale change
      // can mark the shared mounted guard active again.
      requestVersion.current += 1;
      mounted.current = false;
    };
  }, [authAttempt, load, router, t]);

  const summary = useMemo(() => buildHotelObservabilitySummary(data?.metrics ?? []), [data]);
  const maxCount = useMemo(() => Math.max(0, ...(data?.metrics ?? []).map((metric) => metric.count)), [data]);

  function updateFilter<Key extends keyof HotelObservabilityFilters>(key: Key, value: HotelObservabilityFilters[Key]) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  function submitFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void load(filters);
  }

  function resetFilters() {
    setFilters(DEFAULT_FILTERS);
    void load(DEFAULT_FILTERS);
  }

  if (error && !loading && !me?.is_admin) {
    return (
      <main className="shell hotel-observability-page" id="main-content">
        <section className="panel panel-soft hotel-observability-auth-error" role="alert" aria-live="assertive">
          <h1>{t("admin.hotelObservability.authError")}</h1>
          <p className="panel-note">{error}</p>
          <button type="button" className="btn-primary" onClick={() => setAuthAttempt((attempt) => attempt + 1)}>{t("admin.hotelObservability.retry")}</button>
        </section>
      </main>
    );
  }

  if (!me?.is_admin) {
    return (
      <main className="shell" id="main-content">
        <BoneyardPanel name="hotel-observability-access-load" ariaLabel={t("admin.hotelObservability.loading")} />
      </main>
    );
  }

  return (
    <main className="shell hotel-observability-page" id="main-content">
      <section className="page-header hotel-observability-hero">
        <div>
          <p className="hotel-observability-kicker">{t("admin.hotelObservability.kicker")}</p>
          <h1>{t("admin.hotelObservability.title")}</h1>
          <p className="panel-note">{t("admin.hotelObservability.subtitle")}</p>
        </div>
        <div className="hotel-observability-hero-actions">
          <span className="status-pill info">{t("admin.hotelObservability.adminOnly")}</span>
          <Link href="/admin/product-health" className="btn-ghost">{t("admin.hotelObservability.productHealth")}</Link>
          <Link href="/admin" className="btn-ghost">{t("admin.hotelObservability.back")}</Link>
        </div>
      </section>

      {error ? (
        <div className="notice notice-error hotel-observability-notice" role="alert" aria-live="assertive">
          <span>{error}</span>
          <button type="button" className="btn-ghost" onClick={() => void load(filters)}>{t("admin.hotelObservability.retry")}</button>
        </div>
      ) : null}

      {health ? (
        <section className="panel panel-soft hotel-observability-health" aria-labelledby="hotel-observability-health-title">
          <div className="panel-header">
            <div>
              <h2 className="panel-title" id="hotel-observability-health-title">{t("admin.hotelObservability.healthTitle")}</h2>
              <p className="panel-subtitle">{t("admin.hotelObservability.healthSubtitle")}</p>
            </div>
            <span className={`status-pill ${getHotelHealthTone(health.status)}`}>{t(`admin.hotelObservability.health.${health.status}`)}</span>
          </div>
          <div className="hotel-observability-health-grid">
            <div><span>{t("admin.hotelObservability.healthStatus")}</span><strong>{t(`admin.hotelObservability.health.${health.status}`)}</strong></div>
            <div><span>{t("admin.hotelObservability.latestRun")}</span><strong>{health.latest_run ? t(`admin.hotelObservability.run.${health.latest_run.status}`) : t("admin.hotelObservability.noRun")}</strong></div>
            <div><span>{t("admin.hotelObservability.window")}</span><strong>{health.window_hours}h</strong></div>
            <div><span>{t("admin.hotelObservability.providersObserved")}</span><strong>{health.providers.filter((provider) => provider.runs > 0 || provider.last_run_at).length}</strong></div>
          </div>
          <p className="hotel-observability-health-note">{t("admin.hotelObservability.healthFootnote")}</p>
        </section>
      ) : null}

      {providerOutcomes ? (
        <section className="panel panel-soft hotel-observability-outcomes" aria-labelledby="hotel-observability-outcomes-title">
          <div className="panel-header">
            <div>
              <h2 className="panel-title" id="hotel-observability-outcomes-title">{t("admin.hotelObservability.outcomesTitle")}</h2>
              <p className="panel-subtitle">{t("admin.hotelObservability.outcomesSubtitle")}</p>
            </div>
            <span className="status-pill info">{t("admin.hotelObservability.outcomesSample", { count: providerOutcomes.sample_size })}</span>
          </div>
          {providerOutcomes.providers.length === 0 ? <p className="hotel-observability-runs-empty">{t("admin.hotelObservability.noOutcomes")}</p> : (
            <div className="hotel-observability-outcomes-grid">
              {providerOutcomes.providers.map((provider) => (
                <article className="hotel-observability-control-card" key={provider.provider}>
                  <div className="hotel-observability-control-heading"><strong>{provider.provider}</strong><span>{t("admin.hotelObservability.outcomeRuns", { count: provider.runs })}</span></div>
                  <div className="hotel-observability-outcome-chips">
                    {Object.entries(provider.outcomes).slice(0, 6).map(([outcome, count]) => <span className="status-pill info" key={outcome}>{getProviderOutcomeLabel(outcome, t)}: {count}</span>)}
                  </div>
                  <small>{t("admin.hotelObservability.outcomesFootnote")}</small>
                </article>
              ))}
            </div>
          )}
        </section>
      ) : null}

      {leaseDiagnostics ? (
        <section className="panel panel-soft hotel-observability-leases" aria-labelledby="hotel-observability-leases-title">
          <div className="panel-header">
            <div>
              <h2 className="panel-title" id="hotel-observability-leases-title">{t("admin.hotelObservability.leasesTitle")}</h2>
              <p className="panel-subtitle">{t("admin.hotelObservability.leasesSubtitle")}</p>
            </div>
            <span className={`status-pill ${leaseDiagnostics.attention_count > 0 ? "warning" : "success"}`}>{t("admin.hotelObservability.leaseSample", { count: leaseDiagnostics.sample_size })}</span>
          </div>
          <div className="hotel-observability-lease-summary">
            <div><span>{t("admin.hotelObservability.leaseAttention")}</span><strong>{leaseDiagnostics.attention_count}</strong></div>
            <div><span>{t("admin.hotelObservability.leaseExpired")}</span><strong>{leaseDiagnostics.counts.expired}</strong></div>
            <div><span>{t("admin.hotelObservability.leaseRunning")}</span><strong>{leaseDiagnostics.counts.running}</strong></div>
          </div>
          {leaseDiagnostics.leases.length === 0 ? <p className="hotel-observability-runs-empty">{t("admin.hotelObservability.noLeases")}</p> : (
            <div className="hotel-observability-runs-list">
              {leaseDiagnostics.leases.slice(0, 8).map((lease, index) => (
                <article className="hotel-observability-run-row" key={`${lease.updated_at}-${lease.state}-${index}`}>
                  <div className="hotel-observability-run-main"><strong>{t(`admin.hotelObservability.leaseState.${lease.state}`)}</strong><span>{formatHotelMetricTimestamp(lease.updated_at, localeTag)}</span></div>
                  <span className={`status-pill ${getHotelLeaseTone(lease.state)}`}>{lease.attention ? t("admin.hotelObservability.leaseAttentionShort") : t("admin.hotelObservability.leaseObserved")}</span>
                  <span className="hotel-observability-run-stat">{lease.attempt_count} {t("admin.hotelObservability.attempts")}</span>
                  <span className="hotel-observability-run-stat">{lease.has_provider_run ? t("admin.hotelObservability.linkedRun") : t("admin.hotelObservability.noLinkedRun")}</span>
                </article>
              ))}
            </div>
          )}
          <p className="hotel-observability-health-note">{t("admin.hotelObservability.leasesFootnote")}</p>
        </section>
      ) : null}

      {providerControls ? (
        <section className="panel panel-soft hotel-observability-controls" aria-labelledby="hotel-observability-controls-title">
          <div className="panel-header">
            <div>
              <h2 className="panel-title" id="hotel-observability-controls-title">{t("admin.hotelObservability.controlsTitle")}</h2>
              <p className="panel-subtitle">{t("admin.hotelObservability.controlsSubtitle")}</p>
            </div>
            <span className="status-pill info">{t("admin.hotelObservability.controlsReadOnly")}</span>
          </div>
          {providerControls.budgets.length === 0 && providerControls.circuits.length === 0 ? (
            <p className="hotel-observability-runs-empty">{t("admin.hotelObservability.noControls")}</p>
          ) : (
            <div className="hotel-observability-controls-grid">
              <div className="hotel-observability-control-column">
                <h3>{t("admin.hotelObservability.budgetTitle")}</h3>
                {providerControls.budgets.length === 0 ? <p className="panel-note">{t("admin.hotelObservability.noBudgets")}</p> : providerControls.budgets.map((budget) => (
                  <article className="hotel-observability-control-card" key={`${budget.provider}-${budget.operation}-${budget.window_key}`}>
                    <div className="hotel-observability-control-heading"><strong>{budget.provider}</strong><span>{t(`admin.hotelObservability.operation.${budget.operation}`)}</span></div>
                    <div className="hotel-observability-control-values"><span>{t("admin.hotelObservability.budgetRemaining")}</span><strong>{budget.units_remaining}/{budget.hard_limit}</strong></div>
                    <small>{t("admin.hotelObservability.budgetUsage", { used: budget.units_used, reserved: budget.units_reserved })}</small>
                  </article>
                ))}
              </div>
              <div className="hotel-observability-control-column">
                <h3>{t("admin.hotelObservability.circuitTitle")}</h3>
                {providerControls.circuits.length === 0 ? <p className="panel-note">{t("admin.hotelObservability.noCircuits")}</p> : providerControls.circuits.map((circuit) => (
                  <article className="hotel-observability-control-card" key={`${circuit.provider}-${circuit.operation}`}>
                    <div className="hotel-observability-control-heading"><strong>{circuit.provider}</strong><span>{t(`admin.hotelObservability.operation.${circuit.operation}`)}</span></div>
                    <div className="hotel-observability-control-values"><span>{t("admin.hotelObservability.circuitState")}</span><span className={`status-pill ${getHotelCircuitTone(circuit.status)}`}>{t(`admin.hotelObservability.circuit.${circuit.status}`)}</span></div>
                    <small>{t("admin.hotelObservability.circuitFailures", { count: circuit.consecutive_failures, threshold: circuit.failure_threshold })}{circuit.last_error_code ? ` · ${circuit.last_error_code}` : ""}</small>
                  </article>
                ))}
              </div>
            </div>
          )}
        </section>
      ) : null}

      {runDiagnostics ? (
        <section className="panel panel-soft hotel-observability-runs" aria-labelledby="hotel-observability-runs-title">
          <div className="panel-header">
            <div>
              <h2 className="panel-title" id="hotel-observability-runs-title">{t("admin.hotelObservability.runsTitle")}</h2>
              <p className="panel-subtitle">{t("admin.hotelObservability.runsSubtitle")}</p>
            </div>
            <span className="status-pill info">{t("admin.hotelObservability.runsCount", { count: runDiagnostics.runs.length })}</span>
          </div>
          {runDiagnostics.runs.length === 0 ? (
            <p className="hotel-observability-runs-empty">{t("admin.hotelObservability.noRuns")}</p>
          ) : (
            <div className="hotel-observability-runs-list">
              {runDiagnostics.runs.map((run, index) => (
                <article className="hotel-observability-run-row" key={`${run.started_at}-${run.provider}-${index}`}>
                  <div className="hotel-observability-run-main">
                    <strong>{run.provider}</strong>
                    <span>{formatHotelMetricTimestamp(run.started_at, localeTag)}</span>
                  </div>
                  <span className={`status-pill ${getHotelRunTone(run.status)}`}>{t(`admin.hotelObservability.run.${run.status}`)}</span>
                  <span className="hotel-observability-run-stat">{run.items_processed} {t("admin.hotelObservability.items")}</span>
                  <span className="hotel-observability-run-stat">{run.duration_seconds === null ? "—" : `${run.duration_seconds}s`}</span>
                  {run.has_error ? <span className="status-pill error">{t("admin.hotelObservability.hasError")}</span> : null}
                </article>
              ))}
            </div>
          )}
        </section>
      ) : null}

      <section className="panel panel-soft hotel-observability-filters" aria-labelledby="hotel-observability-filters-title">
        <div className="panel-header">
          <div>
            <h2 className="panel-title" id="hotel-observability-filters-title">{t("admin.hotelObservability.filtersTitle")}</h2>
            <p className="panel-subtitle">{t("admin.hotelObservability.filtersSubtitle")}</p>
          </div>
          <button type="button" className="btn-ghost" onClick={resetFilters}>{t("admin.hotelObservability.reset")}</button>
        </div>
        <form className="hotel-observability-filter-grid" onSubmit={submitFilters}>
          <label className="field">
            {t("admin.hotelObservability.days")}
            <select value={filters.days} onChange={(event) => updateFilter("days", Number(event.target.value))}>
              {[1, 7, 14, 31].map((days) => <option value={days} key={days}>{days}</option>)}
            </select>
          </label>
          <label className="field">
            {t("admin.hotelObservability.provider")}
            <select value={filters.provider} onChange={(event) => updateFilter("provider", event.target.value as HotelProvider | "")}>
              <option value="">{t("admin.hotelObservability.all")}</option>
              {HOTEL_PROVIDERS.map((provider) => <option value={provider} key={provider}>{provider}</option>)}
            </select>
          </label>
          <label className="field">
            {t("admin.hotelObservability.metric")}
            <select
              value={filters.metricName}
              onChange={(event) => {
                const metricName = event.target.value as HotelMetricName | "";
                setFilters((current) => ({
                  ...current,
                  metricName,
                  outcome: getHotelOutcomesForMetric(metricName).includes(current.outcome as HotelOutcome) ? current.outcome : "",
                }));
              }}
            >
              <option value="">{t("admin.hotelObservability.all")}</option>
              {HOTEL_METRIC_NAMES.map((metric) => <option value={metric} key={metric}>{getMetricLabel(metric, t)}</option>)}
            </select>
          </label>
          <label className="field">
            {t("admin.hotelObservability.outcome")}
            <select value={filters.outcome} onChange={(event) => updateFilter("outcome", event.target.value as HotelOutcome | "")}>
              <option value="">{t("admin.hotelObservability.all")}</option>
              {getHotelOutcomesForMetric(filters.metricName).map((outcome) => <option value={outcome} key={outcome}>{getOutcomeLabel(outcome, t)}</option>)}
            </select>
          </label>
          <button type="submit" className="btn-primary hotel-observability-submit">{t("admin.hotelObservability.apply")}</button>
        </form>
      </section>

      {loading ? (
        <BoneyardLoad name="hotel-observability-load" className="hotel-observability-loading" ariaLabel={t("admin.hotelObservability.loading")}>
          <div className="hotel-observability-summary-grid">
            {Array.from({ length: 4 }).map((_, index) => <LoadReference shape="card" key={`hotel-summary-load-${index}`} className="hotel-observability-load-card" />)}
          </div>
          <div className="panel panel-soft boneyard-panel">
            <LoadReference shape="chip" width="34%" height={18} />
            <LoadReference width="74%" />
            <LoadReference width="58%" />
          </div>
        </BoneyardLoad>
      ) : data ? (
        <>
          <section className="hotel-observability-summary-grid" aria-label={t("admin.hotelObservability.summaryLabel")}>
            <article className="module-card module-card-feature"><span>{t("admin.hotelObservability.totalEvents")}</span><strong>{summary.total.toLocaleString(localeTag)}</strong><small>{t("admin.hotelObservability.totalEventsDetail")}</small></article>
            <article className="module-card"><span>{t("admin.hotelObservability.daysWithData")}</span><strong>{summary.dates}</strong><small>{t("admin.hotelObservability.daysWithDataDetail")}</small></article>
            <article className="module-card"><span>{t("admin.hotelObservability.providers")}</span><strong>{summary.providers}</strong><small>{t("admin.hotelObservability.providersDetail")}</small></article>
            <article className={`module-card ${summary.attentionCount > 0 ? "hotel-observability-card-warning" : ""}`}><span>{t("admin.hotelObservability.attention")}</span><strong>{summary.attentionCount.toLocaleString(localeTag)}</strong><small>{t("admin.hotelObservability.attentionDetail")}</small></article>
          </section>

          <section className="panel panel-soft hotel-observability-table-panel" aria-labelledby="hotel-observability-table-title">
            <div className="panel-header">
              <div>
                <h2 className="panel-title" id="hotel-observability-table-title">{t("admin.hotelObservability.tableTitle")}</h2>
                <p className="panel-subtitle">{data.metrics.length ? t("admin.hotelObservability.rowsFound", { count: data.metrics.length }) : t("admin.hotelObservability.noRows")}</p>
              </div>
              <span className={`status-pill ${summary.attentionCount > 0 ? "warning" : "success"}`}>
                {summary.attentionCount > 0 ? t("admin.hotelObservability.needsAttention") : t("admin.hotelObservability.stable")}
              </span>
            </div>
            {data.metrics.length === 0 ? (
              <div className="hotel-observability-empty" role="status">
                <span className="hotel-observability-empty-mark" aria-hidden="true">∅</span>
                <strong>{t("admin.hotelObservability.emptyTitle")}</strong>
                <p>{t("admin.hotelObservability.emptyBody")}</p>
                <button type="button" className="btn-secondary btn-compact" onClick={resetFilters}>{t("admin.hotelObservability.reset")}</button>
              </div>
            ) : (
              <div className="hotel-observability-table-wrap">
                <table className="hotel-observability-table" aria-busy={loading}>
                  <caption className="sr-only">{t("admin.hotelObservability.tableCaption")}</caption>
                  <thead>
                    <tr>
                      <th scope="col">{t("admin.hotelObservability.dateColumn")}</th>
                      <th scope="col">{t("admin.hotelObservability.metricColumn")}</th>
                      <th scope="col">{t("admin.hotelObservability.providerColumn")}</th>
                      <th scope="col">{t("admin.hotelObservability.outcomeColumn")}</th>
                      <th scope="col" className="hotel-observability-count-column">{t("admin.hotelObservability.countColumn")}</th>
                      <th scope="col">{t("admin.hotelObservability.updatedColumn")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.metrics.map((metric) => (
                      <tr key={`${metric.metric_date}-${metric.metric_name}-${metric.provider}-${metric.outcome}`}>
                        <td data-label={t("admin.hotelObservability.dateColumn")}>{formatHotelMetricDate(metric.metric_date, localeTag)}</td>
                        <td data-label={t("admin.hotelObservability.metricColumn")}><strong>{getMetricLabel(metric.metric_name, t)}</strong><small>{metric.metric_name}</small></td>
                        <td data-label={t("admin.hotelObservability.providerColumn")}><span className="hotel-observability-provider">{metric.provider}</span></td>
                        <td data-label={t("admin.hotelObservability.outcomeColumn")}><span className={`status-pill ${metricTone(metric)}`}>{getOutcomeLabel(metric.outcome, t)}</span></td>
                        <td data-label={t("admin.hotelObservability.countColumn")} className="hotel-observability-count-column"><div className="hotel-observability-count"><strong>{metric.count.toLocaleString(localeTag)}</strong><span className="hotel-observability-bar" aria-hidden="true"><i style={{ width: `${getHotelMetricBarWidth(metric.count, maxCount)}%` }} /></span></div></td>
                        <td data-label={t("admin.hotelObservability.updatedColumn")}><time dateTime={metric.updated_at}>{formatHotelMetricTimestamp(metric.updated_at, localeTag)}</time></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      ) : null}

      <p className="hotel-observability-footnote">{t("admin.hotelObservability.footnote")}</p>
    </main>
  );
}
