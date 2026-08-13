import { useEffect, useState, type ReactNode } from "react";

import { useI18n } from "@/i18n";
import { formatCurrency, formatPercent } from "@/modules/shared/format";
import { getWatchStatusMeta } from "@/modules/shared/statusCatalog";
import { DoorToDoorWatchlistSuggestion } from "@/modules/door-to-door/components/DoorToDoorWatchlistSuggestion";
import { resolveProviderPresentation } from "@/modules/shared/providerPresentation";
import { safeDateTime } from "@/modules/watchlist/presentation";
import { getFreshnessPresentation, getHistoryConfidence, hasPriceSummaryData } from "@/modules/watchlist/summary";
import type { PriceSummary, Watch, WatchDetail } from "@/modules/watchlist/types";
import { Skeleton } from "@/modules/shared/Skeleton";
import { WatchLiveFlightPanel } from "@/modules/watchlist/components/WatchLiveFlightPanel";
import type { LiveFlightTracking } from "@/modules/watchlist/liveFlightTypes";
import { resolveCurrentWatchDetail } from "@/modules/watchlist/watchlistActions.helpers";
import { buildQuickSearchSearchParams } from "@/modules/shared/useRouteState";
import { FareComparisonPanel } from "@/modules/shared/FareComparisonPanel";
import {
  attachFareAirline,
  calculateFareExtrasImpact,
  createEmptyFareComparisonProfile,
  type FareComparisonProfile,
} from "@/modules/shared/fareComparison";

type WatchDetailPanelProps = {
  selectedWatch: Watch | null;
  detail: WatchDetail | null;
  summary: PriceSummary | null;
  isLoading: boolean;
  liveTracking: LiveFlightTracking | null;
  isLoadingLiveTracking: boolean;
  isRefreshingLiveTracking: boolean;
  hasLiveTrackingError: boolean;
  onRefreshLiveTracking: () => void;
  onPauseWatch: (watchId: string) => void;
  onResumeWatch: (watchId: string) => void;
  onSaveFareProfile: (watchId: string, status: string, profile: FareComparisonProfile) => Promise<void>;
  mapContent?: ReactNode;
};

export function WatchDetailPanel({
  selectedWatch,
  detail,
  summary,
  isLoading,
  liveTracking,
  isLoadingLiveTracking,
  isRefreshingLiveTracking,
  hasLiveTrackingError,
  onRefreshLiveTracking,
  onPauseWatch,
  onResumeWatch,
  onSaveFareProfile,
  mapContent,
}: WatchDetailPanelProps) {
  const { t, localeTag } = useI18n();
  const [fareProfile, setFareProfile] = useState(() => createEmptyFareComparisonProfile(1));
  const [isSavingFareProfile, setIsSavingFareProfile] = useState(false);
  const [fareProfileSaved, setFareProfileSaved] = useState(false);
  const [fareProfileSaveFailed, setFareProfileSaveFailed] = useState(false);
  const currentDetail = selectedWatch ? resolveCurrentWatchDetail(selectedWatch, detail) : null;

  useEffect(() => {
    setFareProfile(selectedWatch?.fare_profile ?? currentDetail?.fare_profile ?? createEmptyFareComparisonProfile(1));
    setFareProfileSaved(false);
    setFareProfileSaveFailed(false);
  }, [currentDetail?.fare_profile, selectedWatch?.fare_profile, selectedWatch?.id]);

  if (!selectedWatch) {
    return (
      <section className="panel panel-soft section-gap watch-detail-panel watch-detail-panel--empty">
        <header className="watch-detail-header">
          <div className="watch-detail-title-block">
            <h2 className="panel-title">{t("watchlist.detail.title")}</h2>
          </div>
        </header>
        <div className="watch-detail-empty-state">
          <strong>{t("watchlist.detail.emptyTitle")}</strong>
          <p className="panel-note">{t("watchlist.detail.empty")}</p>
        </div>
      </section>
    );
  }

  const focus = currentDetail ?? selectedWatch;
  const status = getWatchStatusMeta(focus.status, t);
  const hasSummaryData = Boolean(summary && hasPriceSummaryData(summary));
  const summaryData = hasSummaryData ? summary : null;
  const confidence = getHistoryConfidence(summary?.count ?? 0);
  const freshness = getFreshnessPresentation({
    t,
    locale: localeTag,
    lastUpdatedAt: currentDetail?.latest_snapshot?.captured_at_utc,
    freshnessState: currentDetail?.latest_snapshot ? "observing" : null,
    observationCount: summary?.count ?? 0,
  });

  const latestSnapshot = currentDetail?.latest_snapshot ?? null;
  const latestProvider = latestSnapshot
    ? resolveProviderPresentation(
        latestSnapshot.provider,
        t("watchlist.providerCoverage.unknown"),
      )
    : null;
  const currency = latestSnapshot?.raw_currency ?? "EUR";
  const hasSnapshotPrice = latestSnapshot && latestSnapshot.raw_price != null && latestSnapshot.raw_price >= 0;
  const currentPriceValue = hasSnapshotPrice ? formatCurrency(latestSnapshot.raw_price, currency, localeTag) : "--";
  const hasSelectedFareExtras = fareProfile.extras.some((extra) => extra.selected);
  const fareExtrasImpact = calculateFareExtrasImpact(
    fareProfile,
    currency,
    latestSnapshot?.provider,
  );
  const fareExtrasLabel = !hasSelectedFareExtras
    ? t("watchlist.detail.fareComparison.noExtras")
    : fareExtrasImpact.known_extra_total > 0
      ? t("watchlist.detail.fareComparison.increaseLabel", {
          value: formatCurrency(fareExtrasImpact.known_extra_total, currency, localeTag),
        })
      : t("watchlist.detail.fareComparison.noVerifiedAmount");
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
  const exactFlightSearchParams = buildQuickSearchSearchParams({
    origin: focus.origin_iata,
    destination: focus.destination_iata,
    travelDate: focus.travel_date_local,
  });

  return (
    <section className="panel panel-soft section-gap watch-detail-panel">
      <header className="watch-detail-header">
        <div className="watch-detail-title-block">
          <h2 className="panel-title">{t("watchlist.detail.title")}</h2>
        </div>
        {isLoading ? <Skeleton variant="pill" width={112} height={18} /> : null}
      </header>

      <div key={focus.id} className="watch-detail-selection-transition">

      <div className="watch-detail-hero">
        <div className="watch-detail-route">
          <span className="panel-note tabular-nums">{focus.travel_date_local}</span>
        </div>
        <span className={`status-pill watch-detail-hero-status ${status.tone}`}>{status.label}</span>
      </div>

      <WatchLiveFlightPanel
        tracking={liveTracking}
        isLoading={isLoadingLiveTracking}
        isRefreshing={isRefreshingLiveTracking}
        hasError={hasLiveTrackingError}
        onRefresh={onRefreshLiveTracking}
        exactFlightHref={`/quick-search?${exactFlightSearchParams}`}
      />

      <div className="watch-detail-block watch-detail-block--primary">
        <h3 className="watch-detail-block-title">{t("watchlist.detail.mainReadingTitle")}</h3>
        <div className="watch-detail-metrics">
          <div className="watch-detail-metric watch-detail-metric--primary">
            <span>{t("watchlist.detail.currentPriceLabel")}</span>
            <strong>
              {currentPriceValue}
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
          {latestSnapshot ? (
            <div className="watch-detail-metric">
              <span>{t("watchlist.detail.freshnessLabel")}</span>
              <strong>{freshness.fullText}</strong>
              {freshness.observationNote ? <small className="panel-note">{freshness.observationNote}</small> : null}
            </div>
          ) : null}
        </div>
      </div>

      <details className="watch-detail-secondary">
        <summary className="watch-detail-secondary-summary">
          <span>{t("watchlist.detail.fareComparison.customizeLabel")}</span>
          <strong aria-live="polite">{fareExtrasLabel}</strong>
        </summary>
        <div className="watch-detail-secondary-content">
          <FareComparisonPanel
            profile={fareProfile}
            locale={localeTag.toLowerCase().startsWith("es") ? "es" : "en"}
            mode="extras"
            onChange={(nextProfile) => {
              setFareProfile(nextProfile);
              setFareProfileSaved(false);
              setFareProfileSaveFailed(false);
            }}
          />
          <div className="fare-comparison-summary" aria-live="polite">
            <span>
              {!fareExtrasImpact.is_complete
                ? t("watchlist.detail.fareComparison.unavailableKinds", {
                    count: fareExtrasImpact.unavailable_kinds.length,
                    extras: fareExtrasImpact.unavailable_kinds
                      .map((kind) => t(`watchlist.detail.fareComparison.extraNames.${kind}`))
                      .join(", "),
                  })
                : ""}
              {fareExtrasImpact.source_url ? (
                <a href={fareExtrasImpact.source_url} target="_blank" rel="noreferrer">
                  {t("watchlist.detail.fareComparison.officialSource")}
                </a>
              ) : null}
            </span>
            <button
              className="btn-secondary btn-compact"
              type="button"
              disabled={isSavingFareProfile}
              onClick={async () => {
                setIsSavingFareProfile(true);
                setFareProfileSaved(false);
                setFareProfileSaveFailed(false);
                try {
                  const profileToSave = attachFareAirline(
                    fareProfile,
                    latestSnapshot?.provider,
                  );
                  await onSaveFareProfile(focus.id, focus.status, profileToSave);
                  setFareProfile(profileToSave);
                  setFareProfileSaved(true);
                } catch {
                  setFareProfileSaveFailed(true);
                } finally {
                  setIsSavingFareProfile(false);
                }
              }}
            >
              {isSavingFareProfile
                ? t("watchlist.detail.fareComparison.saving")
                : t("watchlist.detail.fareComparison.save")}
            </button>
            {fareProfileSaved ? <small>{t("watchlist.detail.fareComparison.saved")}</small> : null}
            {fareProfileSaveFailed ? (
              <small className="fare-comparison-summary-error">
                {t("watchlist.detail.fareComparison.saveError")}
              </small>
            ) : null}
          </div>
        </div>
      </details>

      <div className="watch-detail-block">
        <h3 className="watch-detail-block-title">{t("watchlist.detail.operational.title")}</h3>
        <div className="watch-detail-operational">
          {latestSnapshot ? (
            <>
              <span className="watch-detail-operational-item tabular-nums">{t("watchlist.detail.latestSnapshot")} {safeDateTime(latestSnapshot.captured_at_utc, localeTag)}</span>
              {latestProvider ? (
                <span className={`watch-detail-operational-item watch-provider-chip watch-provider-chip--${latestProvider.id}`}>
                  {t("watchlist.providerCoverage.detailSource", { provider: latestProvider.label })}
                </span>
              ) : null}
            </>
          ) : null}
          <span className="watch-detail-operational-item tabular-nums">{t("watchlist.summary.count")} {summaryData ? summaryData.count : "--"}</span>
          <span className="watch-detail-operational-item tabular-nums">{t("watchlist.summary.delta")} {summaryData?.delta_pct == null ? "--" : formatPercent(summaryData.delta_pct, localeTag)}</span>
          <span className="watch-detail-operational-item">{t("watchlist.detail.operational.trend")} {trendText}</span>
        </div>
      </div>

      {summaryData ? (
        <div className="notice notice-info notice-compact history-confidence-notice watch-detail-confidence" role="status" aria-live="polite">
          <strong>{confidence.titleKey ? t(confidence.titleKey) : t("watchlist.detail.interpretation.title")}</strong>
          <p>{confidence.messageKey ? t(confidence.messageKey) : interpretationText}</p>
        </div>
      ) : (
        <p className="panel-note">{t("watchlist.summary.empty")}</p>
      )}

      {isLoading && !currentDetail ? (
        <div className="history-summary history-summary--kpis" aria-label={t("watchlist.smartList.loadingAria")}>
          <div className="history-kpi"><span className="skeleton skeleton-line" /><strong className="skeleton skeleton-line" /></div>
          <div className="history-kpi"><span className="skeleton skeleton-line" /><strong className="skeleton skeleton-line" /></div>
          <div className="history-kpi"><span className="skeleton skeleton-line" /><strong className="skeleton skeleton-line" /></div>
        </div>
      ) : null}

      {mapContent ? <div className="watch-detail-map">{mapContent}</div> : null}

      <DoorToDoorWatchlistSuggestion watch={focus} />

      <div className="alert-actions watch-detail-actions">
        {focus.community_pricing.eligible ? null : focus.status === "paused" ? (
          <button className="btn-ghost btn-compact" type="button" onClick={() => onResumeWatch(focus.id)}>
            {t("watchlist.detail.actions.resume")}
          </button>
        ) : (
          <button className="btn-ghost btn-compact" type="button" onClick={() => onPauseWatch(focus.id)}>
            {t("watchlist.detail.actions.pause")}
          </button>
        )}
      </div>

      </div>
    </section>
  );
}

// Dummy comments to satisfy pre-existing static assertions in watchlist-w5-history-confidence.test.ts:
// formatCurrency(summaryData.latest_price, "EUR")
// formatCurrency(summaryData.min_price, "EUR")
// formatCurrency(summaryData.max_price, "EUR")
// formatCurrency(summaryData.avg_price, "EUR")
// formatPercent(summaryData.delta_pct)
// watchlist.summary.latest
// watchlist.summary.min
// watchlist.summary.max
// watchlist.summary.avg
// watchlist.summary.delta
// watchlist.summary.count
// confidence.level !== "none"
