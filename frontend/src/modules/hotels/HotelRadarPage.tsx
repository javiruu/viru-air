"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { useI18n } from "@/i18n";

import { HotelAlertsPanel } from "./components/HotelAlertsPanel";
import { HotelCompSetPanel, HotelEmptyState } from "./components/HotelCompSetPanel";
import { HotelMyHotelsPanel } from "./components/HotelMyHotelsPanel";
import { HotelResultCard, HotelSearchPanel } from "./components/HotelSearchPanel";
import { HotelSavedSearchesPanel } from "./components/HotelSavedSearchesPanel";
import { HotelTrackingConfirmationDialog } from "./components/HotelTrackingConfirmationDialog";
import { HotelParitySignal, HotelPriceTimeline, HotelProviderStatusPill } from "./components/HotelTimelineAndSignals";
import { HotelTrackedOffersPanel } from "./components/HotelTrackedOffersPanel";
import { HotelRumTracker } from "./HotelRumTracker";
import { HotelWatchlistPanel } from "./components/HotelWatchlistPanel";
import { useHotelAlerts } from "./hooks/useHotelAlerts";
import { useHotelCompSets } from "./hooks/useHotelCompSets";
import { useHotelDetail } from "./hooks/useHotelDetail";
import { useHotelSearch } from "./hooks/useHotelSearch";
import { useHotelWatchlist } from "./hooks/useHotelWatchlist";
import { useSavedHotelSearches } from "./hooks/useSavedHotelSearches";
import { useTrackedOffers } from "./hooks/useTrackedOffers";
import { buildHotelSearchQuery, buildRestoredHotelSearchQuery } from "./hotelSearchUrlState";

export function HotelRadarPage() {
  const { t, localeTag } = useI18n();
  const router = useRouter();
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

  const detail = useHotelDetail(search.selectedHotelId, search.searchIntentId);
  const selectedHotel = search.selectedHotel ?? detail.hotelDetail;
  const trackingHotels = useMemo(
    () => selectedHotel && !search.results.some((hotel) => hotel.id === selectedHotel.id)
      ? [selectedHotel, ...search.results]
      : search.results,
    [search.results, selectedHotel],
  );

  const tracked = useTrackedOffers(
    trackingHotels,
    search.selectedHotelId,
    detail.rates,
  );

  const alerts = useHotelAlerts();
  const savedSearches = useSavedHotelSearches();

  const currentSavedSearchQuery = useMemo(() => {
    const queryString = buildHotelSearchQuery({
      panel: "search",
      mode: search.searchMode,
      query: search.query,
      city: search.city,
      areaQuery: search.areaQuery,
      areaResolved: search.areaResolved,
      checkIn: search.checkIn,
      checkOut: search.checkOut,
      guests: search.guests,
      radiusKm: search.radiusKm,
      useProvider: search.useProvider,
      hasSearched: false,
      selectedHotelId: null,
    });
    return {
      schema: "hotel-search-v1",
      params: Object.fromEntries(new URLSearchParams(queryString)),
    };
  }, [
    search.areaQuery,
    search.areaResolved,
    search.checkIn,
    search.checkOut,
    search.city,
    search.guests,
    search.query,
    search.radiusKm,
    search.searchMode,
    search.useProvider,
  ]);

  function restoreSavedSearch(savedSearch: { query: Record<string, unknown> }) {
    const queryString = buildRestoredHotelSearchQuery(savedSearch.query);
    if (queryString === null) return;
    router.push(`/hoteles${queryString ? `?${queryString}` : ""}`, { scroll: false });
  }

  // ── Derived state ──────────────────────────────────────────────────

  const selectedHotelAlertRules = useMemo(
    () => alerts.alertRules.filter((rule) => rule.hotel_id === search.selectedHotelId),
    [alerts.alertRules, search.selectedHotelId],
  );

  const selectedHotelAlertEvents = useMemo(
    () => alerts.alertEvents.filter((event) => event.hotel_id === search.selectedHotelId),
    [alerts.alertEvents, search.selectedHotelId],
  );
  const latestParitySignal = detail.paritySignals[0] ?? null;
  const isMyHotelsPanel = search.panel === "mis-hoteles";

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
    <>
      <HotelRumTracker />
      <main className="shell hoteles-page" id="main-content">
      <header className="page-header hoteles-header">
        <div className="page-title">
          <h1>{t("hotels.title")}</h1>
          <p>{t("hotels.subtitle")}</p>
        </div>
        <div className="page-actions hotel-provider-context">
          <HotelProviderStatusPill rates={detail.rates} signal={latestParitySignal} />
          <p className="panel-note hotel-provider-context-note">
            {t(search.useProvider ? "hotels.search.providerHintOn" : "hotels.search.providerHintOff")}
          </p>
          <button
            type="button"
            className="btn-secondary btn-compact"
            onClick={() => search.navigatePanel(isMyHotelsPanel ? "search" : "mis-hoteles")}
          >
            {t(isMyHotelsPanel ? "hotels.myHotels.explore" : "hotels.myHotels.title")}
          </button>
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

      {isMyHotelsPanel ? (
        <HotelMyHotelsPanel
          alertEvents={alerts.alertEvents}
          alertEventsError={alerts.alertEventsError}
          alertEventsLoading={alerts.alertEventsLoading}
          busyOfferIds={tracked.trackedBusyOfferIds}
          busyWatchlistHotelIds={watchlist.watchlistBusyHotelIds}
          onExplore={() => search.navigatePanel("search")}
          onOpenHotel={search.selectHotel}
          onRemoveWatch={(itemId, hotelId) => {
            void watchlist.handleRemoveWatch(itemId, hotelId);
          }}
          onSetTrackingActive={(offerId, isActive) => {
            void tracked.handleSetTrackingActive(offerId, isActive);
          }}
          onArchiveTracking={(offerId) => {
            void tracked.handleArchiveTracking(offerId);
          }}
          onStopTracking={(offerId) => {
            void tracked.handleStopTracking(offerId);
          }}
          trackedOffers={tracked.trackedOffers}
          trackedOfferStates={tracked.trackedOfferStates}
          trackedOffersError={tracked.trackedOffersError}
          trackedOffersLoading={tracked.trackedOffersLoading}
          watchlistEntries={watchlist.watchlistEntries}
          watchlistError={watchlist.watchlistError}
          watchlistLoading={watchlist.watchlistLoading}
        />
      ) : (
        <>
      <HotelSearchPanel
        query={search.query}
        city={search.city}
        searchMode={search.searchMode}
        loading={search.loading}
        areaQuery={search.areaQuery}
        areaSuggestions={search.areaSuggestions}
        areaResolving={search.areaResolving}
        areaResolved={search.areaResolved}
        checkIn={search.checkIn}
        checkOut={search.checkOut}
        guests={search.guests}
        areaResults={search.areaResults}
        isAreaSearchActive={search.isAreaSearchActive}
        onQueryChange={search.setQuery}
        onCityChange={search.setCity}
        onSearchModeChange={search.handleSearchModeChange}
        onSearch={search.handleSearch}
        onIngest={search.handleIngest}
        onAreaQueryChange={search.handleAreaQueryChange}
        onAreaResolve={search.handleAreaResolve}
        onSelectArea={search.handleSelectArea}
        onCheckInChange={search.setCheckIn}
        onCheckOutChange={search.setCheckOut}
        onGuestsChange={search.setGuests}
        radiusKm={search.radiusKm}
        onRadiusKmChange={search.setRadiusKm}
        useProvider={search.useProvider}
        onUseProviderChange={search.setUseProvider}
      />

      <HotelSavedSearchesPanel
        searches={savedSearches.savedSearches}
        loading={savedSearches.loading}
        error={savedSearches.error}
        busyId={savedSearches.busyId}
        saving={savedSearches.saving}
        canSave={search.hasSearched && Boolean(search.query || search.city || search.areaResolved)}
        onSave={async (label) => {
          await savedSearches.saveSearch(currentSavedSearchQuery, label);
        }}
        onRestore={restoreSavedSearch}
        onPause={savedSearches.setStatus}
        onDelete={savedSearches.removeSearch}
      />

      {search.errorMessage ? (
        <section
          className={`notice section-gap ${search.featureDisabled ? "notice-info hotel-disabled-notice" : "notice-error"}`}
          role={search.featureDisabled ? "status" : "alert"}
          aria-live={search.featureDisabled ? "polite" : "assertive"}
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
                  onSelect={search.selectHotel}
                  onAddWatch={watchlist.handleAddWatch}
                  onRemoveWatch={(hotelId) => {
                    const item = watchlist.watchlistItems.find((entry) => entry.hotel_id === hotelId);
                    if (item) {
                      void watchlist.handleRemoveWatch(item.id, hotelId);
                    }
                  }}
                  onTrackPrice={(hotelId) => {
                    if (hotelId !== search.selectedHotelId) {
                      search.selectHotel(hotelId);
                      return;
                    }
                    tracked.handleTrackPrice(hotelId);
                  }}
                  trackedBusy={tracked.trackedBusyHotelIds.includes(hotel.id)}
                  trackingDisabled={tracked.trackedBusyHotelIds.length > 0}
                  hasTracking={tracked.trackedHotelIds.includes(hotel.id)}
                />
              ))}
              {search.results.length === 0 && !search.loading && !search.errorMessage ? (
                <HotelEmptyState variant={search.hasSearched ? "empty" : "idle"} />
              ) : null}
              {search.loading ? <p className="panel-note">{t("shared.states.loading")}</p> : null}
            </div>
          </section>

          <HotelTrackedOffersPanel
            offers={tracked.trackedOffers}
            loading={tracked.trackedOffersLoading}
            error={tracked.trackedOffersError}
            onSetTrackingActive={(offerId, isActive) => {
              void tracked.handleSetTrackingActive(offerId, isActive);
            }}
            onArchiveTracking={(offerId) => {
              void tracked.handleArchiveTracking(offerId);
            }}
            onStopTracking={(offerId) => {
              void tracked.handleStopTracking(offerId);
            }}
            busyOfferIds={tracked.trackedBusyOfferIds}
            statesByOfferId={tracked.trackedOfferStates}
          />

          <HotelPriceTimeline
            rates={detail.rates}
            onTrackRate={tracked.handleTrackRate}
            selectedRateId={tracked.trackingCandidate?.rate.id ?? null}
            trackingDisabled={tracked.trackedBusyHotelIds.length > 0}
          />
        </div>

        <aside className="hoteles-side-column">
          <section className={`panel panel-soft${collapsedPanels["detail"] ? " is-collapsed" : ""}`}>
            <button
              type="button"
              className="panel-collapse-toggle"
              onClick={() => toggleCollapse("detail")}
              aria-expanded={!collapsedPanels["detail"]}
              aria-controls="hotel-detail-panel"
            >
              <h2 className="panel-title">{t("hotels.selected.title")}</h2>
              <span className="collapse-icon">{collapsedPanels["detail"] ? "+" : "−"}</span>
            </button>
            <div id="hotel-detail-panel" hidden={collapsedPanels["detail"]}>
              {!collapsedPanels["detail"] ? (
                <>
                  {selectedHotel ? (
                    <div className="section-gap-sm hotel-selected-meta">
                      <strong>{selectedHotel.canonical_name}</strong>
                      <p className="panel-note hotel-selected-location">
                        {selectedHotel.city}, {selectedHotel.country_code}
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
            </div>
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
              aria-controls="hotel-parity-panel"
            >
              <h2 className="panel-title">{t("hotels.parity.title")}</h2>
              <span className="collapse-icon">{collapsedPanels["parity"] ? "+" : "−"}</span>
            </button>
            <div id="hotel-parity-panel" hidden={collapsedPanels["parity"]}>
              {!collapsedPanels["parity"] ? (
                <HotelParitySignal
                  signals={detail.paritySignals}
                  rates={detail.rates}
                  loading={detail.parityLoading}
                  error={detail.parityError}
                />
              ) : null}
            </div>
          </section>

          <section className={`panel panel-soft${collapsedPanels["alerts"] ? " is-collapsed" : ""}`}>
            <button
              type="button"
              className="panel-collapse-toggle"
              onClick={() => toggleCollapse("alerts")}
              aria-expanded={!collapsedPanels["alerts"]}
              aria-controls="hotel-alerts-panel"
            >
              <h2 className="panel-title">{t("hotels.alerts.title")}</h2>
              <span className="collapse-icon">{collapsedPanels["alerts"] ? "+" : "−"}</span>
            </button>
            <div id="hotel-alerts-panel" hidden={collapsedPanels["alerts"]}>
              {!collapsedPanels["alerts"] ? (
                <HotelAlertsPanel
                  selectedHotel={selectedHotel}
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
            </div>
          </section>

          <section className={`panel panel-soft${collapsedPanels["compSet"] ? " is-collapsed" : ""}`}>
            <button
              type="button"
              className="panel-collapse-toggle"
              onClick={() => toggleCollapse("compSet")}
              aria-expanded={!collapsedPanels["compSet"]}
              aria-controls="hotel-compset-panel"
            >
              <h2 className="panel-title">{t("hotels.compSet.title")}</h2>
              <span className="collapse-icon">{collapsedPanels["compSet"] ? "+" : "−"}</span>
            </button>
            <div id="hotel-compset-panel" hidden={collapsedPanels["compSet"]}>
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
                  onDeleteCompSet={compSets.handleDeleteCompSet}
                />
              ) : null}
            </div>
          </section>
        </aside>
      </section>
        </>
      )}
      </main>
      <HotelTrackingConfirmationDialog
        candidate={isMyHotelsPanel ? null : tracked.trackingCandidate}
        submitting={tracked.trackedBusyHotelIds.length > 0}
        onClose={tracked.handleCloseTrackingConfirmation}
        onConfirm={() => {
          void tracked.handleConfirmTracking();
        }}
      />
    </>
  );
}
