"use client";

import { useState } from "react";
import { useI18n } from "@/i18n";

import { formatDateShort, formatPrice } from "../format";
import type { HotelTrackedOfferOut } from "../types";
import { HotelTrackedOfferSnapshots } from "./HotelTrackedOfferSnapshots";

export function HotelTrackedOffersPanel({
  offers,
  loading,
  onStopTracking,
  busyOfferIds,
}: {
  offers: HotelTrackedOfferOut[];
  loading: boolean;
  onStopTracking: (offerId: string) => void;
  busyOfferIds: string[];
}) {
  const { t, localeTag } = useI18n();
  const [expandedSnapshots, setExpandedSnapshots] = useState<Record<string, boolean>>({});

  function toggleSnapshots(offerId: string) {
    setExpandedSnapshots((curr) => ({ ...curr, [offerId]: !curr[offerId] }));
  }

  return (
    <section className="panel panel-soft hotel-tracked-offers-panel">
      <div className="panel-header">
        <h2 className="panel-title">{t("hotels.trackedOffers.title")}</h2>
        <span className="status-pill success">{offers.filter((o) => o.is_active).length}</span>
      </div>

      {loading ? (
        <p className="panel-note section-gap-sm">{t("hotels.trackedOffers.loading")}</p>
      ) : null}

      {!loading && offers.length === 0 ? (
        <p className="panel-note section-gap-sm">{t("hotels.trackedOffers.empty")}</p>
      ) : null}

      {!loading && offers.length > 0 ? (
        <div className="hotel-tracked-offers-list section-gap-sm">
          {offers.map((offer) => {
            const busy = busyOfferIds.includes(offer.id);
            return (
              <article key={offer.id} className="list-row hotel-tracked-offer-item">
                <div className="hotel-tracked-offer-copy">
                  <div className="hotel-tracked-offer-header">
                    <strong>{offer.area_label || offer.hotel_id.slice(0, 8)}</strong>
                    <span className="status-pill info">{offer.provider}</span>
                  </div>
                  <div className="hotel-tracked-offer-dates panel-note">
                    {formatDateShort(offer.check_in, localeTag)} → {formatDateShort(offer.check_out, localeTag)}
                    {" · "}
                    {t("hotels.trackedOffers.guests", { count: offer.guests })}
                  </div>
                  <div className="hotel-tracked-offer-prices">
                    {offer.initial_price !== null && offer.initial_price !== offer.current_price ? (
                      <div className="hotel-tracked-offer-price-row">
                        <span className="panel-note">{t("hotels.trackedOffers.initialPrice")}</span>
                        <span className="panel-note">
                          {formatPrice(offer.initial_price, offer.currency, localeTag)}
                        </span>
                      </div>
                    ) : null}
                    <div className="hotel-tracked-offer-price-row">
                      <span className="panel-note">{t("hotels.trackedOffers.currentPrice")}</span>
                      <strong className="hotel-tracked-offer-price-value">
                        {formatPrice(offer.current_price, offer.currency, localeTag)}
                      </strong>
                    </div>
                    {offer.target_price !== null ? (
                      <div className="hotel-tracked-offer-price-row">
                        <span className="panel-note">{t("hotels.trackedOffers.targetPrice")}</span>
                        <span className="status-pill warning">
                          {formatPrice(offer.target_price, offer.currency, localeTag)}
                        </span>
                      </div>
                    ) : null}
                  </div>
                </div>
                <div className="hotel-tracked-offer-actions">
                  <button
                    type="button"
                    className="btn-ghost btn-compact"
                    onClick={() => toggleSnapshots(offer.id)}
                  >
                    {expandedSnapshots[offer.id]
                      ? t("hotels.trackedOffers.hideHistory")
                      : t("hotels.trackedOffers.viewHistory")}
                  </button>
                  <button
                    type="button"
                    className="btn-ghost btn-compact"
                    onClick={() => onStopTracking(offer.id)}
                    disabled={busy}
                  >
                    {busy ? t("shared.states.loading") : t("hotels.trackedOffers.stopTracking")}
                  </button>
                </div>
                <HotelTrackedOfferSnapshots
                  offerId={offer.id}
                  visible={expandedSnapshots[offer.id] ?? false}
                />
              </article>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}
