"use client";

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

type ComparePanelsProps = {
  compareCards: CompareCard[] | null;
  compareOptions: CompareOption[];
  compareIds: string[];
  compareNotice: string;
  onToggleCompare: (id: string) => void;
};

type CompareTab = "quick" | "multi";

type CompareChartPoint = {
  date: string;
  x: number;
  y: number;
  price: number;
  currency: string;
};

type CompareChartSerie = {
  watchId: string;
  label: string;
  color: string;
  path: string;
  points: CompareChartPoint[];
};

const CHART_WIDTH = 600;
const CHART_HEIGHT = 200;
const CHART_PAD = { left: 14, right: 14, top: 15, bottom: 25 };
const CHART_COLORS = [
  "var(--history-accent-origin)",
  "var(--history-accent-destination)",
  "var(--history-accent-date)",
  "var(--accent)",
];

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
  const { t, localeTag } = useI18n();
  const [activeTab, setActiveTab] = useState<CompareTab>("quick");
  const [compareResponse, setCompareResponse] = useState<PriceCompareResponse | null>(null);
  const [isLoadingCompare, setIsLoadingCompare] = useState(false);
  const [hasCompareError, setHasCompareError] = useState(false);

  const [hoveredWatchId, setHoveredWatchId] = useState<string | null>(null);
  const [hoveredPoint, setHoveredPoint] = useState<(CompareChartPoint & { label: string; color: string }) | null>(null);

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

  const compareChartSeries = useMemo(() => {
    const watches = compareResponse?.watches ?? [];
    const pointBlocks = compareResponse?.points ?? [];
    if (watches.length === 0 || pointBlocks.length === 0) {
      return { hasData: false, series: [] as CompareChartSerie[] };
    }

    const routeByWatchId = new Map(watches.map((item) => [item.watch_id, item.route]));
    const prepared = pointBlocks
      .map((block, index) => {
        const route = routeByWatchId.get(block.watch_id) ?? block.watch_id;
        const [origin = route, destination = ""] = route.split("->");
        const label = `${origin.trim()} -> ${destination.trim()}`;
        const color = CHART_COLORS[index % CHART_COLORS.length];
        const points = block.points
          .map((item) => {
            const ts = new Date(item.date).getTime();
            return {
              ts,
              date: item.date,
              price: item.avg_price,
              currency: item.currency,
            };
          })
          .filter((item) => Number.isFinite(item.ts) && Number.isFinite(item.price))
          .sort((a, b) => a.ts - b.ts);
        return {
          watchId: block.watch_id,
          label,
          color,
          points,
        };
      })
      .filter((serie) => serie.points.length > 0);

    if (prepared.length === 0) {
      return { hasData: false, series: [] as CompareChartSerie[] };
    }

    const allTs = prepared.flatMap((serie) => serie.points.map((point) => point.ts));
    const allPrices = prepared.flatMap((serie) => serie.points.map((point) => point.price));
    const minTs = Math.min(...allTs);
    const maxTs = Math.max(...allTs);
    const minPrice = Math.min(...allPrices);
    const maxPrice = Math.max(...allPrices);
    const xSpan = Math.max(1, maxTs - minTs);
    const ySpan = Math.max(1, maxPrice - minPrice);

    const series: CompareChartSerie[] = prepared.map((serie) => {
      const points = serie.points.map((point) => {
        const xRatio = (point.ts - minTs) / xSpan;
        const yRatio = (point.price - minPrice) / ySpan;
        const x = CHART_PAD.left + xRatio * (CHART_WIDTH - CHART_PAD.left - CHART_PAD.right);
        const y = CHART_HEIGHT - CHART_PAD.bottom - yRatio * (CHART_HEIGHT - CHART_PAD.top - CHART_PAD.bottom);
        return {
          date: point.date,
          x,
          y,
          price: point.price,
          currency: point.currency,
        };
      });
      const path = points
        .map((point, index) => `${index === 0 ? "M" : "L"}${point.x.toFixed(2)} ${point.y.toFixed(2)}`)
        .join(" ");
      return {
        watchId: serie.watchId,
        label: serie.label,
        color: serie.color,
        path,
        points,
      };
    });

    return { hasData: true, series };
  }, [compareResponse?.points, compareResponse?.watches]);

  const sortedChartSeries = useMemo(() => {
    if (!hoveredWatchId) return compareChartSeries.series;
    return [...compareChartSeries.series].sort((a, b) => {
      if (a.watchId === hoveredWatchId) return 1;
      if (b.watchId === hoveredWatchId) return -1;
      return 0;
    });
  }, [compareChartSeries.series, hoveredWatchId]);

  useEffect(() => {
    if (selectedCount < 2 || selectedCount > 4) {
      setCompareResponse(null);
      setHasCompareError(false);
      return;
    }
    let mounted = true;
    setIsLoadingCompare(true);
    apiFetch<PriceCompareResponse>(`/prices/compare?watch_ids=${compareQuery}`)
      .then((payload) => {
        if (!mounted) return;
        setCompareResponse(payload);
        setHasCompareError(false);
      })
      .catch(() => {
        if (!mounted) return;
        setCompareResponse(null);
        setHasCompareError(true);
      })
      .finally(() => {
        if (mounted) setIsLoadingCompare(false);
      });
    return () => {
      mounted = false;
    };
  }, [compareQuery, selectedCount]);

  return (
    <section className={`panel compare-panel section-gap${compareIds.length < 2 ? " compare-empty" : ""}`}>
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
                const deltaLabel = card.delta === 0 ? t("watchlist.compare.noChange") : formatSignedCurrency(card.delta, card.latest.currency, localeTag);
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
                        <strong>{formatCurrency(card.latest.price, card.latest.currency, localeTag)}</strong>
                      </div>
                      <div>
                        <span className="compare-label">{t("watchlist.compare.min")}</span>
                        <strong>{formatCurrency(card.min, card.latest.currency, localeTag)}</strong>
                      </div>
                      <div>
                        <span className="compare-label">{t("watchlist.compare.max")}</span>
                        <strong>{formatCurrency(card.max, card.latest.currency, localeTag)}</strong>
                      </div>
                    </div>
                    <div className="compare-meta">{t("watchlist.compare.lastUpdate", { value: formatDateTime(card.latest.capturedAt, localeTag) })}</div>
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
          {hasCompareError ? <div className="notice notice-error notice-compact">{t("watchlist.compare.errorInline")}</div> : null}
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
                  <span className="compare-route">{option.origin} -&gt; {option.destination}</span>
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
            <div className="compare-multi-container">

              {compareChartSeries.hasData && (
                <div className="compare-chart compare-chart--global" data-testid="compare-master-chart" style={{ position: "relative" }}>
                  <div className="compare-chart-frame" style={{ position: "relative" }}>
                    <svg
                      className="compare-chart-svg"
                      viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
                      role="img"
                      aria-label="Grafico comparativo de vuelos seleccionados"
                    >
                      {[0, 0.33, 0.66, 1].map((ratio) => {
                        const y = CHART_PAD.top + (CHART_HEIGHT - CHART_PAD.top - CHART_PAD.bottom) * ratio;
                        return <line key={`y-grid-${ratio}`} x1={CHART_PAD.left} y1={y} x2={CHART_WIDTH - CHART_PAD.right} y2={y} className="compare-chart-grid" />;
                      })}

                      {sortedChartSeries.map((serie) => {
                        const isFocused = hoveredWatchId === serie.watchId;
                        const isMuted = hoveredWatchId !== null && !isFocused;
                        return (
                          <g key={`serie-${serie.watchId}`}>
                            <path
                              fill="none"
                              d={serie.path}
                              stroke={serie.color}
                              className={`compare-chart-line ${isFocused ? "is-focused" : ""} ${isMuted ? "is-muted" : ""}`}
                            />
                            {serie.points.length > 0 && (
                              <>
                                <circle cx={serie.points[0].x} cy={serie.points[0].y} r={isFocused ? 3.5 : 2.6} fill={serie.color} className={`compare-chart-endpoint ${isMuted ? "is-muted" : ""}`} />
                                <circle cx={serie.points[serie.points.length - 1].x} cy={serie.points[serie.points.length - 1].y} r={isFocused ? 4.5 : 3.2} fill={serie.color} className={`compare-chart-endpoint compare-chart-endpoint--last ${isMuted ? "is-muted" : ""}`} />
                              </>
                            )}
                          </g>
                        );
                      })}

                      {sortedChartSeries.map((serie) => (
                        <g key={`hit-area-${serie.watchId}`}>
                          {serie.points.map((point, i) => (
                            <circle
                              key={`hit-${serie.watchId}-${i}`}
                              cx={point.x}
                              cy={point.y}
                              r={16}
                              fill="transparent"
                              style={{ cursor: "crosshair", pointerEvents: "all" }}
                              onMouseEnter={() => {
                                setHoveredWatchId(serie.watchId);
                                setHoveredPoint({ ...point, label: serie.label, color: serie.color });
                              }}
                              onMouseLeave={() => {
                                setHoveredWatchId(null);
                                setHoveredPoint(null);
                              }}
                            />
                          ))}
                        </g>
                      ))}
                    </svg>

                    {hoveredPoint && (
                      <div
                        className="history-tooltip"
                        style={{
                          left: `${hoveredPoint.x}px`,
                          top: `${hoveredPoint.y}px`,
                          opacity: 1,
                        }}
                      >
                        <span className="history-tooltip-tag" style={{ color: hoveredPoint.color }}>
                          {hoveredPoint.label}
                        </span>
                        <strong style={{ fontSize: "1.05rem" }}>
                          {formatCurrency(hoveredPoint.price, hoveredPoint.currency, localeTag)}
                        </strong>
                        <span>{formatDateTime(hoveredPoint.date, localeTag)}</span>
                      </div>
                    )}
                  </div>

                  <div className="compare-chart-legend" aria-hidden="true">
                    {compareChartSeries.series.map((serie) => (
                      <span
                        key={`legend-${serie.watchId}`}
                        className={`compare-chart-legend-item ${hoveredWatchId === serie.watchId ? "is-current" : ""}`}
                        onMouseEnter={() => setHoveredWatchId(serie.watchId)}
                        onMouseLeave={() => setHoveredWatchId(null)}
                      >
                        <i style={{ background: serie.color }} />
                        {serie.label}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div className="compare-grid compare-grid--multi">
                {compareResponse.watches.map((card) => {
                  const [origin = card.route, destination = ""] = card.route.split("->");
                  return (
                    <article
                      key={`multi-${card.watch_id}`}
                      className={`compare-card compare-card--multi ${hoveredWatchId === card.watch_id ? "is-hovered" : ""}`}
                      onMouseEnter={() => setHoveredWatchId(card.watch_id)}
                      onMouseLeave={() => setHoveredWatchId(null)}
                    >
                      <div className="compare-head">
                        <strong>{origin} -&gt; {destination}</strong>
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
                          <strong>{card.latest_price == null ? t("watchlist.compare.noData") : formatCurrency(card.latest_price, card.currency, localeTag)}</strong>
                        </div>
                        <div>
                          <span className="compare-label">{t("watchlist.compare.minMax")}</span>
                          <strong>
                            {card.min_price != null && card.max_price != null
                              ? `${formatCurrency(card.min_price, card.currency, localeTag)} - ${formatCurrency(card.max_price, card.currency, localeTag)}`
                              : t("watchlist.compare.noData")}
                          </strong>
                        </div>
                        <div>
                          <span className="compare-label">{t("watchlist.summary.avg")}</span>
                          <strong>{card.avg_price == null ? t("watchlist.compare.noData") : formatCurrency(card.avg_price, card.currency, localeTag)}</strong>
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
            </div>
          ) : (
            <p className="muted">{t("watchlist.compare.noDataInRange")}</p>
          )}
        </div>
      )}
    </section>
  );
}