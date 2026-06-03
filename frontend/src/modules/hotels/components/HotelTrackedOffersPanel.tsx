"use client";

import { useI18n } from "@/i18n";

import type { HotelTrackedOfferOut } from "../types";

function formatDate(iso: string | null, localeTag: string): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat(localeTag, {
    day: "2-digit",
    month: "short",
  }).format(new Date(iso));
}

function formatPrice(value: number | null, currency: string, localeTag: string): string {
  if (value === null) return "—";
  return new Intl.NumberFormat(localeTag, {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(value);
}

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
                    {formatDate(offer.check_in, localeTag)} → {formatDate(offer.check_out, localeTag)}
                    {" · "}
                    {t("hotels.trackedOffers.guests", { count: offer.guests })}
                  </div>
                  <div className="hotel-tracked-offer-prices">
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
                    onClick={() => onStopTracking(offer.id)}
                    disabled={busy}
                  >
                    {busy ? t("shared.states.loading") : t("hotels.trackedOffers.stopTracking")}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}
