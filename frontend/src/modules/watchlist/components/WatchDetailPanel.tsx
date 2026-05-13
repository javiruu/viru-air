import { useI18n } from "@/i18n";
import { formatCurrency, formatPercent } from "@/modules/shared/format";
import { getWatchStatusMeta } from "@/modules/shared/statusCatalog";
import { safeDateTime } from "@/modules/watchlist/presentation";
import { getFreshnessPresentation, getHistoryConfidence, hasPriceSummaryData } from "@/modules/watchlist/summary";
import type { PriceSummary, Watch, WatchDetail } from "@/modules/watchlist/types";

type WatchDetailPanelProps = {
  selectedWatch: Watch | null;
  detail: WatchDetail | null;
  summary: PriceSummary | null;
  isLoading: boolean;
  onRefreshWatch: (watchId: string) => void;
  onPauseWatch: (watchId: string) => void;
  onResumeWatch: (watchId: string) => void;
};

export function WatchDetailPanel({
  selectedWatch,
  detail,
  summary,
  isLoading,
  onRefreshWatch,
  onPauseWatch,
  onResumeWatch,
}: WatchDetailPanelProps) {
  const { t } = useI18n();

  if (!selectedWatch) {
    return (
      <section className="panel panel-soft section-gap watch-detail-panel">
        <h2 className="panel-title">{t("watchlist.detail.title")}</h2>
        <p className="panel-note">{t("watchlist.detail.empty")}</p>
      </section>
    );
  }

  const focus = detail || selectedWatch;
  const status = getWatchStatusMeta(focus.status, t);
  const hasSummaryData = Boolean(summary && hasPriceSummaryData(summary));
  const summaryData = hasSummaryData ? summary : null;
  const confidence = getHistoryConfidence(summary?.count ?? 0);
  const freshness = getFreshnessPresentation({
    t,
    lastUpdatedAt: detail?.latest_snapshot?.captured_at_utc,
    freshnessState: detail?.latest_snapshot ? "observing" : null,
  });

  return (
    <section className="panel panel-soft section-gap watch-detail-panel">
      <div className="row-between">
        <h2 className="panel-title">{t("watchlist.detail.title")}</h2>
        {isLoading ? <span className="panel-note">{t("watchlist.detail.loading")}</span> : null}
      </div>
      <div className="stack">
        <strong>{focus.origin_iata} {"→"} {focus.destination_iata}</strong>
        <span className="panel-note">{focus.travel_date_local}</span>
        <span className={`status-pill ${status.tone}`}>{status.label}</span>
        <span className="panel-note">
          {t("watchlist.detail.currentPrice")} {detail?.latest_snapshot ? formatCurrency(detail.latest_snapshot.raw_price, detail.latest_snapshot.raw_currency) : "--"}
        </span>
        <span className="panel-note">
          {t("watchlist.detail.freshness")} {freshness.fullText}
        </span>
        {detail?.latest_snapshot ? (
          <span className="panel-note">
            {t("watchlist.detail.latestSnapshot")} {safeDateTime(detail.latest_snapshot.captured_at_utc)}
          </span>
        ) : null}
      </div>
      {isLoading && !detail ? (
        <div className="history-summary history-summary--kpis" aria-label={t("watchlist.smartList.loadingAria")}>
          <div className="history-kpi"><span className="skeleton skeleton-line" /><strong className="skeleton skeleton-line" /></div>
          <div className="history-kpi"><span className="skeleton skeleton-line" /><strong className="skeleton skeleton-line" /></div>
          <div className="history-kpi"><span className="skeleton skeleton-line" /><strong className="skeleton skeleton-line" /></div>
        </div>
      ) : null}
      <div className="alert-actions">
        <button className="btn-secondary btn-compact" type="button" onClick={() => onRefreshWatch(focus.id)}>
          {t("watchlist.detail.actions.refresh")}
        </button>
        {focus.status === "paused" ? (
          <button className="btn-ghost btn-compact" type="button" onClick={() => onResumeWatch(focus.id)}>
            {t("watchlist.detail.actions.resume")}
          </button>
        ) : (
          <button className="btn-ghost btn-compact" type="button" onClick={() => onPauseWatch(focus.id)}>
            {t("watchlist.detail.actions.pause")}
          </button>
        )}
      </div>
      <div className="history-summary history-summary--kpis">
        {summaryData ? (
          <>
            {confidence.level !== "none" && confidence.titleKey && confidence.messageKey ? (
              <div className="notice notice-info notice-compact history-confidence-notice" role="status" aria-live="polite">
                <strong>{t(confidence.titleKey)}</strong>
                <p>{t(confidence.messageKey)}</p>
              </div>
            ) : null}
            <div className="history-kpi"><span className="history-kpi-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M4 16l6-6 4 4 6-8" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg></span><span>{t("watchlist.summary.latest")}</span><strong>{summaryData.latest_price == null ? "--" : formatCurrency(summaryData.latest_price, "EUR")}</strong></div>
            <div className="history-kpi"><span className="history-kpi-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M4 14l6-6 4 4 6-8" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg></span><span>{t("watchlist.summary.min")}</span><strong>{summaryData.min_price == null ? "--" : formatCurrency(summaryData.min_price, "EUR")}</strong></div>
            <div className="history-kpi"><span className="history-kpi-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M4 18l6-10 4 6 6-10" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg></span><span>{t("watchlist.summary.max")}</span><strong>{summaryData.max_price == null ? "--" : formatCurrency(summaryData.max_price, "EUR")}</strong></div>
            <div className="history-kpi"><span className="history-kpi-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 12h14M12 5v14" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg></span><span>{t("watchlist.summary.avg")}</span><strong>{summaryData.avg_price == null ? "--" : formatCurrency(summaryData.avg_price, "EUR")}</strong></div>
            <div className="history-kpi"><span className="history-kpi-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M7 15l5-6 5 6" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg></span><span>{t("watchlist.summary.delta")}</span><strong>{summaryData.delta_pct == null ? "--" : formatPercent(summaryData.delta_pct)}</strong></div>
            <div className="history-kpi"><span className="history-kpi-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M7 5v14M17 5v14M4 9h16M4 15h16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg></span><span>{t("watchlist.summary.count")}</span><strong>{summaryData.count}</strong></div>
          </>
        ) : (
          <p className="panel-note">{t("watchlist.summary.empty")}</p>
        )}
      </div>
    </section>
  );
}
