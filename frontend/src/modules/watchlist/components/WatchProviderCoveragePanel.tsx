import { useI18n } from "@/i18n";
import { safeDateTime } from "@/modules/watchlist/presentation";
import type { WatchProviderCoverageItem } from "@/modules/watchlist/providerCoverage";

type WatchProviderCoveragePanelProps = {
  coverage: WatchProviderCoverageItem[];
};

export function WatchProviderCoveragePanel({ coverage }: WatchProviderCoveragePanelProps) {
  const { t, localeTag } = useI18n();
  const observedCount = coverage.filter((provider) => provider.status === "observed").length;
  const totalCount = coverage.length;

  return (
    <section className="watch-provider-panel section-gap" aria-label={t("watchlist.providerCoverage.ariaLabel")}>
      <div className="watch-provider-copy">
        <span className="watch-provider-kicker">{t("watchlist.providerCoverage.kicker")}</span>
        <strong>{t("watchlist.providerCoverage.heading")}</strong>
        <p>
          {observedCount > 0
            ? t("watchlist.providerCoverage.summary", { observed: observedCount, total: totalCount })
            : t("watchlist.providerCoverage.pendingSummary")}
        </p>
      </div>
      <div className="watch-provider-rail" role="list">
        {coverage.map((provider) => (
          <div
            key={provider.id}
            className={`watch-provider-item watch-provider-item--${provider.status}`}
            role="listitem"
          >
            <span className="watch-provider-dot" aria-hidden="true" />
            <span className="watch-provider-name">{provider.label}</span>
            <span className="watch-provider-state">
              {provider.status === "observed"
                ? t("watchlist.providerCoverage.observed", { count: provider.observedCount })
                : t("watchlist.providerCoverage.ready")}
            </span>
            <span className="watch-provider-latest tabular-nums">
              {provider.latestCapturedAt
                ? t("watchlist.providerCoverage.latest", { value: safeDateTime(provider.latestCapturedAt, localeTag) })
                : t("watchlist.providerCoverage.readyDetail")}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
