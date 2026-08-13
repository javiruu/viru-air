"use client";

import { useEffect, useState } from "react";
import { useI18n } from "@/i18n";
import { getTrackedOfferHistoryV2 } from "../api";
import { formatDate, formatPrice } from "../format";
import type { HotelTrackedOfferHistoryV2Out } from "../types";

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
      .catch((error: unknown) => {
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
