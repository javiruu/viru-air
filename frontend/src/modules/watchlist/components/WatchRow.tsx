import { useI18n } from "@/i18n";
import { formatCurrency, formatSignedCurrency } from "@/modules/shared/format";
import { resolveProviderPresentation } from "@/modules/shared/providerPresentation";
import { getWatchStatusMeta } from "@/modules/shared/statusCatalog";
import { CommunityHubButton } from "@/modules/watchlist/components/CommunityHubButton";
import { safeDateTime } from "@/modules/watchlist/presentation";
import { getFreshnessPresentation } from "@/modules/watchlist/summary";
import type { Watch } from "@/modules/watchlist/types";

export type WatchMetaEntry = {
  readonly latest: {
    readonly capturedAt: string;
    readonly price: number;
    readonly currency: string;
    readonly provider: string | null;
  } | null;
  readonly previous: {
    readonly price: number;
    readonly currency: string;
  } | null;
  readonly min: number | null;
  readonly max: number | null;
};

type WatchRowProps = {
  readonly watch: Watch;
  readonly meta: WatchMetaEntry | undefined;
  readonly isSelected: boolean;
  readonly isBulkSelected: boolean;
  readonly onSelect: (watch: Watch) => void;
  readonly onToggleBulkSelected: (watchId: string, selected: boolean) => void;
  readonly onOpenCommunity: (
    watch: Watch,
    trigger: HTMLButtonElement,
  ) => void;
  readonly onPause: (watchId: string) => void;
  readonly onResume: (watchId: string) => void;
  readonly onDelete: (watchId: string) => void;
};

export function WatchRow({
  watch,
  meta,
  isSelected,
  isBulkSelected,
  onSelect,
  onToggleBulkSelected,
  onOpenCommunity,
  onPause,
  onResume,
  onDelete,
}: WatchRowProps) {
  const { t, localeTag } = useI18n();
  const watchStatus = getWatchStatusMeta(watch.status, t);
  const canManageTracking =
    !watch.community_pricing.eligible && watch.status !== "purchased";
  const trend =
    !meta?.latest || !meta.previous
      ? "flat"
      : meta.latest.price > meta.previous.price
        ? "up"
        : meta.latest.price < meta.previous.price
          ? "down"
          : "flat";
  const deltaLabel =
    !meta?.latest || !meta.previous
      ? t("watchlist.smartList.noTrend")
      : formatSignedCurrency(
          meta.latest.price - meta.previous.price,
          meta.latest.currency,
          localeTag,
        );
  const routeHealthLabel =
    trend === "up"
      ? t("watchlist.smartList.trendUp")
      : trend === "down"
        ? t("watchlist.smartList.trendDown")
        : t("watchlist.smartList.trendStable");
  const freshness = getFreshnessPresentation({
    t,
    locale: localeTag,
    lastUpdatedAt: meta?.latest?.capturedAt,
    freshnessState: meta?.latest ? "observing" : null,
  });
  const priceDropAmount =
    trend === "down" && meta?.latest && meta.previous
      ? meta.previous.price - meta.latest.price
      : null;
  const priceDropPercent =
    priceDropAmount !== null && meta?.previous && meta.previous.price > 0
      ? Math.round((priceDropAmount / meta.previous.price) * 100)
      : null;
  const percentDelta =
    meta?.previous && meta.previous.price > 0 && meta.latest
      ? Math.round(
          ((meta.latest.price - meta.previous.price) / meta.previous.price) *
            100,
        )
      : null;
  const trendPercentLabel =
    percentDelta !== null && percentDelta !== 0
      ? t("watchlist.smartList.trendPercentDelta", {
          value: `${percentDelta > 0 ? "+" : ""}${percentDelta}`,
        })
      : "";
  const hasMeaningfulDrop =
    priceDropAmount !== null &&
    priceDropPercent !== null &&
    priceDropPercent > 0;
  const isBestPrice = Boolean(
    meta?.latest &&
      meta.min !== null &&
      meta.latest.price <= meta.min &&
      meta.max !== null &&
      meta.max > meta.min,
  );
  const provider = resolveProviderPresentation(
    meta?.latest?.provider,
    t("watchlist.providerCoverage.unknown"),
  );

  return (
    <article
      className={`list-row watch-row ${isSelected ? "watch-selected" : ""}`}
      data-selected={isSelected ? "true" : "false"}
    >
      <button
        className="watch-row-select-surface"
        type="button"
        aria-pressed={isSelected}
        aria-label={t("watchlist.smartList.selectRowAria", {
          origin: watch.origin_iata,
          destination: watch.destination_iata,
          date: watch.travel_date_local,
        })}
        onClick={() => onSelect(watch)}
      />
      <CommunityHubButton watch={watch} onOpen={onOpenCommunity} />
      <div className="watch-details">
        <div className="watch-route">
          <input
            type="checkbox"
            className="watch-bulk-checkbox"
            checked={isBulkSelected}
            onClick={(event) => event.stopPropagation()}
            onChange={(event) =>
              onToggleBulkSelected(watch.id, event.target.checked)
            }
            aria-label={t("watchlist.smartList.selectCheckboxAria", {
              origin: watch.origin_iata,
              destination: watch.destination_iata,
            })}
          />
          <strong className="watch-route-code">
            {watch.origin_iata} → {watch.destination_iata}
          </strong>
          <span className="watch-date tabular-nums">
            {watch.travel_date_local}
          </span>
          <span className={`status-pill ${watchStatus.tone}`}>
            {watchStatus.label}
          </span>
          <strong className="watch-inline-price tabular-nums">
            {meta?.latest
              ? formatCurrency(
                  meta.latest.price,
                  meta.latest.currency,
                  localeTag,
                )
              : "--"}
          </strong>
        </div>
        <div className="watch-meta">
          <span
            className={`status-pill ${
              trend === "up"
                ? "error"
                : trend === "down"
                  ? "success"
                  : "warning"
            }`}
          >
            {routeHealthLabel}
          </span>
          <span className="watch-meta-chip tabular-nums">
            {t("watchlist.detail.latestSnapshot")}{" "}
            {safeDateTime(meta?.latest?.capturedAt, localeTag)}
          </span>
          <span className="watch-meta-chip watch-meta-chip--freshness tabular-nums">
            {t("watchlist.detail.freshness")} {freshness.label}
          </span>
          <span className={`watch-provider-chip watch-provider-chip--${provider.id}`}>
            {t("watchlist.providerCoverage.rowSource", {
              provider: provider.label,
            })}
          </span>
          <span className="watch-note">{freshness.detail}</span>
          <span className="watch-note">
            {t("watchlist.smartList.priceDisclaimer")}
          </span>
        </div>
      </div>
      <div className="watch-price-area">
        <div className="watch-price tabular-nums">
          <span className="watch-price-caption">
            {t("watchlist.smartList.currentPrice")}
          </span>
          <span className={`trend-chip trend-${trend}`}>
            <span className="trend-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24">
                <path
                  d="M6 15l6-6 6 6"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </span>
            {deltaLabel}
            {trendPercentLabel ? (
              <span
                className="trend-chip-percent"
                aria-label={trendPercentLabel}
              >
                {trendPercentLabel}
              </span>
            ) : null}
          </span>
        </div>
        {hasMeaningfulDrop || isBestPrice ? (
          <div className="watch-price-badges">
            {hasMeaningfulDrop &&
            priceDropAmount !== null &&
            priceDropPercent !== null ? (
              <span className="price-drop-badge tabular-nums">
                {formatCurrency(
                  priceDropAmount,
                  meta?.latest?.currency ?? "EUR",
                  localeTag,
                )}{" "}
                ({priceDropPercent}%)
              </span>
            ) : null}
            {isBestPrice ? (
              <span className="best-price-badge">
                {t("watchlist.compare.bestPriceBadge")}
              </span>
            ) : null}
          </div>
        ) : null}
        <div className="watch-row-actions">
          <div className="alert-actions">
            {canManageTracking && watch.status === "paused" ? (
              <button
                className="btn-ghost btn-compact"
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  onResume(watch.id);
                }}
              >
                {t("watchlist.smartList.resume")}
              </button>
            ) : canManageTracking ? (
              <button
                className="btn-ghost btn-compact"
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  onPause(watch.id);
                }}
              >
                {t("watchlist.smartList.pause")}
              </button>
            ) : null}
            <button
              className="btn-danger btn-compact"
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                onDelete(watch.id);
              }}
            >
              {t("watchlist.smartList.delete")}
            </button>
          </div>
        </div>
      </div>
    </article>
  );
}
