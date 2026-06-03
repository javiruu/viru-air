"use client";

import { useMemo } from "react";

import { useI18n } from "@/i18n";

import type { HotelSearchOut } from "../types";

export function HotelSearchPanel({
  query,
  city,
  loading,
  onQueryChange,
  onCityChange,
  onSearch,
  onIngest,
}: {
  query: string;
  city: string;
  loading: boolean;
  onQueryChange: (value: string) => void;
  onCityChange: (value: string) => void;
  onSearch: () => void;
  onIngest: () => void;
}) {
  const { t } = useI18n();
  const disabled = useMemo(() => loading, [loading]);

  return (
    <section className="panel hotel-search-panel" aria-label={t("hotels.search.panelLabel")}>
      <div className="panel-header">
        <div>
          <h2 className="panel-title">{t("hotels.search.title")}</h2>
          <p className="panel-subtitle">{t("hotels.search.subtitle")}</p>
        </div>
        <span className="status-pill info">{t("hotels.provider.statusMock")}</span>
      </div>
      <form
        className="section-gap-sm"
        onSubmit={(event) => {
          event.preventDefault();
          onSearch();
        }}
      >
        <div className="hotel-search-grid">
          <label className="field qs-label">
            <span>{t("hotels.search.nameLabel")}</span>
            <input className="qs-input-neutral" value={query} onChange={(event) => onQueryChange(event.target.value)} placeholder={t("hotels.search.namePlaceholder")} />
          </label>
          <label className="field qs-label">
            <span>{t("hotels.search.cityLabel")}</span>
            <input className="qs-input-neutral" value={city} onChange={(event) => onCityChange(event.target.value)} placeholder={t("hotels.search.cityPlaceholder")} />
          </label>
        </div>
        <div className="action-row section-gap-sm">
          <button type="submit" className="btn-primary" disabled={disabled}>{loading ? t("shared.states.loading") : t("hotels.actions.search")}</button>
          <button type="button" className="btn-secondary" onClick={onIngest} disabled={disabled}>{t("hotels.actions.loadMock")}</button>
        </div>
      </form>
    </section>
  );
}

export function HotelResultCard({
  hotel,
  isActive,
  isInWatchlist,
  watchlistBusy,
  onSelect,
  onAddWatch,
  onRemoveWatch,
  onTrackPrice,
  trackedBusy,
  hasTracking,
}: {
  hotel: HotelSearchOut;
  isActive: boolean;
  isInWatchlist: boolean;
  watchlistBusy: boolean;
  onSelect: (hotelId: string) => void;
  onAddWatch: (hotelId: string) => void;
  onRemoveWatch: (hotelId: string) => void;
  onTrackPrice?: (hotelId: string) => void;
  trackedBusy?: boolean;
  hasTracking?: boolean;
}) {
  const { t } = useI18n();

  return (
    <article className={`card hotel-result-card${isActive ? " is-active" : ""}`}>
      <button type="button" className="hotel-result-main" onClick={() => onSelect(hotel.id)}>
        <div>
          <h3>{hotel.canonical_name}</h3>
          <p>{hotel.city}, {hotel.country_code}</p>
        </div>
        <span className="status-pill info">{hotel.stars ? `${hotel.stars}\u2605` : t("hotels.card.noStars")}</span>
      </button>
      <div className="row-actions hotel-result-actions">
        {onTrackPrice ? (
          <button
            type="button"
            className={`btn-primary btn-compact${hasTracking ? " is-active" : ""}`}
            onClick={() => onTrackPrice(hotel.id)}
            disabled={trackedBusy || hasTracking}
            aria-pressed={hasTracking}
          >
            {trackedBusy
              ? t("shared.states.loading")
              : hasTracking
                ? t("hotels.actions.trackingActive")
                : t("hotels.actions.trackPrice")}
          </button>
        ) : (
          <button
            type="button"
            className={`btn-ghost btn-compact${isInWatchlist ? " is-active" : ""}`}
            onClick={() => (isInWatchlist ? onRemoveWatch(hotel.id) : onAddWatch(hotel.id))}
            disabled={watchlistBusy}
            aria-pressed={isInWatchlist}
          >
            {watchlistBusy ? t("shared.states.loading") : isInWatchlist ? t("hotels.actions.inWatchlist") : t("hotels.actions.addToWatchlist")}
          </button>
        )}
      </div>
    </article>
  );
}

