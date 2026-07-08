import { useI18n } from "@/i18n";
import { formatCurrency } from "@/modules/shared/format";
import { safeDateTime } from "@/modules/watchlist/presentation";
import type { WatchCombinationGroup } from "@/modules/watchlist/types";

type WatchlistCombinationPanelProps = {
  groups: WatchCombinationGroup[];
  selectedWatchId: string;
  onSelectWatchById: (watchId: string) => void;
};

export function WatchlistCombinationPanel({
  groups,
  selectedWatchId,
  onSelectWatchById,
}: WatchlistCombinationPanelProps) {
  const { t, localeTag } = useI18n();

  if (groups.length === 0) return null;

  return (
    <section className="panel panel-soft section-gap watch-combo-panel" aria-label={t("watchlist.combinations.ariaLabel")}>
      <div className="panel-header watch-combo-header">
        <div>
          <span className="panel-kicker">{t("watchlist.combinations.kicker")}</span>
          <h2 className="panel-title">{t("watchlist.combinations.title")}</h2>
        </div>
        <span className="watch-combo-count tabular-nums">
          {t("watchlist.combinations.count", { count: groups.length })}
        </span>
      </div>

      <div className="watch-combo-grid">
        {groups.map((group) => {
          const selectedInGroup = group.legs.some((leg) => leg.id === selectedWatchId);
          const totalLabel =
            group.totalLatestPrice == null
              ? t("watchlist.combinations.totalPending")
              : formatCurrency(group.totalLatestPrice, group.currency, localeTag);

          return (
            <article key={group.groupId} className={`watch-combo-card ${selectedInGroup ? "is-selected" : ""}`}>
              <div className="watch-combo-card-head">
                <strong>{t("watchlist.combinations.roundTrip")}</strong>
                <span className="watch-combo-total tabular-nums">{totalLabel}</span>
              </div>
              <div className="watch-combo-legs">
                {group.legs.map((leg, index) => (
                  <button
                    key={leg.id}
                    type="button"
                    className={`watch-combo-leg ${leg.id === selectedWatchId ? "is-active" : ""}`}
                    onClick={() => onSelectWatchById(leg.id)}
                  >
                    <span className="watch-combo-leg-label">
                      {index === 0 ? t("watchlist.combinations.outbound") : t("watchlist.combinations.return")}
                    </span>
                    <strong>{leg.origin}{" → "}{leg.destination}</strong>
                    <span className="tabular-nums">{leg.travelDate}</span>
                    <span className="watch-combo-leg-price tabular-nums">
                      {leg.latestPrice == null ? "--" : formatCurrency(leg.latestPrice, leg.latestCurrency, localeTag)}
                    </span>
                    {leg.latestCapturedAt ? (
                      <small>{safeDateTime(leg.latestCapturedAt, localeTag)}</small>
                    ) : null}
                  </button>
                ))}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
