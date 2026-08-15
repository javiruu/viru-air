"use client";

import { useEffect, useMemo, useState } from "react";
import { useI18n } from "@/i18n";
import { getTrackedOfferHistoryV2 } from "../api";
import { formatDate, formatPrice } from "../format";
import type { HotelTrackedOfferHistoryV2Out } from "../types";
import { buildHotelPriceObservationChart } from "./hotelPriceObservationChart";

export function HotelTrackedOfferSnapshots({
  offerId,
  visible,
  panelId,
}: {
  offerId: string;
  visible: boolean;
  panelId: string;
}) {
  const { t, localeTag } = useI18n();
  const [history, setHistory] = useState<HotelTrackedOfferHistoryV2Out | null>(null);
  const [loading, setLoading] = useState(false);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    if (!visible) return;
    const controller = new AbortController();
    let cancelled = false;
    setLoading(true);
    setHasError(false);
    setHistory(null);
    getTrackedOfferHistoryV2(offerId, controller.signal)
      .then((data) => {
        if (cancelled) return;
        setHistory(data);
      })
      .catch(() => {
        if (cancelled) return;
        if (controller.signal.aborted) return;
        setHasError(true);
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [offerId, visible]);

  const priceChart = useMemo(() => {
    if (history === null) return null;
    const completeObservations = history.capabilities.gap_detection === "supported"
      && history.series.gaps.length === 0
      && history.series.points.every((snap) => (
        snap.eligibility === "eligible"
        && snap.price_semantics === "total"
        && snap.price.amount !== null
        && snap.price.amount > 0
      ));
    return buildHotelPriceObservationChart(
      history.series.points.map((snap) => ({
        id: snap.snapshot_id,
        observedAt: snap.observed_at,
        amount: snap.price.amount,
        eligible: snap.eligibility === "eligible",
        totalPrice: snap.price_semantics === "total",
      })),
      completeObservations,
    );
  }, [history]);

  if (!visible) return null;

  return (
    <div id={panelId} className="hotel-tracked-offer-snapshots section-gap-sm">
      <strong className="hotel-snapshots-title">{t("hotels.trackedOffers.snapshotsTitle")}</strong>
      {loading ? (
        <p className="panel-note">{t("shared.states.loading")}</p>
      ) : hasError ? (
        <p className="panel-note">{t("hotels.trackedOffers.snapshotsLoadError")}</p>
      ) : history === null || history.series.points.length === 0 ? (
        <p className="panel-note">{t("hotels.trackedOffers.snapshotsEmpty")}</p>
      ) : (
        <div className="hotel-snapshots-list">
          <p className="panel-note">
            {t(`hotels.trackedOffers.freshness.${history.freshness.state}`)}
          </p>
          {history.aggregates.sample_size_eligible < 3 ? (
            <p className="panel-note">{t("hotels.trackedOffers.snapshotsLimited")}</p>
          ) : null}
          {priceChart !== null && priceChart.points.length > 0 ? (
            <figure className="hotel-price-observations">
              <figcaption id={`${panelId}-observations-title`} className="hotel-price-observations-header">
                <span>{t("hotels.trackedOffers.snapshotsVisualTitle")}</span>
                <strong>
                  {formatPrice(priceChart.minAmount, history.aggregates.currency, localeTag)}
                  {priceChart.minAmount !== priceChart.maxAmount
                    ? `–${formatPrice(priceChart.maxAmount, history.aggregates.currency, localeTag)}`
                    : null}
                </strong>
              </figcaption>
              <svg
                className="hotel-price-observations-chart"
                viewBox="0 0 640 154"
                role="img"
                aria-labelledby={`${panelId}-observations-title`}
              >
                {priceChart.hasContinuousLine ? (
                  <polyline
                    className="hotel-price-observations-line"
                    points={priceChart.points.map((point) => `${point.x},${point.y}`).join(" ")}
                  />
                ) : null}
                {priceChart.points.map((point) => (
                  <circle
                    key={point.id}
                    className="hotel-price-observations-point"
                    cx={point.x}
                    cy={point.y}
                    r="5"
                  >
                    <title>{`${formatPrice(point.amount, history.aggregates.currency, localeTag)} · ${formatDate(point.observedAt, localeTag)}`}</title>
                  </circle>
                ))}
              </svg>
              <p className="panel-note hotel-price-observations-note">
                {t(
                  priceChart.hasContinuousLine
                    ? "hotels.trackedOffers.snapshotsVisualComplete"
                    : "hotels.trackedOffers.snapshotsVisualGaps",
                )}
              </p>
            </figure>
          ) : null}
          {history.series.points.map((snap) => (
            <article key={snap.snapshot_id} className="list-row hotel-snapshot-item">
              <div>
                <strong>
                  {snap.price.amount === null
                    ? t("hotels.trackedOffers.noPrice")
                    : formatPrice(snap.price.amount, snap.price.currency, localeTag)}
                </strong>
                <p className="panel-note">
                  {snap.provider}
                  {snap.availability_status === "unavailable"
                    ? ` · ${t("shared.states.unavailable")}`
                    : null}
                  {snap.eligibility === "excluded"
                    ? ` · ${t("hotels.trackedOffers.snapshotsNotComparable")}`
                    : null}
                </p>
              </div>
              <p className="panel-note">{formatDate(snap.observed_at, localeTag)}</p>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
