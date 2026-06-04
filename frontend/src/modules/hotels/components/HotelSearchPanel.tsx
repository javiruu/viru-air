"use client";

import { useEffect, useMemo } from "react";

import { useI18n } from "@/i18n";

import type { HotelAreaResolveOut, HotelAreaSearchResultOut, HotelSearchOut } from "../types";

export function HotelSearchPanel({
  query,
  city,
  searchMode,
  loading,
  areaQuery,
  areaSuggestions,
  areaResolving,
  areaResolved,
  checkIn,
  checkOut,
  guests,
  areaResults,
  isAreaSearchActive,
  onQueryChange,
  onCityChange,
  onSearchModeChange,
  onSearch,
  onIngest,
  onAreaQueryChange,
  onAreaResolve,
  onSelectArea,
  onCheckInChange,
  onCheckOutChange,
  onGuestsChange,
}: {
  query: string;
  city: string;
  searchMode: "name" | "area";
  loading: boolean;
  areaQuery: string;
  areaSuggestions: HotelAreaResolveOut[];
  areaResolving: boolean;
  areaResolved: HotelAreaResolveOut | null;
  checkIn: string;
  checkOut: string;
  guests: number;
  areaResults: HotelAreaSearchResultOut[];
  isAreaSearchActive: boolean;
  onQueryChange: (value: string) => void;
  onCityChange: (value: string) => void;
  onSearchModeChange: (mode: "name" | "area") => void;
  onSearch: () => void;
  onIngest: () => void;
  onAreaQueryChange: (value: string) => void;
  onAreaResolve: () => void;
  onSelectArea: (area: HotelAreaResolveOut) => void;
  onCheckInChange: (value: string) => void;
  onCheckOutChange: (value: string) => void;
  onGuestsChange: (value: number) => void;
}) {
  const { t } = useI18n();
  const disabled = useMemo(() => loading, [loading]);

  // Debounced area resolve
  useEffect(() => {
    if (searchMode !== "area" || areaQuery.trim().length < 2) return;
    const timer = setTimeout(() => {
      onAreaResolve();
    }, 350);
    return () => clearTimeout(timer);
  }, [areaQuery, searchMode, onAreaResolve]);

  const canSearch = useMemo(() => {
    if (searchMode === "area") {
      return areaResolved !== null && checkIn !== "" && checkOut !== "" && guests > 0;
    }
    return query.trim() !== "" || city.trim() !== "";
  }, [searchMode, areaResolved, checkIn, checkOut, guests, query, city]);

  return (
    <section className="panel hotel-search-panel" aria-label={t("hotels.search.panelLabel")}>
      <div className="panel-header">
        <div>
          <h2 className="panel-title">{t("hotels.search.title")}</h2>
          <p className="panel-subtitle">{t("hotels.search.subtitle")}</p>
        </div>
        <span className="status-pill info">{t("hotels.provider.statusMock")}</span>
      </div>

      {/* ── Search mode toggle ─────────────────────────────────── */}
      <div className="hotel-search-mode-tabs section-gap-sm">
        <button
          type="button"
          className={`hotel-search-mode-tab${searchMode === "name" ? " is-active" : ""}`}
          onClick={() => onSearchModeChange("name")}
        >
          {t("hotels.search.nameMode")}
        </button>
        <button
          type="button"
          className={`hotel-search-mode-tab${searchMode === "area" ? " is-active" : ""}`}
          onClick={() => onSearchModeChange("area")}
        >
          {t("hotels.search.areaMode")}
        </button>
      </div>

      <form
        className="section-gap-sm"
        onSubmit={(event) => {
          event.preventDefault();
          onSearch();
        }}
      >
        {/* ── Name/City mode ───────────────────────────────────── */}
        {searchMode === "name" ? (
          <div className="hotel-search-grid">
            <label className="field qs-label">
              <span>{t("hotels.search.nameLabel")}</span>
              <input
                className="qs-input-neutral"
                value={query}
                onChange={(event) => onQueryChange(event.target.value)}
                placeholder={t("hotels.search.namePlaceholder")}
              />
            </label>
            <label className="field qs-label">
              <span>{t("hotels.search.cityLabel")}</span>
              <input
                className="qs-input-neutral"
                value={city}
                onChange={(event) => onCityChange(event.target.value)}
                placeholder={t("hotels.search.cityPlaceholder")}
              />
            </label>
          </div>
        ) : (
          /* ── Area mode ──────────────────────────────────────── */
          <div className="hotel-search-grid hotel-search-area-grid">
            <label className="field qs-label">
              <span>{t("hotels.search.areaLabel")}</span>
              <div className="hotel-area-autocomplete">
                <input
                  className="qs-input-neutral"
                  value={areaQuery}
                  onChange={(event) => onAreaQueryChange(event.target.value)}
                  placeholder={t("hotels.search.areaPlaceholder")}
                  autoComplete="off"
                />
                {areaResolving ? (
                  <span className="hotel-area-spinner" aria-label={t("shared.states.loading")} />
                ) : null}
                {areaSuggestions.length > 0 ? (
                  <ul className="hotel-area-suggestions" role="listbox">
                    {areaSuggestions.map((suggestion) => (
                      <li key={`${suggestion.latitude}-${suggestion.longitude}`} role="option">
                        <button
                          type="button"
                          className="hotel-area-suggestion-item"
                          onClick={() => onSelectArea(suggestion)}
                        >
                          <strong>{suggestion.area_label}</strong>
                          <span>{suggestion.country_code}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
              {areaResolved ? (
                <span className="hotel-area-resolved-badge">
                  {areaResolved.area_label} · {areaResolved.country_code}
                </span>
              ) : null}
            </label>

            <label className="field qs-label">
              <span>{t("hotels.search.checkInLabel")}</span>
              <input
                type="date"
                className="qs-input-neutral"
                value={checkIn}
                onChange={(event) => onCheckInChange(event.target.value)}
              />
            </label>

            <label className="field qs-label">
              <span>{t("hotels.search.checkOutLabel")}</span>
              <input
                type="date"
                className="qs-input-neutral"
                value={checkOut}
                onChange={(event) => onCheckOutChange(event.target.value)}
              />
            </label>

            <label className="field qs-label">
              <span>{t("hotels.search.guestsLabel")}</span>
              <select
                className="qs-input-neutral"
                value={guests}
                onChange={(event) => onGuestsChange(Number(event.target.value))}
              >
                {[1, 2, 3, 4, 5, 6].map((n) => (
                  <option key={n} value={n}>
                    {n} {t("hotels.search.guestsOption", { count: n })}
                  </option>
                ))}
              </select>
            </label>
          </div>
        )}

        <div className="action-row section-gap-sm">
          <button type="submit" className="btn-primary" disabled={disabled || !canSearch}>
            {loading ? t("shared.states.loading") : t("hotels.actions.search")}
          </button>
          <button type="button" className="btn-secondary" onClick={onIngest} disabled={disabled}>
            {t("hotels.actions.loadMock")}
          </button>
        </div>
      </form>

      {/* ── Area results summary ───────────────────────────────── */}
      {isAreaSearchActive ? (
        <section className="hotel-area-results section-gap-sm">
          <div className="panel-header">
            <h3 className="panel-title">
              {t("hotels.area.resultsTitle", { area: areaResolved?.area_label ?? "" })}
            </h3>
            <span className="status-pill info">{areaResults.length}</span>
          </div>
          <div className="hotel-area-results-list">
            {areaResults.map((result) => (
              <article key={result.hotel_id} className="card hotel-area-result-card">
                <div className="hotel-area-result-main">
                  <strong>{result.canonical_name}</strong>
                  <p className="panel-note">
                    {result.city}, {result.country_code}
                    {" · "}
                    {t("hotels.area.distanceKm", { distance: result.distance_km.toFixed(1) })}
                  </p>
                </div>
                <div className="hotel-area-result-price">
                  {result.lowest_price !== null ? (
                    <strong>
                      {new Intl.NumberFormat("es-ES", {
                        style: "currency",
                        currency: result.currency,
                        maximumFractionDigits: 0,
                      }).format(result.lowest_price)}
                    </strong>
                  ) : (
                    <span className="panel-note">{t("hotels.trackedOffers.noPrice")}</span>
                  )}
                  {result.provider ? (
                    <span className="status-pill info">{result.provider}</span>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}
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
