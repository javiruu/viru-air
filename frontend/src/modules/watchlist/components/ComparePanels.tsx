import { useEffect, useMemo, useState } from "react";

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

function volatilityLabel(value: "low" | "medium" | "high" | "insufficient_data"): string {
  if (value === "low") return "Baja";
  if (value === "medium") return "Media";
  if (value === "high") return "Alta";
  return "Sin datos";
}

export function ComparePanels({
  compareCards,
  compareOptions,
  compareSelection,
  compareBadges,
  compareIds,
  compareNotice,
  onToggleCompare,
}: ComparePanelsProps) {
  const [compareResponse, setCompareResponse] = useState<PriceCompareResponse | null>(null);
  const [isLoadingCompare, setIsLoadingCompare] = useState(false);
  const selectedCount = compareIds.length;
  const compareQuery = useMemo(() => compareIds.join(","), [compareIds]);
  const compareBadgesFromResponse = useMemo(() => {
    const watches = compareResponse?.watches ?? [];
    if (watches.length === 0) {
      return { bestPriceId: null as string | null, stableId: null as string | null };
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
    return {
      bestPriceId: bestPrice?.watch_id ?? null,
      stableId: stable?.watch_id ?? null,
    };
  }, [compareResponse?.watches]);

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
    <>
      {compareCards ? (
        <section className="panel compare-panel section-gap">
          <div className="panel-header">
            <h2 className="panel-title">Comparativa rapida</h2>
            <span className="muted">Dos fechas seleccionadas</span>
          </div>
          <div className="compare-grid">
            {compareCards.map((card) => {
              const trend = card.delta > 0 ? "up" : card.delta < 0 ? "down" : "flat";
              const deltaLabel = card.delta === 0 ? "Sin variación" : formatSignedCurrency(card.delta, card.latest.currency);
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
                      <span className="compare-label">Actual</span>
                      <strong>{formatCurrency(card.latest.price, card.latest.currency)}</strong>
                    </div>
                    <div>
                      <span className="compare-label">Mínimo</span>
                      <strong>{formatCurrency(card.min, card.latest.currency)}</strong>
                    </div>
                    <div>
                      <span className="compare-label">Máximo</span>
                      <strong>{formatCurrency(card.max, card.latest.currency)}</strong>
                    </div>
                  </div>
                  <div className="compare-meta">Última actualización: {formatDateTime(card.latest.capturedAt)}</div>
                </article>
              );
            })}
          </div>
        </section>
      ) : null}

      <section className="panel compare-multi-panel section-gap">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">Comparativa multi-vuelo</h2>
            <p className="panel-subtitle">Selecciona hasta 4 vuelos para ver precio, estabilidad y frescura.</p>
          </div>
          <span className="compare-count">{compareIds.length}/4 seleccionados</span>
        </div>
        {compareNotice ? <div className="notice notice-error notice-compact">{compareNotice}</div> : null}
        {compareResponse?.currency_mode === "mixed" ? (
          <div className="notice notice-info notice-compact">Hay monedas distintas; compara con cuidado.</div>
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
        {compareIds.length < 2 || compareIds.length > 4 ? (
          <p className="muted">Selecciona entre 2 y 4 rutas para comparar.</p>
        ) : isLoadingCompare ? (
          <p className="muted">Cargando comparativa...</p>
        ) : compareResponse?.watches?.length ? (
          <div className="compare-grid compare-grid--multi">
            {compareResponse.watches.map((card) => {
              const [origin = card.route, destination = ""] = card.route.split("->");
              return (
                <article key={`multi-${card.watch_id}`} className="compare-card compare-card--multi">
                  <div className="compare-head">
                    <strong>{origin} → {destination}</strong>
                    <div className="compare-badges">
                      {compareBadgesFromResponse.bestPriceId === card.watch_id ? <span className="compare-badge">Mejor precio</span> : null}
                      {compareBadgesFromResponse.stableId === card.watch_id ? <span className="compare-badge">Más estable</span> : null}
                    </div>
                  </div>
                  <div className="compare-subtitle">{card.travel_date}</div>
                  <div className="compare-body">
                    <div>
                      <span className="compare-label">Actual</span>
                      <strong>{card.latest_price == null ? "Sin datos" : formatCurrency(card.latest_price, card.currency)}</strong>
                    </div>
                    <div>
                      <span className="compare-label">Mín / Máx</span>
                      <strong>
                        {card.min_price != null && card.max_price != null
                          ? `${formatCurrency(card.min_price, card.currency)}-${formatCurrency(card.max_price, card.currency)}`
                          : "Sin datos"}
                      </strong>
                    </div>
                    <div>
                      <span className="compare-label">Media</span>
                      <strong>{card.avg_price == null ? "Sin datos" : formatCurrency(card.avg_price, card.currency)}</strong>
                    </div>
                  </div>
                  <div className="compare-meta">
                    <span>Capturas: {card.snapshot_count}</span>
                    <span>Volatilidad: {volatilityLabel(card.volatility_hint)}</span>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <p className="muted">No hay datos para comparar en este rango.</p>
        )}
      </section>
    </>
  );
}
