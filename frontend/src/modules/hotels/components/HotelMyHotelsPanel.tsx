"use client";

import { useI18n } from "@/i18n";

import type { HotelAlertEventOut, HotelTrackedOfferOut, HotelTrackedOfferV2State, HotelWatchlistEntry } from "../types";
import { HotelTrackedOffersPanel } from "./HotelTrackedOffersPanel";
import { HotelWatchlistPanel } from "./HotelWatchlistPanel";

type HotelMyHotelsPanelProps = {
  readonly alertEvents: HotelAlertEventOut[];
  readonly alertEventsError: string | null;
  readonly alertEventsLoading: boolean;
  readonly busyOfferIds: string[];
  readonly busyWatchlistHotelIds: string[];
  readonly onExplore: () => void;
  readonly onOpenHotel: (hotelId: string) => void;
  readonly onRemoveWatch: (itemId: string, hotelId: string) => void;
  readonly onSetTrackingActive: (offerId: string, isActive: boolean) => void;
  readonly onArchiveTracking: (offerId: string) => void;
  readonly onStopTracking: (offerId: string) => void;
  readonly trackedOffers: HotelTrackedOfferOut[];
  readonly trackedOfferStates: Readonly<Record<string, HotelTrackedOfferV2State>>;
  readonly trackedOffersError: string | null;
  readonly trackedOffersLoading: boolean;
  readonly watchlistEntries: HotelWatchlistEntry[];
  readonly watchlistError: string | null;
  readonly watchlistLoading: boolean;
};

function formatEventDate(value: string, localeTag: string): string {
  return new Date(value).toLocaleString(localeTag, { dateStyle: "medium", timeStyle: "short" });
}

export function HotelMyHotelsPanel({
  alertEvents,
  alertEventsError,
  alertEventsLoading,
  busyOfferIds,
  busyWatchlistHotelIds,
  onExplore,
  onOpenHotel,
  onRemoveWatch,
  onSetTrackingActive,
  onArchiveTracking,
  onStopTracking,
  trackedOffers,
  trackedOfferStates,
  trackedOffersError,
  trackedOffersLoading,
  watchlistEntries,
  watchlistError,
  watchlistLoading,
}: HotelMyHotelsPanelProps) {
  const { localeTag, t } = useI18n();
  const hasVisibleItems = trackedOffers.length > 0 || alertEvents.length > 0 || watchlistEntries.length > 0;
  const loading = trackedOffersLoading || alertEventsLoading || watchlistLoading;
  const hasError = alertEventsError !== null || trackedOffersError !== null || watchlistError !== null;

  return (
    <section className="hotel-my-hotels-panel section-gap" aria-labelledby="hotel-my-hotels-title">
      <header className="hotel-my-hotels-header">
        <div>
          <p className="hotel-my-hotels-eyebrow">{t("hotels.myHotels.eyebrow")}</p>
          <h2 id="hotel-my-hotels-title">{t("hotels.myHotels.title")}</h2>
          <p className="panel-note">{t("hotels.myHotels.subtitle")}</p>
        </div>
        <button type="button" className="btn-secondary btn-compact" onClick={onExplore}>
          {t("hotels.myHotels.explore")}
        </button>
      </header>

      {hasError ? (
        <p className="notice notice-error" role="alert">
          {alertEventsError ?? trackedOffersError ?? watchlistError}
        </p>
      ) : null}

      {!loading && !hasError && !hasVisibleItems ? (
        <section className="hotel-my-hotels-empty panel panel-soft">
          <h3>{t("hotels.myHotels.emptyTitle")}</h3>
          <p className="panel-note">{t("hotels.myHotels.emptyBody")}</p>
          <button type="button" className="btn-primary btn-compact" onClick={onExplore}>
            {t("hotels.myHotels.explore")}
          </button>
        </section>
      ) : (
        <div className="hotel-my-hotels-sections">
          {trackedOffersLoading || trackedOffersError || trackedOffers.length > 0 ? (
            <HotelTrackedOffersPanel
              offers={trackedOffers}
              loading={trackedOffersLoading}
              error={trackedOffersError}
              onSetTrackingActive={onSetTrackingActive}
              onArchiveTracking={onArchiveTracking}
              onStopTracking={onStopTracking}
              busyOfferIds={busyOfferIds}
              statesByOfferId={trackedOfferStates}
            />
          ) : null}

          {alertEventsLoading || alertEvents.length > 0 || alertEventsError ? (
            <section className="panel panel-soft hotel-my-hotels-alerts" aria-labelledby="hotel-my-hotels-alerts-title">
              <div className="panel-header">
                <h3 id="hotel-my-hotels-alerts-title" className="panel-title">{t("hotels.myHotels.alertsTitle")}</h3>
                <span className="status-pill info">{alertEvents.length}</span>
              </div>
              {alertEventsLoading ? <p className="panel-note section-gap-sm">{t("hotels.alerts.loadingEvents")}</p> : null}
              {!alertEventsLoading && !alertEventsError ? (
                <div className="hotel-my-hotels-alert-list section-gap-sm">
                  {alertEvents.map((event) => (
                    <article key={event.id} className="hotel-my-hotels-alert-item">
                      <div>
                        <strong>{event.message}</strong>
                        <p className="panel-note">{formatEventDate(event.created_at, localeTag)}</p>
                      </div>
                      <button type="button" className="btn-ghost btn-compact" onClick={() => onOpenHotel(event.hotel_id)}>
                        {t("hotels.myHotels.review")}
                      </button>
                    </article>
                  ))}
                </div>
              ) : null}
            </section>
          ) : null}

          {watchlistLoading || watchlistEntries.length > 0 || watchlistError ? (
            <HotelWatchlistPanel
              entries={watchlistEntries}
              loading={watchlistLoading}
              error={watchlistError}
              busyHotelIds={busyWatchlistHotelIds}
              onRemove={onRemoveWatch}
            />
          ) : null}
        </div>
      )}
    </section>
  );
}
