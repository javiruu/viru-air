"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { useI18n } from "@/i18n";
import { formatCurrency, formatNumber } from "@/modules/shared/format";
import { apiFetch } from "@/modules/shared/api";

import { buildRankingReasons } from "./rankingExplainers";
import { getScoreBand, getScoreClass } from "./scoreBands";
import { DEFAULT_WEIGHTS, getWeightImpactLines, getWeightPrioritySummary, type WeightKey } from "./weightImpact";

type ExperienceMode = "discover" | "optimize";
type SortKey = "ai" | "price" | "speed" | "climate" | "trend";
type SortDirection = "asc" | "desc";

type RecommendationItem = {
  id: string;
  origin_iata: string;
  destination_iata: string;
  travel_date: string;
  departure_time_local: string | null;
  price: number;
  currency: string;
  avg_price?: number | null;
  distance_km?: number | null;
  duration_minutes_est?: number | null;
  weather?: {
    temp_max?: number | null;
    temp_min?: number | null;
    precip_probability?: number | null;
  } | null;
  trend: "up" | "down" | "flat";
  tags?: string[];
  score: number;
  ai_reason?: string;
  signals?: Partial<Record<WeightKey, number>>;
};

type RecommendationResponse = {
  query: {
    strict_filters?: boolean;
    soft_filters_weight?: number;
  };
  items: RecommendationItem[];
  ai: {
    used: boolean;
    model: string | null;
    error: string | null;
    reasoning_mode: "ai" | "heuristic";
    summary?: string | null;
    active_signals?: string[];
  };
};

type WeightsPercent = Record<WeightKey, number>;

type RankedItem = RecommendationItem & {
  liveScore: number;
};

function parseIataField(value: string): string | string[] | null {
  const parts = value
    .split(",")
    .map((entry) => entry.trim().toUpperCase())
    .filter((entry) => /^[A-Z]{3}$/.test(entry));

  if (parts.length === 0) return null;
  if (parts.length === 1) return parts[0];
  return parts;
}

function normalizeWeightPercent(weights: WeightsPercent): Record<WeightKey, number> {
  const clamped = {
    price: Math.max(0, weights.price),
    speed: Math.max(0, weights.speed),
    climate: Math.max(0, weights.climate),
    trend: Math.max(0, weights.trend),
    novelty: Math.max(0, weights.novelty),
  };
  const total = clamped.price + clamped.speed + clamped.climate + clamped.trend + clamped.novelty;
  if (total <= 0) {
    return { ...DEFAULT_WEIGHTS };
  }
  return {
    price: clamped.price / total,
    speed: clamped.speed / total,
    climate: clamped.climate / total,
    trend: clamped.trend / total,
    novelty: clamped.novelty / total,
  };
}

function computeLiveScore(item: RecommendationItem, weights: Record<WeightKey, number>): number {
  if (!item.signals) return item.score;
  const weighted =
    (weights.price * (item.signals.price ?? 0.5)
      + weights.speed * (item.signals.speed ?? 0.5)
      + weights.climate * (item.signals.climate ?? 0.5)
      + weights.trend * (item.signals.trend ?? 0.5)
      + weights.novelty * (item.signals.novelty ?? 0.5)) *
    100;
  return Number(weighted.toFixed(2));
}

function truncateLine(value: string, max = 80): string {
  if (value.length <= max) return value;
  return `${value.slice(0, max - 1).trimEnd()}...`;
}

function defaultTravelDate(): string {
  return new Date().toISOString().slice(0, 10);
}

function formatRouteMeta(item: RecommendationItem, t: (key: string, params?: Record<string, string | number>) => string): string {
  const flightText = item.duration_minutes_est
    ? `Directo | ${t("recommendations.duration", { value: Math.round(item.duration_minutes_est) })}`
    : t("recommendations.unknownDuration");

  if (!item.weather?.temp_min && !item.weather?.temp_max) {
    return flightText;
  }

  const minTemp = item.weather.temp_min ?? "--";
  const maxTemp = item.weather.temp_max ?? "--";
  const precip = item.weather.precip_probability ?? "--";
  return `${flightText} | ${minTemp}C-${maxTemp}C | ${precip}%`;
}

function smartTagKey(item: RecommendationItem, score: number): string {
  if (score >= 70) return "recommendations.smartTag.opportunity";
  if (item.trend === "down") return "recommendations.smartTag.trendingDown";
  if ((item.avg_price ?? 0) > 0 && item.price > (item.avg_price ?? 0) * 1.08) return "recommendations.smartTag.aboveAvg";
  if (score >= 45) return "recommendations.smartTag.stable";
  return "recommendations.smartTag.watch";
}

function signalLabelKey(signal: WeightKey): string {
  return `recommendations.weights.${signal}`;
}

function AnimatedScore({ value }: { value: number }) {
  const [visible, setVisible] = useState(Math.round(value));
  const previousValueRef = useRef<number>(Math.round(value));

  useEffect(() => {
    const rounded = Math.round(value);
    if (typeof window === "undefined") {
      setVisible(rounded);
      previousValueRef.current = rounded;
      return;
    }

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setVisible(rounded);
      previousValueRef.current = rounded;
      return;
    }

    const startValue = previousValueRef.current;
    const durationMs = 320;
    const startTime = performance.now();
    let frame = 0;

    const tick = (now: number) => {
      const progress = Math.min(1, (now - startTime) / durationMs);
      const next = Math.round(startValue + (rounded - startValue) * progress);
      setVisible(next);
      if (progress < 1) {
        frame = window.requestAnimationFrame(tick);
      } else {
        previousValueRef.current = rounded;
      }
    };

    frame = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(frame);
  }, [value]);

  return <span>{visible}</span>;
}

export default function RecommendationsExplorer() {
  const { locale, localeTag, t } = useI18n();
  const router = useRouter();

  const [mode, setMode] = useState<ExperienceMode>("discover");
  const [panelCollapsed, setPanelCollapsed] = useState(true);
  const [sortBy, setSortBy] = useState<SortKey>("ai");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  const [origin, setOrigin] = useState("MAD");
  const [destination, setDestination] = useState("STN");
  const [travelDate, setTravelDate] = useState(defaultTravelDate());
  const [daysBefore, setDaysBefore] = useState(1);
  const [daysAfter, setDaysAfter] = useState(2);

  const [departAfter, setDepartAfter] = useState("07:00");
  const [departBefore, setDepartBefore] = useState("22:00");
  const [radiusKm, setRadiusKm] = useState(150);
  const [includeNearbyOrigins, setIncludeNearbyOrigins] = useState(false);
  const [includeNearbyDestinations, setIncludeNearbyDestinations] = useState(false);
  const [excludeOrigins, setExcludeOrigins] = useState("");
  const [excludeDestinations, setExcludeDestinations] = useState("");
  const [strictFilters, setStrictFilters] = useState(true);
  const [softFiltersWeight, setSoftFiltersWeight] = useState(60);

  const [weightsPercent, setWeightsPercent] = useState<WeightsPercent>({
    price: 40,
    speed: 20,
    climate: 20,
    trend: 10,
    novelty: 10,
  });

  const [items, setItems] = useState<RecommendationItem[]>([]);
  const [aiMeta, setAiMeta] = useState<RecommendationResponse["ai"] | null>(null);
  const [expandedCards, setExpandedCards] = useState<Record<string, boolean>>({});
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const saved = window.sessionStorage.getItem("viru_reco_mode");
    if (saved === "discover" || saved === "optimize") {
      setMode(saved);
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.sessionStorage.setItem("viru_reco_mode", mode);
  }, [mode]);

  const normalizedWeights = useMemo(() => normalizeWeightPercent(weightsPercent), [weightsPercent]);

  const rankedItems = useMemo<RankedItem[]>(() => {
    const enriched = items.map((item) => ({
      ...item,
      liveScore: computeLiveScore(item, normalizedWeights),
    }));

    const directionFactor = sortDirection === "desc" ? -1 : 1;
    return enriched.sort((a, b) => {
      if (sortBy === "price") {
        return directionFactor * (a.price - b.price);
      }
      if (sortBy === "speed") {
        return directionFactor * ((a.duration_minutes_est ?? Number.MAX_SAFE_INTEGER) - (b.duration_minutes_est ?? Number.MAX_SAFE_INTEGER));
      }
      if (sortBy === "climate") {
        return directionFactor * ((a.signals?.climate ?? 0) - (b.signals?.climate ?? 0));
      }
      if (sortBy === "trend") {
        const trendValue = (value: RecommendationItem["trend"]) => (value === "down" ? 2 : value === "flat" ? 1 : 0);
        return directionFactor * (trendValue(a.trend) - trendValue(b.trend));
      }
      return directionFactor * (a.liveScore - b.liveScore);
    });
  }, [items, normalizedWeights, sortBy, sortDirection]);

  const impactLines = useMemo(() => getWeightImpactLines(normalizedWeights), [normalizedWeights]);
  const prioritySummary = useMemo(() => getWeightPrioritySummary(normalizedWeights), [normalizedWeights]);

  async function refreshRecommendations() {
    setError("");

    const originPayload = parseIataField(origin);
    const destinationPayload = parseIataField(destination);

    if (!originPayload || !destinationPayload || !travelDate) {
      setError(t("recommendations.requiredMissing"));
      return;
    }

    const payload = {
      origin_iata: originPayload,
      destination_iata: destinationPayload,
      travel_date: travelDate,
      days_before: daysBefore,
      days_after: daysAfter,
      radius_km: radiusKm,
      include_nearby_origins: includeNearbyOrigins,
      include_nearby_destinations: includeNearbyDestinations,
      depart_after: departAfter || undefined,
      depart_before: departBefore || undefined,
      exclude_origins: excludeOrigins,
      exclude_destinations: excludeDestinations,
      strict_filters: strictFilters,
      soft_filters_weight: softFiltersWeight / 100,
      locale,
      weights: normalizedWeights,
    };

    try {
      setIsLoading(true);
      const response = await apiFetch<RecommendationResponse>("/recommendations", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setItems(response.items || []);
      setAiMeta(response.ai || null);
      setExpandedCards({});
    } catch {
      setError(t("recommendations.errorGeneric"));
      setItems([]);
      setAiMeta(null);
    } finally {
      setIsLoading(false);
    }
  }

  const activeSignalsText = aiMeta?.active_signals?.join(" | ") || "price | trend | speed | climate | novelty";

  return (
    <main className="shell reco-shell" id="main-content">
      <header className="panel panel-soft reco-header-clean">
        <button className="btn-ghost" type="button" onClick={() => router.push("/dashboard")}>
          {t("shared.actions.back")}
        </button>
        <div>
          <h1>{t("recommendations.title")}</h1>
          <p>{t("recommendations.subtitle")}</p>
        </div>
        <div className="reco-mode-toggle" role="tablist" aria-label={t("recommendations.modeTitle")}>
          <button
            type="button"
            className={mode === "discover" ? "is-active" : ""}
            onClick={() => setMode("discover")}
          >
            {t("recommendations.mode.discover")}
          </button>
          <button
            type="button"
            className={mode === "optimize" ? "is-active" : ""}
            onClick={() => {
              setMode("optimize");
              setPanelCollapsed(false);
            }}
          >
            {t("recommendations.mode.optimize")}
          </button>
        </div>
      </header>

      <section className="panel panel-soft reco-status-line" aria-live="polite">
        <span><strong>{t("recommendations.originLabel")}:</strong> {origin || t("recommendations.emptyOrigin")}</span>
        <span className="reco-status-sep">|</span>
        <span><strong>{t("recommendations.destinationLabel")}:</strong> {destination || t("recommendations.emptyDestination")}</span>
        <span className="reco-status-sep">|</span>
        <span><strong>{t("recommendations.dateLabel")}:</strong> {travelDate || t("recommendations.pendingDate")}</span>
        <span className="reco-status-sep">|</span>
        <span>
          <strong>{t("recommendations.systemLabel")}:</strong>{" "}
          {aiMeta?.used ? t("recommendations.aiUsed") : t("recommendations.aiFallbackTitle")}
        </span>
      </section>

      <section className="reco-layout-2">
        <aside className={`panel panel-soft reco-config-panel ${panelCollapsed ? "is-collapsed" : ""}`}>
          <div className="reco-panel-header">
            <h2>{t("recommendations.mode.optimize")}</h2>
            <button type="button" className="btn-ghost" onClick={() => setPanelCollapsed((prev) => !prev)}>
              {panelCollapsed ? t("recommendations.editCriteria") : t("recommendations.hideCriteria")}
            </button>
          </div>

          <div className="reco-pick">
            <label className="field">
              <span>{t("recommendations.originLabel")}</span>
              <input
                type="text"
                value={origin}
                onChange={(event) => setOrigin(event.target.value.toUpperCase())}
                placeholder="MAD, BCN"
              />
            </label>
            <label className="field">
              <span>{t("recommendations.destinationLabel")}</span>
              <input
                type="text"
                value={destination}
                onChange={(event) => setDestination(event.target.value.toUpperCase())}
                placeholder="STN, LGW"
              />
            </label>
            <label className="field">
              <span>{t("recommendations.dateLabel")}</span>
              <input type="date" value={travelDate} onChange={(event) => setTravelDate(event.target.value)} />
            </label>
          </div>

          {mode === "optimize" ? (
            <>
              <div className="reco-flex">
                <label className="field">
                  <span>{t("recommendations.daysBefore")}</span>
                  <input type="number" min={0} max={7} value={daysBefore} onChange={(event) => setDaysBefore(Number(event.target.value))} />
                </label>
                <label className="field">
                  <span>{t("recommendations.daysAfter")}</span>
                  <input type="number" min={0} max={7} value={daysAfter} onChange={(event) => setDaysAfter(Number(event.target.value))} />
                </label>
              </div>

              <div className="reco-weight">
                <h3>{t("recommendations.weightsTitle")}</h3>
                <p className="panel-note">{t("recommendations.weightsSubtitle")}</p>
                {(Object.keys(weightsPercent) as WeightKey[]).map((key) => {
                  const impact = impactLines.find((line) => line.key === key)?.deltaPoints ?? 0;
                  const delta = `${impact > 0 ? "+" : ""}${impact}`;
                  return (
                    <label key={key} className="field reco-slider-row">
                      <div className="reco-slider-head">
                        <span>{t(signalLabelKey(key))}</span>
                        <small>{weightsPercent[key]}%</small>
                      </div>
                      <input
                        type="range"
                        min={0}
                        max={100}
                        value={weightsPercent[key]}
                        onChange={(event) =>
                          setWeightsPercent((prev) => ({
                            ...prev,
                            [key]: Number(event.target.value),
                          }))
                        }
                      />
                      <small className={`reco-impact ${impact > 0 ? "is-positive" : impact < 0 ? "is-negative" : ""}`}>
                        {t("recommendations.impactByWeight", { signal: t(signalLabelKey(key)), delta })}
                      </small>
                    </label>
                  );
                })}
                {prioritySummary ? (
                  <p className="reco-impact-summary">
                    {t("recommendations.prioritySummary", {
                      primary: t(signalLabelKey(prioritySummary.primary)).toLowerCase(),
                      secondary: t(signalLabelKey(prioritySummary.secondary)).toLowerCase(),
                      percent: prioritySummary.percentMore,
                    })}
                  </p>
                ) : null}
              </div>

              <div className="reco-filters">
                <h3>{t("recommendations.filtersTitle")}</h3>
                <p className="panel-note">{t("recommendations.filtersSubtitle")}</p>

                <div className="reco-filter-mode" role="radiogroup" aria-label={t("recommendations.filterMode")}>
                  <label>
                    <input
                      type="radio"
                      name="filterMode"
                      checked={strictFilters}
                      onChange={() => setStrictFilters(true)}
                    />
                    {t("recommendations.filterStrict")}
                  </label>
                  <label>
                    <input
                      type="radio"
                      name="filterMode"
                      checked={!strictFilters}
                      onChange={() => setStrictFilters(false)}
                    />
                    {t("recommendations.filterFlexible")}
                  </label>
                </div>

                {!strictFilters ? (
                  <label className="field reco-slider-row">
                    <div className="reco-slider-head">
                      <span>{t("recommendations.softWeight")}</span>
                      <small>{softFiltersWeight}%</small>
                    </div>
                    <input
                      type="range"
                      min={20}
                      max={100}
                      value={softFiltersWeight}
                      onChange={(event) => setSoftFiltersWeight(Number(event.target.value))}
                    />
                  </label>
                ) : null}

                <label className="field">
                  <span>{t("recommendations.radiusLabel")}</span>
                  <input type="number" min={0} max={500} value={radiusKm} onChange={(event) => setRadiusKm(Number(event.target.value))} />
                </label>

                <div className="reco-flex">
                  <label className="field checkbox">
                    <input
                      type="checkbox"
                      checked={includeNearbyOrigins}
                      onChange={(event) => setIncludeNearbyOrigins(event.target.checked)}
                    />
                    <span>{t("recommendations.includeNearbyOrigins")}</span>
                  </label>
                  <label className="field checkbox">
                    <input
                      type="checkbox"
                      checked={includeNearbyDestinations}
                      onChange={(event) => setIncludeNearbyDestinations(event.target.checked)}
                    />
                    <span>{t("recommendations.includeNearbyDestinations")}</span>
                  </label>
                </div>

                <div className="reco-flex">
                  <label className="field">
                    <span>{t("recommendations.departAfter")}</span>
                    <input type="time" value={departAfter} onChange={(event) => setDepartAfter(event.target.value)} />
                  </label>
                  <label className="field">
                    <span>{t("recommendations.departBefore")}</span>
                    <input type="time" value={departBefore} onChange={(event) => setDepartBefore(event.target.value)} />
                  </label>
                </div>

                <div className="reco-flex">
                  <label className="field">
                    <span>{t("recommendations.excludeOrigins")}</span>
                    <input
                      type="text"
                      placeholder="MAD, BCN"
                      value={excludeOrigins}
                      onChange={(event) => setExcludeOrigins(event.target.value.toUpperCase())}
                    />
                  </label>
                  <label className="field">
                    <span>{t("recommendations.excludeDestinations")}</span>
                    <input
                      type="text"
                      placeholder="STN, LGW"
                      value={excludeDestinations}
                      onChange={(event) => setExcludeDestinations(event.target.value.toUpperCase())}
                    />
                  </label>
                </div>
              </div>
            </>
          ) : null}

          <div className="reco-cta-sticky">
            <button type="button" className="btn-primary reco-cta-main" onClick={refreshRecommendations} disabled={isLoading}>
              {isLoading ? t("recommendations.loadingRadar") : t("recommendations.searchStrong")}
            </button>
          </div>
        </aside>

        <section className="reco-results-focus">
          <div className="panel panel-soft reco-results-toolbar">
            <div className="reco-results-bar">
              <div>
                <h2>{t("recommendations.resultsTitle")}</h2>
                <p className="panel-note">{t("recommendations.resultsSubtitle")}</p>
              </div>
              <div className="reco-sort">
                <label className="field">
                  <span>{t("recommendations.sortLabel")}</span>
                  <select value={sortBy} onChange={(event) => setSortBy(event.target.value as SortKey)}>
                    <option value="ai">{t("recommendations.sort.ai")}</option>
                    <option value="price">{t("recommendations.sort.price")}</option>
                    <option value="speed">{t("recommendations.sort.speed")}</option>
                    <option value="climate">{t("recommendations.sort.climate")}</option>
                    <option value="trend">{t("recommendations.sort.trend")}</option>
                  </select>
                </label>
                <label className="field">
                  <span>{t("recommendations.sortDirection")}</span>
                  <select value={sortDirection} onChange={(event) => setSortDirection(event.target.value as SortDirection)}>
                    <option value="desc">{t("recommendations.sortDesc")}</option>
                    <option value="asc">{t("recommendations.sortAsc")}</option>
                  </select>
                </label>
              </div>
            </div>
          </div>

          {!aiMeta?.used && aiMeta ? (
            <article className="panel panel-soft reco-ai-fallback" role="status">
              <strong>{t("recommendations.aiFallbackTitle")}</strong>
              <p>{t("recommendations.aiFallbackBody")}</p>
              <p>{aiMeta.summary || t("recommendations.aiFallback")}</p>
              <p>{t("recommendations.aiFallbackSignals", { signals: activeSignalsText })}</p>
            </article>
          ) : null}

          {error ? <div className="notice notice-error">{error}</div> : null}

          {rankedItems.length === 0 && !isLoading ? (
            <article className="panel panel-soft reco-empty">
              <h3>{t("recommendations.emptyTitle")}</h3>
              <p>{t("recommendations.emptyBody")}</p>
            </article>
          ) : null}

          {rankedItems.length > 0 ? (
            <div className="reco-cards-grid">
              {rankedItems.map((item, index) => {
                const score = Math.round(item.liveScore);
                const scoreBand = getScoreBand(score);
                const scoreClass = getScoreClass(score);
                const detailsOpen = Boolean(expandedCards[item.id]);

                const reasons = buildRankingReasons({
                  price: item.price,
                  avg_price: item.avg_price,
                  trend: item.trend,
                  weather: item.weather,
                });

                const topByLine = truncateLine(
                  reasons
                    .slice(0, 2)
                    .map((reason) => t(reason.key, reason.params))
                    .join(" | "),
                );

                const topPercent = Math.max(1, Math.round(((index + 1) / Math.max(1, rankedItems.length)) * 100));
                const smartTag = t(smartTagKey(item, score));

                return (
                  <article key={item.id} className="reco-card-v2" style={{ animationDelay: `${Math.min(index, 8) * 50}ms` }}>
                    <div className="reco-card-summary">
                      <div className="reco-card-main">
                        <span className="reco-rank-pill">#{index + 1}</span>
                        <h3 className="reco-route-xl">
                          {item.origin_iata} {"->"} {item.destination_iata}
                        </h3>
                        <p className="reco-price-xl">{formatCurrency(item.price, item.currency || "EUR", localeTag)}</p>
                        <p className="reco-smart-tag">{smartTag}</p>
                        <p className="reco-topby-line">{topByLine}</p>
                        <p className="reco-meta-line">{formatRouteMeta(item, t)}</p>
                      </div>

                      <div className={`reco-score-lg ${scoreClass}`}>
                        <div className="reco-score-top">
                          <AnimatedScore value={score} />
                          <button
                            type="button"
                            className="reco-score-tip"
                            data-tip={t("recommendations.aiTooltip")}
                            aria-label={t("recommendations.aiTooltip")}
                          >
                            i
                          </button>
                        </div>
                        <small>{t("recommendations.scoreShort")}</small>
                        <small className="reco-score-band-text">{t(`recommendations.scoreBand.${scoreBand}`)}</small>
                        <small className="reco-score-percentile">
                          {t("recommendations.topPercentToday", { percent: topPercent })}
                        </small>
                      </div>
                    </div>

                    <div className="reco-why">
                      <strong>{t("recommendations.whyTop")}</strong>
                      <ul>
                        {reasons.map((reason, reasonIndex) => (
                          <li key={`${item.id}-reason-${reasonIndex}`} className={`tone-${reason.tone}`}>
                            {t(reason.key, reason.params)}
                          </li>
                        ))}
                      </ul>
                    </div>

                    <button
                      type="button"
                      className="btn-ghost reco-expand-btn"
                      aria-expanded={detailsOpen}
                      onClick={() => setExpandedCards((prev) => ({ ...prev, [item.id]: !prev[item.id] }))}
                    >
                      {detailsOpen ? t("recommendations.hideDetails") : t("recommendations.showDetails")}
                    </button>

                    {detailsOpen ? (
                      <div className="reco-card-details">
                        <p className="reco-detail-row">
                          <strong>{t("recommendations.avgPrice", { value: item.avg_price ? formatCurrency(item.avg_price, item.currency || "EUR", localeTag) : "--" })}</strong>
                        </p>
                        <p className="reco-detail-row">
                          {item.distance_km ? `${formatNumber(item.distance_km, { maximumFractionDigits: 0 }, localeTag)} km` : t("recommendations.unknownDistance")}
                        </p>
                        <p className="reco-detail-row">
                          {item.weather
                            ? `${t("recommendations.weather")}: ${item.weather.temp_min ?? "--"}C-${item.weather.temp_max ?? "--"}C | ${item.weather.precip_probability ?? "--"}%`
                            : t("recommendations.weatherUnavailable")}
                        </p>
                        {item.ai_reason ? <p className="reco-detail-row">{item.ai_reason}</p> : null}
                        {item.tags && item.tags.length > 0 ? (
                          <div className="reco-tags">
                            {item.tags.map((tag) => (
                              <span key={`${item.id}-${tag}`} className="chip chip-soft">{tag}</span>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    ) : null}
                  </article>
                );
              })}
            </div>
          ) : null}
        </section>
      </section>

      <footer className="panel panel-soft reco-scale-footer">
        <h3>{t("recommendations.scaleTitle")}</h3>
        <p>{t("recommendations.scaleHigh")}</p>
        <p>{t("recommendations.scaleMidHigh")}</p>
        <p>{t("recommendations.scaleMidLow")}</p>
        <p>{t("recommendations.scaleLow")}</p>
      </footer>
    </main>
  );
}
