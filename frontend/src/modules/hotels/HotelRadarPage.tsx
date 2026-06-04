"use client";

import { useEffect, useMemo, useState } from "react";

import { useI18n } from "@/i18n";

import { HotelAlertsPanel } from "./components/HotelAlertsPanel";
import { HotelCompSetPanel, HotelEmptyState } from "./components/HotelCompSetPanel";
import { HotelResultCard, HotelSearchPanel } from "./components/HotelSearchPanel";
import { HotelParitySignal, HotelPriceTimeline, HotelProviderStatusPill } from "./components/HotelTimelineAndSignals";
import { HotelTrackedOffersPanel } from "./components/HotelTrackedOffersPanel";
import { HotelWatchlistPanel } from "./components/HotelWatchlistPanel";
import { useHotelAlerts } from "./hooks/useHotelAlerts";
import { useHotelCompSets } from "./hooks/useHotelCompSets";
import { useHotelDetail } from "./hooks/useHotelDetail";
import { useHotelSearch } from "./hooks/useHotelSearch";
import { useHotelWatchlist } from "./hooks/useHotelWatchlist";
import { useTrackedOffers } from "./hooks/useTrackedOffers";

export function HotelRadarPage() {
  const { t, localeTag } = useI18n();
  const [collapsedPanels, setCollapsedPanels] = useState<Record<string, boolean>>({});

  // ── Hooks ──────────────────────────────────────────────────────────

  const watchlist = useHotelWatchlist();
  const compSets = useHotelCompSets();

  const search = useHotelSearch(async () => {
    if (watchlist.watchlistItems.length > 0) {
      await watchlist.hydrateWatchlistHotels(watchlist.watchlistItems);
    }
    await compSets.refreshCompSets();
  });

  const detail = useHotelDetail(search.selectedHotelId);

  const tracked = useTrackedOffers(
    search.results,
    search.selectedHotelId,
    detail.rates,
  );

  const alerts = useHotelAlerts();

  // ── Derived state ──────────────────────────────────────────────────

  const selectedHotelAlertRules = useMemo(
    () => alerts.alertRules.filter((rule) => rule.hotel_id === search.selectedHotelId),
    [alerts.alertRules, search.selectedHotelId],
  );

  const selectedHotelAlertEvents = useMemo(
    () => alerts.alertEvents.filter((event) => event.hotel_id === search.selectedHotelId),
    [alerts.alertEvents, search.selectedHotelId],
  );

  function toggleCollapse(key: string) {
    setCollapsedPanels((current) => ({ ...current, [key]: !current[key] }));
  }

  // ── Side effects ───────────────────────────────────────────────────

  useEffect(() => {
    compSets.refreshCompSets().catch(() => undefined);
    watchlist.refreshWatchlist().catch(() => undefined);
    alerts.refreshAlertRules().catch(() => undefined);
    tracked.refreshTrackedOffers().catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    alerts.refreshAlertEvents(search.selectedHotelId).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search.selectedHotelId]);

  // Sync detail hotel into watchlist cache
  useEffect(() => {
    if (detail.hotelDetail) {
      watchlist.setWatchlistHotelCache((current) => ({
        ...current,
        [detail.hotelDetail!.id]: detail.hotelDetail!,
      }));
      watchlist.setWatchlistUnavailableHotelIds((current) =>
        current.filter((hotelId) => hotelId !== detail.hotelDetail!.id),
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail.hotelDetail]);

  // ── Render ─────────────────────────────────────────────────────────

  return (
    <main className="shell hoteles-page" id="main-content">
      <header className="page-header hoteles-header">
        <div className="page-title">
          <h1>{t("hotels.title")}</h1>
          <p>{t("hotels.subtitle")}</p>
        </div>
        <div className="page-actions">
          <HotelProviderStatusPill rates={detail.rates} />
        </div>
      </header>

      <section className="hotel-overview-strip section-gap-sm" aria-label={t("hotels.title")}>
        <article className="hotel-overview-card">
          <span>{t("hotels.overview.hotels")}</span>
          <strong>{search.results.length}</strong>
        </article>
        <article className="hotel-overview-card">
          <span>{t("hotels.overview.tracking")}</span>
          <strong>{tracked.trackedOffers.filter((o) => o.is_active).length}</strong>
        </article>
        <article className="hotel-overview-card">
          <span>{t("hotels.overview.watchlist")}</span>
          <strong>{watchlist.watchlistItems.length}</strong>
        </article>
      </section>

      <HotelSearchPanel
        query={search.query}
        city={search.city}
        loading={search.loading}
        onQueryChange={search.setQuery}
        onCityChange={search.setCity}
        onSearch={search.handleSearch}
        onIngest={search.handleIngest}
      />

      {search.errorMessage ? (
        <section
          className={`notice section-gap ${search.featureDisabled ? "notice-info hotel-disabled-notice" : "notice-error"}`}
          role="status"
        >
          {search.errorMessage}
        </section>
      ) : null}

      <section className="hoteles-layout section-gap">
        <div className="hoteles-main-column">
          <section
            className={`panel panel-soft hotel-results-panel${search.results.length === 0 ? " is-empty" : ""}`}
          >
            <div className="panel-header">
              <h2 className="panel-title">{t("hotels.results.title")}</h2>
              <span className="status-pill info">{search.results.length}</span>
            </div>
            <div className="hotel-results-list section-gap-sm">
              {search.results.map((hotel) => (
                <HotelResultCard
                  key={hotel.id}
                  hotel={hotel}
                  isActive={hotel.id === search.selectedHotelId}
                  isInWatchlist={watchlist.watchlistHotelIds.includes(hotel.id)}
                  watchlistBusy={watchlist.watchlistBusyHotelIds.includes(hotel.id)}
                  onSelect={search.setSelectedHotelId}
                  onAddWatch={watchlist.handleAddWatch}
                  onRemoveWatch={(hotelId) => {
                    const item = watchlist.watchlistItems.find((entry) => entry.hotel_id === hotelId);
                    if (item) {
                      void watchlist.handleRemoveWatch(item.id, hotelId);
                    }
                  }}
                  onTrackPrice={tracked.handleTrackPrice}
                  trackedBusy={tracked.trackedBusyHotelIds.includes(hotel.id)}
                  hasTracking={tracked.trackedHotelIds.includes(hotel.id)}
                />
              ))}
              {search.results.length === 0 && !search.loading ? <HotelEmptyState /> : null}
              {search.loading ? <p className="panel-note">{t("shared.states.loading")}</p> : null}
            </div>
          </section>

          <HotelTrackedOffersPanel
            offers={tracked.trackedOffers}
            loading={tracked.trackedOffersLoading}
            onStopTracking={(offerId) => {
              void tracked.handleStopTracking(offerId);
            }}
            busyOfferIds={tracked.trackedBusyOfferIds}
          />

          <HotelPriceTimeline rates={detail.rates} />
        </div>

        <aside className="hoteles-side-column">
          <section className={`panel panel-soft${collapsedPanels["detail"] ? " is-collapsed" : ""}`}>
            <button
              type="button"
              className="panel-collapse-toggle"
              onClick={() => toggleCollapse("detail")}
              aria-expanded={!collapsedPanels["detail"]}
            >
              <h2 className="panel-title">{t("hotels.selected.title")}</h2>
              <span className="collapse-icon">{collapsedPanels["detail"] ? "+" : "−"}</span>
            </button>
            {!collapsedPanels["detail"] ? (
              <>
                {search.selectedHotel ? (
                  <div className="section-gap-sm hotel-selected-meta">
                    <strong>{search.selectedHotel.canonical_name}</strong>
                    <p className="panel-note hotel-selected-location">
                      {search.selectedHotel.city}, {search.selectedHotel.country_code}
                    </p>
                    {detail.hotelDetail?.address ? (
                      <p className="panel-note">{detail.hotelDetail.address}</p>
                    ) : null}
                    {detail.hotelDetail?.updated_at ? (
                      <p className="panel-note">
                        {t("hotels.selected.lastCapture")}:{" "}
                        {new Date(detail.hotelDetail.updated_at).toLocaleString(localeTag)}
                      </p>
                    ) : null}
                  </div>
                ) : (
                  <p className="panel-note section-gap-sm">{t("hotels.selected.empty")}</p>
                )}
                {detail.loadingRates ? (
                  <p className="panel-note section-gap-sm">{t("shared.states.loading")}</p>
                ) : null}
              </>
            ) : null}
          </section>

          <HotelWatchlistPanel
            entries={watchlist.watchlistEntries}
            loading={watchlist.watchlistLoading}
            error={watchlist.watchlistError}
            busyHotelIds={watchlist.watchlistBusyHotelIds}
            onRemove={(itemId, hotelId) => {
              void watchlist.handleRemoveWatch(itemId, hotelId);
            }}
          />

          <section className={`panel panel-soft${collapsedPanels["parity"] ? " is-collapsed" : ""}`}>
            <button
              type="button"
              className="panel-collapse-toggle"
              onClick={() => toggleCollapse("parity")}
              aria-expanded={!collapsedPanels["parity"]}
            >
              <h2 className="panel-title">{t("hotels.parity.title")}</h2>
              <span className="collapse-icon">{collapsedPanels["parity"] ? "+" : "−"}</span>
            </button>
            {!collapsedPanels["parity"] ? (
              <HotelParitySignal
                signals={detail.paritySignals}
                loading={detail.parityLoading}
                error={detail.parityError}
              />
            ) : null}
          </section>

          <section className={`panel panel-soft${collapsedPanels["alerts"] ? " is-collapsed" : ""}`}>
            <button
              type="button"
              className="panel-collapse-toggle"
              onClick={() => toggleCollapse("alerts")}
              aria-expanded={!collapsedPanels["alerts"]}
            >
              <h2 className="panel-title">{t("hotels.alerts.title")}</h2>
              <span className="collapse-icon">{collapsedPanels["alerts"] ? "+" : "−"}</span>
            </button>
            {!collapsedPanels["alerts"] ? (
              <HotelAlertsPanel
                selectedHotel={search.selectedHotel}
                rules={selectedHotelAlertRules}
                rulesLoading={alerts.alertRulesLoading}
                rulesError={alerts.alertRulesError}
                events={selectedHotelAlertEvents}
                eventsLoading={alerts.alertEventsLoading}
                eventsError={alerts.alertEventsError}
                createBusy={alerts.alertCreateBusy}
                busyRuleIds={alerts.alertBusyRuleIds}
                onCreateRule={alerts.handleCreateAlertRule}
                onToggleRule={(ruleId, isActive) => {
                  void alerts.handleToggleAlertRule(ruleId, isActive);
                }}
                onDeleteRule={(ruleId) => {
                  void alerts.handleDeleteAlertRule(ruleId);
                }}
              />
            ) : null}
          </section>

          <section className={`panel panel-soft${collapsedPanels["compSet"] ? " is-collapsed" : ""}`}>
            <button
              type="button"
              className="panel-collapse-toggle"
              onClick={() => toggleCollapse("compSet")}
              aria-expanded={!collapsedPanels["compSet"]}
            >
              <h2 className="panel-title">{t("hotels.compSet.title")}</h2>
              <span className="collapse-icon">{collapsedPanels["compSet"] ? "+" : "−"}</span>
            </button>
            {!collapsedPanels["compSet"] ? (
              <HotelCompSetPanel
                compSets={compSets.compSets}
                selectedCompSet={compSets.selectedCompSet}
                anchorDetail={compSets.compSetAnchorDetail}
                anchorLoading={compSets.anchorLoading}
                anchorError={compSets.anchorError}
                hotels={search.results}
                selectedHotelId={search.selectedHotelId}
                nearbySuggestions={compSets.nearbySuggestions}
                nearbyLoading={compSets.nearbyLoading}
                nearbyMessage={compSets.nearbyMessage}
                onCreateCompSet={compSets.handleCreateCompSet}
                onSelectCompSet={compSets.handleSelectCompSet}
                onAddMember={compSets.handleAddMember}
                onDeleteMember={compSets.handleDeleteMember}
              />
            ) : null}
          </section>
        </aside>
      </section>
    </main>
  );
}
