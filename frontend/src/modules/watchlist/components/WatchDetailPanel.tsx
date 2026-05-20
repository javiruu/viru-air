import { useI18n } from "@/i18n";
import { formatCurrency, formatPercent } from "@/modules/shared/format";
import { getWatchStatusMeta } from "@/modules/shared/statusCatalog";
import { DoorToDoorWatchlistSuggestion } from "@/modules/door-to-door/components/DoorToDoorWatchlistSuggestion";
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
  const { t, localeTag } = useI18n();

  if (!selectedWatch) {
    return (
      <section className="panel panel-soft section-gap watch-detail-panel">
        <header className="watch-detail-header">
          <h2 className="panel-title">{t("watchlist.detail.title")}</h2>
        </header>
        <div className="watch-detail-empty-state">
          <strong>{t("watchlist.detail.emptyTitle")}</strong>
          <p className="panel-note">{t("watchlist.detail.empty")}</p>
        </div>
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
    locale: localeTag,
    lastUpdatedAt: detail?.latest_snapshot?.captured_at_utc,
    freshnessState: detail?.latest_snapshot ? "observing" : null,
  });

  const latestSnapshot = detail?.latest_snapshot ?? null;
  const currency = latestSnapshot?.raw_currency ?? "EUR";
  const hasSnapshotPrice = latestSnapshot && latestSnapshot.raw_price != null && latestSnapshot.raw_price >= 0;
  const currentPriceValue = hasSnapshotPrice ? formatCurrency(latestSnapshot.raw_price, currency, localeTag) : "--";
  const currentPriceStatus = !latestSnapshot ? "no-snapshot" : !hasSnapshotPrice ? "pending-capture" : "ok";
  const minPriceValue = summaryData?.min_price == null ? "--" : formatCurrency(summaryData.min_price, currency, localeTag);
  const deltaFromMin = latestSnapshot && summaryData?.min_price != null
    ? latestSnapshot.raw_price - summaryData.min_price
    : null;
  const deltaFromMinValue = deltaFromMin == null ? "--" : formatCurrency(deltaFromMin, currency, localeTag);

  const trendText = summaryData?.delta_pct == null
    ? t("watchlist.detail.operational.trendUnknown")
    : summaryData.delta_pct > 0
      ? t("watchlist.detail.operational.trendUp")
      : summaryData.delta_pct < 0
        ? t("watchlist.detail.operational.trendDown")
        : t("watchlist.detail.operational.trendFlat");

  const interpretationText = confidence.level === "sufficient"
    ? t("watchlist.detail.interpretation.sufficient")
    : confidence.level === "limited"
      ? t("watchlist.detail.interpretation.limited")
      : t("watchlist.detail.interpretation.initial");

  return (
    <section className="panel panel-soft section-gap watch-detail-panel">
      <header className="watch-detail-header">
        <div>
          <h2 className="panel-title">{t("watchlist.detail.title")}</h2>
        </div>
        {isLoading ? <span className="panel-note">{t("watchlist.detail.loading")}</span> : null}
      </header>

      <div className="watch-detail-hero">
        <div className="watch-detail-route">
          <strong>{focus.origin_iata} {"→"} {focus.destination_iata}</strong>
          <span className="panel-note">{focus.travel_date_local}</span>
        </div>
        <span className={`status-pill ${status.tone}`}>{status.label}</span>
      </div>

      <div className="watch-detail-block">
        <h3 className="watch-detail-block-title">{t("watchlist.detail.mainReadingTitle")}</h3>
        <div className="watch-detail-metrics">
          <div className="watch-detail-metric">
            <span>{t("watchlist.detail.currentPriceLabel")}</span>
            <strong>
              {currentPriceValue}
              {currentPriceStatus !== "ok" ? (
                <span className="watch-detail-price-status">
                  {currentPriceStatus === "no-snapshot"
                    ? t("watchlist.noDataLabel")
                    : t("watchlist.noDataDetail")}
                </span>
              ) : null}
            </strong>
          </div>
          <div className="watch-detail-metric">
            <span>{t("watchlist.detail.bestPriceLabel")}</span>
            <strong>{minPriceValue}</strong>
          </div>
          <div className="watch-detail-metric">
            <span>{t("watchlist.detail.deltaFromMinLabel")}</span>
            <strong>{deltaFromMinValue}</strong>
          </div>
          <div className="watch-detail-metric">
            <span>{t("watchlist.detail.freshnessLabel")}</span>
            <strong>{freshness.fullText}</strong>
          </div>
        </div>
      </div>

      <div className="watch-detail-block">
        <h3 className="watch-detail-block-title">{t("watchlist.detail.operational.title")}</h3>
        <div className="watch-detail-operational">
          <span>{t("watchlist.detail.latestSnapshot")} {latestSnapshot ? safeDateTime(latestSnapshot.captured_at_utc, localeTag) : "--"}</span>
          <span>{t("watchlist.summary.count")} {summaryData ? summaryData.count : "--"}</span>
          <span>{t("watchlist.summary.delta")} {summaryData?.delta_pct == null ? "--" : formatPercent(summaryData.delta_pct, localeTag)}</span>
          <span>{t("watchlist.detail.operational.trend")} {trendText}</span>
        </div>
      </div>

      {summaryData ? (
        <div className="notice notice-info notice-compact history-confidence-notice" role="status" aria-live="polite">
          <strong>{confidence.titleKey ? t(confidence.titleKey) : t("watchlist.detail.interpretation.title")}</strong>
          <p>{confidence.messageKey ? t(confidence.messageKey) : interpretationText}</p>
        </div>
      ) : (
        <p className="panel-note">{t("watchlist.summary.empty")}</p>
      )}

      {isLoading && !detail ? (
        <div className="history-summary history-summary--kpis" aria-label={t("watchlist.smartList.loadingAria")}>
          <div className="history-kpi"><span className="skeleton skeleton-line" /><strong className="skeleton skeleton-line" /></div>
          <div className="history-kpi"><span className="skeleton skeleton-line" /><strong className="skeleton skeleton-line" /></div>
          <div className="history-kpi"><span className="skeleton skeleton-line" /><strong className="skeleton skeleton-line" /></div>
        </div>
      ) : null}

      <DoorToDoorWatchlistSuggestion watch={focus} />

      <div className="alert-actions watch-detail-actions">
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


    </section>
  );
}
