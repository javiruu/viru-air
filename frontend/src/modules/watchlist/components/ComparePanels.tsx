import { useEffect, useMemo, useState } from "react";

import { useI18n } from "@/i18n";
import { apiFetch } from "@/modules/shared/api";
import { formatCurrency, formatSignedCurrency } from "@/modules/shared/format";
import { formatDateTime } from "@/modules/watchlist/presentation";
import type { PriceCompareResponse } from "@/modules/watchlist/types";

type CompareLatest = {
  capturedAt: string;
  currency: string;
  price: number;
};

type CompareCard = {
  date: string;
  latest: CompareLatest;
  delta: number;
  min: number;
  max: number;
};

type CompareOption = {
  id: string;
  origin: string;
  destination: string;
  travelDate: string;
};

type CompareSelectionItem = {
  id: string;
  origin: string;
  destination: string;
  travelDate: string;
  latest: CompareLatest | null;
  delta: number;
  volatility: number | null;
  min: number | null;
  max: number | null;
};

type CompareBadges = {
  bestPriceId: string | null;
  freshestId: string | null;
  stableId: string | null;
};

type ComparePanelsProps = {
  compareCards: CompareCard[] | null;
  compareOptions: CompareOption[];
  compareSelection: CompareSelectionItem[];
  compareBadges: CompareBadges | null;
  compareIds: string[];
  compareNotice: string;
  onToggleCompare: (id: string) => void;
};

type CompareTab = "quick" | "multi";

function volatilityLabel(value: "low" | "medium" | "high" | "insufficient_data", t: (key: string) => string): string {
  if (value === "low") return t("watchlist.compare.volatilityLow");
  if (value === "medium") return t("watchlist.compare.volatilityMedium");
  if (value === "high") return t("watchlist.compare.volatilityHigh");
  return t("watchlist.compare.noData");
}

export function ComparePanels({
  compareCards,
  compareOptions,
  compareIds,
  compareNotice,
  onToggleCompare,
}: ComparePanelsProps) {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState<CompareTab>("quick");
  const [compareResponse, setCompareResponse] = useState<PriceCompareResponse | null>(null);
  const [isLoadingCompare, setIsLoadingCompare] = useState(false);
  const selectedCount = compareIds.length;
  const compareQuery = useMemo(() => compareIds.join(","), [compareIds]);
  const hasQuickData = Boolean(compareCards && compareCards.length > 0);

  useEffect(() => {
    if (activeTab === "quick" && !hasQuickData) {
      setActiveTab("multi");
    }
  }, [activeTab, hasQuickData]);

  const compareBadgesFromResponse = useMemo(() => {
    const watches = compareResponse?.watches ?? [];
    if (watches.length === 0) {
      return {
        bestPriceId: null as string | null,
        stableId: null as string | null,
        freshestId: null as string | null,
      };
    }

    const bestPrice = watches
      .filter((item) => item.latest_price != null || item.min_price != null)
      .reduce<typeof watches[number] | null>((acc, item) => {
        const score = item.latest_price ?? item.min_price ?? Number.POSITIVE_INFINITY;
        if (!acc) return item;
        const accScore = acc.latest_price ?? acc.min_price ?? Number.POSITIVE_INFINITY;
        return score < accScore ? item : acc;
      }, null);

    const stable = watches
      .filter((item) => item.volatility_hint !== "insufficient_data")
      .reduce<typeof watches[number] | null>((acc, item) => {
        const rank = item.volatility_hint === "low" ? 0 : item.volatility_hint === "medium" ? 1 : 2;
        if (!acc) return item;
        const accRank = acc.volatility_hint === "low" ? 0 : acc.volatility_hint === "medium" ? 1 : 2;
        return rank < accRank ? item : acc;
      }, null);

    const freshestPoint = (compareResponse?.points ?? []).reduce<{ watchId: string; ts: number } | null>((acc, point) => {
      const lastDate = point.points
        .map((item) => new Date(item.date).getTime())
        .filter((value) => Number.isFinite(value))
        .reduce((max, value) => (value > max ? value : max), Number.NEGATIVE_INFINITY);
      if (!Number.isFinite(lastDate)) return acc;
      if (!acc || lastDate > acc.ts) return { watchId: point.watch_id, ts: lastDate };
      return acc;
    }, null);

    return {
      bestPriceId: bestPrice?.watch_id ?? null,
      stableId: stable?.watch_id ?? null,
      freshestId: freshestPoint?.watchId ?? null,
    };
  }, [compareResponse?.points, compareResponse?.watches]);

  useEffect(() => {
    if (selectedCount < 2 || selectedCount > 4) {
      setCompareResponse(null);
      return;
    }
    let mounted = true;
    setIsLoadingCompare(true);
    apiFetch<PriceCompareResponse>(`/prices/compare?watch_ids=${compareQuery}`)
      .then((payload) => {
        if (!mounted) return;
        setCompareResponse(payload);
      })
      .catch(() => {
        if (!mounted) return;
        setCompareResponse(null);
      })
      .finally(() => {
        if (mounted) setIsLoadingCompare(false);
      });
    return () => {
      mounted = false;
    };
  }, [compareQuery, selectedCount]);

  return (
    <section className="panel compare-panel section-gap">
      <div className="panel-header">
        <div>
          <h2 className="panel-title">{t("watchlist.compare.title")}</h2>
          <p className="panel-subtitle">{t("watchlist.compare.subtitle")}</p>
        </div>
        <span className="compare-count">{compareIds.length}/4 {t("watchlist.compare.selected")}</span>
      </div>

      <div className="compare-tabs" role="tablist" aria-label={t("watchlist.compare.modeLabel")}>
        <button
          id="compare-tab-quick"
          type="button"
          role="tab"
          aria-selected={activeTab === "quick"}
          aria-controls="compare-tabpanel-quick"
          tabIndex={activeTab === "quick" ? 0 : -1}
          className={`compare-tab ${activeTab === "quick" ? "is-active" : ""}`}
          disabled={!hasQuickData}
          onClick={() => setActiveTab("quick")}
        >
          {t("watchlist.compare.tabs.quick")}
        </button>
        <button
          id="compare-tab-multi"
          type="button"
          role="tab"
          aria-selected={activeTab === "multi"}
          aria-controls="compare-tabpanel-multi"
          tabIndex={activeTab === "multi" ? 0 : -1}
          className={`compare-tab ${activeTab === "multi" ? "is-active" : ""}`}
          onClick={() => setActiveTab("multi")}
        >
          {t("watchlist.compare.tabs.multi")}
        </button>
      </div>

      {activeTab === "quick" ? (
        <div id="compare-tabpanel-quick" role="tabpanel" aria-labelledby="compare-tab-quick" className="compare-panel-body">
          {hasQuickData ? (
            <div className="compare-grid">
              {compareCards!.map((card) => {
                const trend = card.delta > 0 ? "up" : card.delta < 0 ? "down" : "flat";
                const deltaLabel = card.delta === 0 ? t("watchlist.compare.noChange") : formatSignedCurrency(card.delta, card.latest.currency);
                return (
                  <article key={`compare-${card.date}`} className="compare-card">
                    <div className="compare-head">
                      <strong>{card.date}</strong>
                      <span className={`trend-chip trend-${trend}`}>
                        <span className="trend-icon" aria-hidden="true">
                          <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                            <path d="M6 15l6-6 6 6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        </span>
                        {deltaLabel}
                      </span>
                    </div>
                    <div className="compare-body">
                      <div>
                        <span className="compare-label">{t("watchlist.compare.current")}</span>
                        <strong>{formatCurrency(card.latest.price, card.latest.currency)}</strong>
                      </div>
                      <div>
                        <span className="compare-label">{t("watchlist.compare.min")}</span>
                        <strong>{formatCurrency(card.min, card.latest.currency)}</strong>
                      </div>
                      <div>
                        <span className="compare-label">{t("watchlist.compare.max")}</span>
                        <strong>{formatCurrency(card.max, card.latest.currency)}</strong>
                      </div>
                    </div>
                    <div className="compare-meta">{t("watchlist.compare.lastUpdate", { value: formatDateTime(card.latest.capturedAt) })}</div>
                  </article>
                );
              })}
            </div>
          ) : (
            <p className="muted">{t("watchlist.compare.quickEmpty")}</p>
          )}
        </div>
      ) : (
        <div id="compare-tabpanel-multi" role="tabpanel" aria-labelledby="compare-tab-multi" className="compare-panel-body">
          {compareNotice ? <div className="notice notice-error notice-compact">{compareNotice}</div> : null}
          {compareResponse?.currency_mode === "mixed" ? (
            <div className="notice notice-info notice-compact">{t("watchlist.compare.mixedCurrencyWarning")}</div>
          ) : null}
          <div className="compare-selector">
            {compareOptions.map((option) => {
              const isChecked = compareIds.includes(option.id);
              return (
                <label key={option.id} className={`compare-option ${isChecked ? "active" : ""}`}>
                  <input type="checkbox" name="compare_selection" value={option.id} checked={isChecked} onChange={() => onToggleCompare(option.id)} />
                  <span className="compare-check" aria-hidden="true">
                    <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                      <path d="M5 12l4 4 10-10" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </span>
                  <span className="compare-route">
                    {option.origin} → {option.destination}
                  </span>
                  <span className="compare-date">{option.travelDate}</span>
                </label>
              );
            })}
          </div>
          {selectedCount === 0 ? (
            <p className="muted">{t("watchlist.compare.emptySelectionMessage")}</p>
          ) : selectedCount === 1 ? (
            <p className="muted">{t("watchlist.compare.oneSelectionMessage")}</p>
          ) : selectedCount > 4 ? (
            <p className="muted">{t("watchlist.compare.maxSelectionMessage")}</p>
          ) : isLoadingCompare ? (
            <p className="muted">{t("watchlist.compare.loading")}</p>
          ) : compareResponse?.watches?.length ? (
            <div className="compare-grid compare-grid--multi">
              {compareResponse.watches.map((card) => {
                const [origin = card.route, destination = ""] = card.route.split("->");
                return (
                  <article key={`multi-${card.watch_id}`} className="compare-card compare-card--multi">
                    <div className="compare-head">
                      <strong>{origin} → {destination}</strong>
                      <div className="compare-badges">
                        {compareBadgesFromResponse.bestPriceId === card.watch_id ? <span className="compare-badge">{t("watchlist.compare.bestPriceBadge")}</span> : null}
                        {compareBadgesFromResponse.stableId === card.watch_id ? <span className="compare-badge">{t("watchlist.compare.mostStableBadge")}</span> : null}
                        {compareBadgesFromResponse.freshestId === card.watch_id ? <span className="compare-badge">{t("watchlist.compare.freshestBadge")}</span> : null}
                      </div>
                    </div>
                    <div className="compare-subtitle">{card.travel_date}</div>
                    <div className="compare-body">
                      <div>
                        <span className="compare-label">{t("watchlist.compare.current")}</span>
                        <strong>{card.latest_price == null ? t("watchlist.compare.noData") : formatCurrency(card.latest_price, card.currency)}</strong>
                      </div>
                      <div>
                        <span className="compare-label">{t("watchlist.compare.minMax")}</span>
                        <strong>
                          {card.min_price != null && card.max_price != null
                            ? `${formatCurrency(card.min_price, card.currency)}-${formatCurrency(card.max_price, card.currency)}`
                            : t("watchlist.compare.noData")}
                        </strong>
                      </div>
                      <div>
                        <span className="compare-label">{t("watchlist.summary.avg")}</span>
                        <strong>{card.avg_price == null ? t("watchlist.compare.noData") : formatCurrency(card.avg_price, card.currency)}</strong>
                      </div>
                    </div>
                    <div className="compare-meta">
                      <span>{t("watchlist.compare.captures", { count: card.snapshot_count })}</span>
                      <span>{t("watchlist.compare.volatility", { value: volatilityLabel(card.volatility_hint, t) })}</span>
                    </div>
                  </article>
                );
              })}
            </div>
          ) : (
            <p className="muted">{t("watchlist.compare.noDataInRange")}</p>
          )}
        </div>
      )}
    </section>
  );
}
