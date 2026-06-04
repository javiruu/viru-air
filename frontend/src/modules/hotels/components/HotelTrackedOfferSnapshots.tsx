"use client";

import { useEffect, useState } from "react";
import { useI18n } from "@/i18n";
import { getTrackedOfferSnapshots } from "../api";
import { formatDate, formatPrice } from "../format";
import type { HotelRateOut } from "../types";

export function HotelTrackedOfferSnapshots({
  offerId,
  visible,
}: {
  offerId: string;
  visible: boolean;
}) {
  const { t, localeTag } = useI18n();
  const [snapshots, setSnapshots] = useState<HotelRateOut[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!visible) return;
    let cancelled = false;
    setLoading(true);
    getTrackedOfferSnapshots(offerId)
      .then((data) => {
        if (cancelled) return;
        setSnapshots(data);
      })
      .catch(() => {
        if (cancelled) return;
        setSnapshots([]);
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [offerId, visible]);

  if (!visible) return null;

  return (
    <div className="hotel-tracked-offer-snapshots section-gap-sm">
      <strong className="hotel-snapshots-title">{t("hotels.trackedOffers.snapshotsTitle")}</strong>
      {loading ? (
        <p className="panel-note">{t("shared.states.loading")}</p>
      ) : snapshots.length === 0 ? (
        <p className="panel-note">{t("hotels.trackedOffers.snapshotsEmpty")}</p>
      ) : (
        <div className="hotel-snapshots-list">
          {snapshots.map((snap) => (
            <article key={snap.id} className="list-row hotel-snapshot-item">
              <div>
                <strong>
                  {formatPrice(snap.amount, snap.currency, localeTag)}
                </strong>
                <p className="panel-note">
                  {snap.provider}
                  {snap.availability_status === "unavailable"
                    ? " · No disponible"
                    : null}
                </p>
              </div>
              <p className="panel-note">{formatDate(snap.collected_at, localeTag)}</p>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
