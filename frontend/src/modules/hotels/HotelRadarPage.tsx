"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { useI18n } from "@/i18n";

import {
  addHotelCompSetMember,
  createHotelAlertRule,
  createHotelCompSet,
  createHotelWatchlistItem,
  deleteHotelAlertRule,
  deleteHotelCompSetMember,
  deleteHotelWatchlistItem,
  getHotelCompSetDetail,
  getHotelDetail,
  getHotelNearbySuggestions,
  getHotelParity,
  getHotelRates,
  HotelsRequestError,
  ingestHotelsMock,
  listHotelAlertEvents,
  listHotelAlertRules,
  listHotelCompSets,
  listHotelWatchlist,
  searchHotels,
  updateHotelAlertRule,
} from "./api";
import { HotelAlertsPanel } from "./components/HotelAlertsPanel";
import { HotelCompSetPanel, HotelEmptyState } from "./components/HotelCompSetPanel";
import { HotelResultCard, HotelSearchPanel } from "./components/HotelSearchPanel";
import { HotelParitySignal, HotelPriceTimeline, HotelProviderStatusPill } from "./components/HotelTimelineAndSignals";
import { HotelWatchlistPanel } from "./components/HotelWatchlistPanel";
import type {
  HotelAlertEventOut,
  HotelAlertRuleOut,
  HotelAlertRuleType,
  HotelCompSetDetailOut,
  HotelCompSetOut,
  HotelDetailOut,
  HotelNearbySuggestionOut,
  HotelParityOut,
  HotelRateOut,
  HotelSearchOut,
  HotelWatchlistEntry,
  HotelWatchlistItemOut,
} from "./types";

function resolveHotelMessage(error: unknown, t: ReturnType<typeof useI18n>["t"]): string {
  if (error instanceof HotelsRequestError) {
    if (error.message.includes("HOTEL_FEATURE_ENABLED")) {
      return t("hotels.messages.featureDisabled");
    }
    if (error.message === "hotel_comp_set_member_already_exists") {
      return t("hotels.messages.memberAlreadyAdded");
    }
    if (error.message === "hotel_comp_set_anchor_cannot_be_member") {
      return t("hotels.messages.anchorCannotBeMember");
    }
    if (error.message === "hotel_not_found") {
      return t("hotels.messages.hotelNotFound");
    }
    if (error.message === "hotel_watchlist_item_already_exists") {
      return t("hotels.messages.watchAlreadyAdded");
    }
    if (error.message === "threshold_required_for_price_rule") {
      return t("hotels.alerts.validation.priceThresholdRequired");
    }
    if (error.message === "threshold_percent_required_for_parity_break") {
      return t("hotels.alerts.validation.parityThresholdRequired");
    }
    if (error.message === "threshold_amount_not_allowed_for_parity_break") {
      return t("hotels.alerts.validation.parityAmountNotAllowed");
    }
    return error.message;
  }
  if (error instanceof Error && error.message.includes("HOTEL_FEATURE_ENABLED")) {
    return t("hotels.messages.featureDisabled");
  }
  return error instanceof Error ? error.message : t("shared.errors.generic");
}

export function HotelRadarPage() {
  const { t, localeTag } = useI18n();
  const { notify } = useNotificationCenter();

  const [query, setQuery] = useState("");
  const [city, setCity] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<HotelSearchOut[]>([]);
  const [selectedHotelId, setSelectedHotelId] = useState<string | null>(null);
  const [rates, setRates] = useState<HotelRateOut[]>([]);
  const [hotelDetail, setHotelDetail] = useState<HotelDetailOut | null>(null);
  const [loadingRates, setLoadingRates] = useState(false);
  const [paritySignals, setParitySignals] = useState<HotelParityOut[]>([]);
  const [parityLoading, setParityLoading] = useState(false);
  const [parityError, setParityError] = useState<string | null>(null);
  const [watchlistItems, setWatchlistItems] = useState<HotelWatchlistItemOut[]>([]);
  const [watchlistLoading, setWatchlistLoading] = useState(false);
  const [watchlistError, setWatchlistError] = useState<string | null>(null);
  const [watchlistHotelCache, setWatchlistHotelCache] = useState<Record<string, HotelDetailOut>>({});
  const [watchlistUnavailableHotelIds, setWatchlistUnavailableHotelIds] = useState<string[]>([]);
  const [watchlistBusyHotelIds, setWatchlistBusyHotelIds] = useState<string[]>([]);
  const watchlistHotelCacheRef = useRef<Record<string, HotelDetailOut>>({});
  const [compSets, setCompSets] = useState<HotelCompSetOut[]>([]);
  const [selectedCompSet, setSelectedCompSet] = useState<HotelCompSetDetailOut | null>(null);
  const [compSetAnchorDetail, setCompSetAnchorDetail] = useState<HotelDetailOut | null>(null);
  const [anchorLoading, setAnchorLoading] = useState(false);
  const [anchorError, setAnchorError] = useState<string | null>(null);
  const [anchorCache, setAnchorCache] = useState<Record<string, HotelDetailOut>>({});
  const [nearbySuggestions, setNearbySuggestions] = useState<HotelNearbySuggestionOut[]>([]);
  const [nearbyLoading, setNearbyLoading] = useState(false);
  const [nearbyMessage, setNearbyMessage] = useState<string | null>(null);
  const [alertRules, setAlertRules] = useState<HotelAlertRuleOut[]>([]);
  const [alertRulesLoading, setAlertRulesLoading] = useState(false);
  const [alertRulesError, setAlertRulesError] = useState<string | null>(null);
  const [alertEvents, setAlertEvents] = useState<HotelAlertEventOut[]>([]);
  const [alertEventsLoading, setAlertEventsLoading] = useState(false);
  const [alertEventsError, setAlertEventsError] = useState<string | null>(null);
  const [alertCreateBusy, setAlertCreateBusy] = useState(false);
  const [alertBusyRuleIds, setAlertBusyRuleIds] = useState<string[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const selectedHotel = useMemo(() => results.find((item) => item.id === selectedHotelId) ?? null, [results, selectedHotelId]);
  const featureDisabled = Boolean(errorMessage && errorMessage.includes("HOTEL_FEATURE_ENABLED"));
  const watchlistHotelIds = useMemo(() => watchlistItems.map((item) => item.hotel_id), [watchlistItems]);
  const selectedHotelAlertRules = useMemo(
    () => alertRules.filter((rule) => rule.hotel_id === selectedHotelId),
    [alertRules, selectedHotelId],
  );
  const selectedHotelAlertEvents = useMemo(
    () => alertEvents.filter((event) => event.hotel_id === selectedHotelId),
    [alertEvents, selectedHotelId],
  );
  const watchlistEntries = useMemo<HotelWatchlistEntry[]>(
    () =>
      watchlistItems.map((item) => ({
        item,
        hotel: watchlistHotelCache[item.hotel_id] ?? null,
        detailUnavailable: watchlistUnavailableHotelIds.includes(item.hotel_id),
      })),
    [watchlistHotelCache, watchlistItems, watchlistUnavailableHotelIds],
  );

  useEffect(() => {
    watchlistHotelCacheRef.current = watchlistHotelCache;
  }, [watchlistHotelCache]);

  async function hydrateWatchlistHotels(items: HotelWatchlistItemOut[]) {
    const missingHotelIds = Array.from(
      new Set(items.map((item) => item.hotel_id).filter((hotelId) => !watchlistHotelCacheRef.current[hotelId])),
    );

    if (missingHotelIds.length === 0) return;

    const results = await Promise.allSettled(missingHotelIds.map((hotelId) => getHotelDetail(hotelId)));
    const nextCache: Record<string, HotelDetailOut> = {};
    const failedHotelIds: string[] = [];

    results.forEach((result, index) => {
      const hotelId = missingHotelIds[index];
      if (result.status === "fulfilled") {
        nextCache[hotelId] = result.value;
      } else {
        failedHotelIds.push(hotelId);
      }
    });

    const successfulHotelIds = Object.keys(nextCache);
    if (successfulHotelIds.length > 0) {
      setWatchlistHotelCache((current) => ({ ...current, ...nextCache }));
      setWatchlistUnavailableHotelIds((current) => current.filter((hotelId) => !successfulHotelIds.includes(hotelId)));
    }
    if (failedHotelIds.length > 0) {
      setWatchlistUnavailableHotelIds((current) => Array.from(new Set([...current, ...failedHotelIds])));
    }
  }

  async function refreshWatchlist() {
    setWatchlistLoading(true);
    setWatchlistError(null);
    try {
      const items = await listHotelWatchlist();
      setWatchlistItems(items);
      await hydrateWatchlistHotels(items);
    } catch (error) {
      setWatchlistError(resolveHotelMessage(error, t) || t("hotels.messages.watchlistLoadError"));
    } finally {
      setWatchlistLoading(false);
    }
  }

  function markWatchlistBusy(hotelId: string, isBusy: boolean) {
    setWatchlistBusyHotelIds((current) => {
      if (isBusy) return current.includes(hotelId) ? current : [...current, hotelId];
      return current.filter((item) => item !== hotelId);
    });
  }

  async function refreshCompSets() {
    const next = await listHotelCompSets();
    setCompSets(next);
  }

  const refreshAlertRules = useCallback(async () => {
    setAlertRulesLoading(true);
    setAlertRulesError(null);
    try {
      const items = await listHotelAlertRules();
      setAlertRules(items);
    } catch (error) {
      setAlertRulesError(resolveHotelMessage(error, t) || t("hotels.alerts.loadRulesError"));
    } finally {
      setAlertRulesLoading(false);
    }
  }, [t]);

  const refreshAlertEvents = useCallback(async (hotelId?: string | null) => {
    setAlertEventsLoading(true);
    setAlertEventsError(null);
    try {
      if (!hotelId) {
        setAlertEvents([]);
        return;
      }
      const items = await listHotelAlertEvents({ hotel_id: hotelId, limit: 50 });
      setAlertEvents(items);
    } catch (error) {
      setAlertEventsError(resolveHotelMessage(error, t) || t("hotels.alerts.loadEventsError"));
    } finally {
      setAlertEventsLoading(false);
    }
  }, [t]);

  function markAlertRuleBusy(ruleId: string, isBusy: boolean) {
    setAlertBusyRuleIds((current) => {
      if (isBusy) return current.includes(ruleId) ? current : [...current, ruleId];
      return current.filter((item) => item !== ruleId);
    });
  }

  async function runSearch() {
    const list = await searchHotels({ q: query || undefined, city: city || undefined, limit: 30 });
    setResults(list);
    if (!list.some((item) => item.id === selectedHotelId)) {
      setSelectedHotelId(list[0]?.id ?? null);
    }
  }

  async function handleSearch() {
    setLoading(true);
    setErrorMessage(null);
    try {
      await runSearch();
    } catch (error) {
      const message = resolveHotelMessage(error, t);
      setErrorMessage(message);
      notify({ tone: "error", title: message });
    } finally {
      setLoading(false);
    }
  }

  async function handleIngest() {
    setLoading(true);
    setErrorMessage(null);
    try {
      const ingest = await ingestHotelsMock();
      notify({
        tone: "success",
        title: t("hotels.messages.ingestSuccess", { count: ingest.hotels_processed }),
      });
      await runSearch();
      if (watchlistItems.length > 0) {
        await hydrateWatchlistHotels(watchlistItems);
      }
      await refreshCompSets();
    } catch (error) {
      const message = resolveHotelMessage(error, t);
      setErrorMessage(message);
      notify({ tone: "error", title: message });
    } finally {
      setLoading(false);
    }
  }

  async function handleAddWatch(hotelId: string) {
    markWatchlistBusy(hotelId, true);
    try {
      await createHotelWatchlistItem({ hotel_id: hotelId, label: t("hotels.watchlist.defaultLabel") });
      await refreshWatchlist();
      notify({ tone: "success", title: t("hotels.messages.watchAdded") });
    } catch (error) {
      const message = resolveHotelMessage(error, t);
      if (error instanceof HotelsRequestError && error.message === "hotel_watchlist_item_already_exists") {
        await refreshWatchlist();
      }
      notify({ tone: "error", title: message });
    } finally {
      markWatchlistBusy(hotelId, false);
    }
  }

  async function handleRemoveWatch(itemId: string, hotelId: string) {
    markWatchlistBusy(hotelId, true);
    try {
      await deleteHotelWatchlistItem(itemId);
      await refreshWatchlist();
      notify({ tone: "success", title: t("hotels.messages.watchRemoved") });
    } catch (error) {
      const message = resolveHotelMessage(error, t);
      notify({ tone: "error", title: message });
    } finally {
      markWatchlistBusy(hotelId, false);
    }
  }

  async function handleCreateCompSet(name: string, anchorHotelId: string) {
    try {
      const created = await createHotelCompSet({ name, anchor_hotel_id: anchorHotelId });
      await refreshCompSets();
      const detail = await getHotelCompSetDetail(created.id);
      setSelectedCompSet(detail);
      notify({ tone: "success", title: t("hotels.messages.compSetCreated") });
    } catch (error) {
      const message = error instanceof Error ? error.message : t("shared.errors.generic");
      notify({ tone: "error", title: message });
    }
  }

  async function handleSelectCompSet(compSetId: string) {
    try {
      const detail = await getHotelCompSetDetail(compSetId);
      setSelectedCompSet(detail);
    } catch (error) {
      const message = error instanceof Error ? error.message : t("shared.errors.generic");
      notify({ tone: "error", title: message });
    }
  }

  async function handleAddMember(compSetId: string, hotelId: string) {
    try {
      await addHotelCompSetMember(compSetId, { hotel_id: hotelId });
      const detail = await getHotelCompSetDetail(compSetId);
      setSelectedCompSet(detail);
      notify({ tone: "success", title: t("hotels.messages.memberAdded") });
    } catch (error) {
      const message = resolveHotelMessage(error, t);
      notify({ tone: "error", title: message });
    }
  }

  async function handleDeleteMember(compSetId: string, memberId: string) {
    try {
      await deleteHotelCompSetMember(compSetId, memberId);
      const detail = await getHotelCompSetDetail(compSetId);
      setSelectedCompSet(detail);
      notify({ tone: "success", title: t("hotels.messages.memberRemoved") });
    } catch (error) {
      const message = resolveHotelMessage(error, t);
      notify({ tone: "error", title: message });
    }
  }

  async function handleCreateAlertRule(payload: {
    hotel_id: string;
    rule_type: HotelAlertRuleType;
    threshold_amount: number | null;
    threshold_percent: number | null;
    is_active: boolean;
  }): Promise<boolean> {
    setAlertCreateBusy(true);
    try {
      await createHotelAlertRule(payload);
      await refreshAlertRules();
      notify({ tone: "success", title: t("hotels.messages.alertCreated") });
      return true;
    } catch (error) {
      const message = resolveHotelMessage(error, t);
      notify({ tone: "error", title: message });
      return false;
    } finally {
      setAlertCreateBusy(false);
    }
  }

  async function handleToggleAlertRule(ruleId: string, isActive: boolean) {
    markAlertRuleBusy(ruleId, true);
    try {
      await updateHotelAlertRule(ruleId, { is_active: isActive });
      await refreshAlertRules();
      notify({ tone: "success", title: t("hotels.messages.alertUpdated") });
    } catch (error) {
      const message = resolveHotelMessage(error, t);
      notify({ tone: "error", title: message });
    } finally {
      markAlertRuleBusy(ruleId, false);
    }
  }

  async function handleDeleteAlertRule(ruleId: string) {
    markAlertRuleBusy(ruleId, true);
    try {
      await deleteHotelAlertRule(ruleId);
      await refreshAlertRules();
      notify({ tone: "success", title: t("hotels.messages.alertDeleted") });
    } catch (error) {
      const message = resolveHotelMessage(error, t);
      notify({ tone: "error", title: message });
    } finally {
      markAlertRuleBusy(ruleId, false);
    }
  }

  useEffect(() => {
    refreshCompSets().catch(() => undefined);
    let cancelled = false;

    async function loadInitialWatchlist() {
      setWatchlistLoading(true);
      setWatchlistError(null);
      try {
        const items = await listHotelWatchlist();
        if (cancelled) return;
        setWatchlistItems(items);

        const missingHotelIds = Array.from(
          new Set(items.map((item) => item.hotel_id).filter((hotelId) => !watchlistHotelCacheRef.current[hotelId])),
        );

        if (missingHotelIds.length > 0) {
          const detailResults = await Promise.allSettled(missingHotelIds.map((hotelId) => getHotelDetail(hotelId)));
          if (cancelled) return;

          const nextCache: Record<string, HotelDetailOut> = {};
          const failedHotelIds: string[] = [];

          detailResults.forEach((result, index) => {
            const hotelId = missingHotelIds[index];
            if (result.status === "fulfilled") {
              nextCache[hotelId] = result.value;
            } else {
              failedHotelIds.push(hotelId);
            }
          });

          const successfulHotelIds = Object.keys(nextCache);
          if (successfulHotelIds.length > 0) {
            setWatchlistHotelCache((current) => ({ ...current, ...nextCache }));
            setWatchlistUnavailableHotelIds((current) => current.filter((hotelId) => !successfulHotelIds.includes(hotelId)));
          }
          if (failedHotelIds.length > 0) {
            setWatchlistUnavailableHotelIds((current) => Array.from(new Set([...current, ...failedHotelIds])));
          }
        }
      } catch (error) {
        if (cancelled) return;
        setWatchlistError(resolveHotelMessage(error, t) || t("hotels.messages.watchlistLoadError"));
      } finally {
        if (!cancelled) {
          setWatchlistLoading(false);
        }
      }
    }

    loadInitialWatchlist().catch(() => undefined);
    refreshAlertRules().catch(() => undefined);

    return () => {
      cancelled = true;
    };
  }, [refreshAlertRules, t]);

  useEffect(() => {
    refreshAlertEvents(selectedHotelId).catch(() => undefined);
  }, [refreshAlertEvents, selectedHotelId]);

  useEffect(() => {
    if (!selectedHotelId) {
      setHotelDetail(null);
      setRates([]);
      setParitySignals([]);
      setParityError(null);
      setParityLoading(false);
      return;
    }
    let cancelled = false;
    setLoadingRates(true);
    setParityLoading(true);
    setParityError(null);
    Promise.allSettled([getHotelDetail(selectedHotelId), getHotelRates(selectedHotelId), getHotelParity(selectedHotelId)])
      .then(([detailResult, ratesResult, parityResult]) => {
        if (cancelled) return;
        setHotelDetail(detailResult.status === "fulfilled" ? detailResult.value : null);
        if (detailResult.status === "fulfilled") {
          setWatchlistHotelCache((current) => ({ ...current, [detailResult.value.id]: detailResult.value }));
          setWatchlistUnavailableHotelIds((current) => current.filter((hotelId) => hotelId !== detailResult.value.id));
        }
        setRates(ratesResult.status === "fulfilled" ? ratesResult.value : []);
        if (parityResult.status === "fulfilled") {
          setParitySignals(parityResult.value);
          setParityError(null);
        } else {
          setParitySignals([]);
          setParityError(resolveHotelMessage(parityResult.reason, t));
        }
      })
      .finally(() => {
        if (cancelled) return;
        setLoadingRates(false);
        setParityLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedHotelId, t]);

  useEffect(() => {
    const anchorHotelId = selectedCompSet?.anchor_hotel_id;
    if (!anchorHotelId) {
      setCompSetAnchorDetail(null);
      setAnchorError(null);
      setAnchorLoading(false);
      return;
    }

    const cached = anchorCache[anchorHotelId];
    if (cached) {
      setCompSetAnchorDetail(cached);
      setAnchorError(null);
      setAnchorLoading(false);
      return;
    }

    let cancelled = false;
    setCompSetAnchorDetail(null);
    setAnchorLoading(true);
    setAnchorError(null);
    getHotelDetail(anchorHotelId)
      .then((detail) => {
        if (cancelled) return;
        setAnchorCache((current) => ({ ...current, [anchorHotelId]: detail }));
        setCompSetAnchorDetail(detail);
      })
      .catch(() => {
        if (cancelled) return;
        setCompSetAnchorDetail(null);
        setAnchorError(t("hotels.compSet.anchorLoadError"));
      })
      .finally(() => {
        if (cancelled) return;
        setAnchorLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [anchorCache, selectedCompSet, t]);

  useEffect(() => {
    if (!selectedCompSet) {
      setNearbySuggestions([]);
      setNearbyMessage(null);
      setNearbyLoading(false);
      return;
    }

    setNearbyLoading(true);
    setNearbyMessage(null);
    getHotelNearbySuggestions(selectedCompSet.id)
      .then((items) => {
        setNearbySuggestions(items);
      })
      .catch((error) => {
        setNearbySuggestions([]);
        if (error instanceof HotelsRequestError && error.status === 422) {
          setNearbyMessage(t("hotels.compSet.nearbyMissingCoords"));
          return;
        }
        setNearbyMessage(t("hotels.compSet.nearbyGenericError"));
      })
      .finally(() => setNearbyLoading(false));
  }, [selectedCompSet, t]);

  return (
    <main className="shell hoteles-page" id="main-content">
      <header className="page-header hoteles-header">
        <div className="page-title">
          <h1>{t("hotels.title")}</h1>
          <p>{t("hotels.subtitle")}</p>
        </div>
        <div className="page-actions">
          <HotelProviderStatusPill rates={rates} />
        </div>
      </header>

      <section className="hotel-overview-strip section-gap-sm" aria-label={t("hotels.title")}>
        <article className="hotel-overview-card">
          <span>{t("hotels.overview.hotels")}</span>
          <strong>{results.length}</strong>
        </article>
        <article className="hotel-overview-card">
          <span>{t("hotels.overview.compSets")}</span>
          <strong>{compSets.length}</strong>
        </article>
        <article className="hotel-overview-card">
          <span>{t("hotels.overview.nearby")}</span>
          <strong>{featureDisabled ? t("hotels.overview.limited") : nearbySuggestions.length}</strong>
        </article>
      </section>

      <HotelSearchPanel
        query={query}
        city={city}
        loading={loading}
        onQueryChange={setQuery}
        onCityChange={setCity}
        onSearch={handleSearch}
        onIngest={handleIngest}
      />

      {errorMessage ? (
        <section className={`notice section-gap ${featureDisabled ? "notice-info hotel-disabled-notice" : "notice-error"}`} role="status">
          {errorMessage}
        </section>
      ) : null}

      <section className="hoteles-layout section-gap">
        <div className="hoteles-main-column">
          <section className={`panel panel-soft hotel-results-panel${results.length === 0 ? " is-empty" : ""}`}>
            <div className="panel-header">
              <h2 className="panel-title">{t("hotels.results.title")}</h2>
              <span className="status-pill info">{results.length}</span>
            </div>
            <div className="hotel-results-list section-gap-sm">
              {results.map((hotel) => (
                <HotelResultCard
                  key={hotel.id}
                  hotel={hotel}
                  isActive={hotel.id === selectedHotelId}
                  isInWatchlist={watchlistHotelIds.includes(hotel.id)}
                  watchlistBusy={watchlistBusyHotelIds.includes(hotel.id)}
                  onSelect={setSelectedHotelId}
                  onAddWatch={handleAddWatch}
                  onRemoveWatch={(hotelId) => {
                    const item = watchlistItems.find((entry) => entry.hotel_id === hotelId);
                    if (item) {
                      void handleRemoveWatch(item.id, hotelId);
                    }
                  }}
                />
              ))}
              {results.length === 0 && !loading ? <HotelEmptyState /> : null}
              {loading ? <p className="panel-note">{t("shared.states.loading")}</p> : null}
            </div>
          </section>

          <HotelPriceTimeline rates={rates} />
        </div>

        <aside className="hoteles-side-column">
          <section className="panel panel-soft hotel-selected-summary">
            <div className="panel-header">
              <h2 className="panel-title">{t("hotels.selected.title")}</h2>
            </div>
            {selectedHotel ? (
              <div className="section-gap-sm hotel-selected-meta">
                <strong>{selectedHotel.canonical_name}</strong>
                <p className="panel-note hotel-selected-location">
                  {selectedHotel.city}, {selectedHotel.country_code}
                </p>
                {hotelDetail?.address ? <p className="panel-note">{hotelDetail.address}</p> : null}
                {hotelDetail?.updated_at ? <p className="panel-note">{t("hotels.selected.lastCapture")}: {new Date(hotelDetail.updated_at).toLocaleString(localeTag)}</p> : null}
              </div>
            ) : (
              <p className="panel-note section-gap-sm">{t("hotels.selected.empty")}</p>
            )}
            {loadingRates ? <p className="panel-note section-gap-sm">{t("shared.states.loading")}</p> : null}
          </section>

          <HotelWatchlistPanel
            entries={watchlistEntries}
            loading={watchlistLoading}
            error={watchlistError}
            busyHotelIds={watchlistBusyHotelIds}
            onRemove={(itemId, hotelId) => {
              void handleRemoveWatch(itemId, hotelId);
            }}
          />

          <HotelParitySignal signals={paritySignals} loading={parityLoading} error={parityError} />

          <HotelAlertsPanel
            selectedHotel={selectedHotel}
            rules={selectedHotelAlertRules}
            rulesLoading={alertRulesLoading}
            rulesError={alertRulesError}
            events={selectedHotelAlertEvents}
            eventsLoading={alertEventsLoading}
            eventsError={alertEventsError}
            createBusy={alertCreateBusy}
            busyRuleIds={alertBusyRuleIds}
            onCreateRule={handleCreateAlertRule}
            onToggleRule={(ruleId, isActive) => {
              void handleToggleAlertRule(ruleId, isActive);
            }}
            onDeleteRule={(ruleId) => {
              void handleDeleteAlertRule(ruleId);
            }}
          />

          <HotelCompSetPanel
            compSets={compSets}
            selectedCompSet={selectedCompSet}
            anchorDetail={compSetAnchorDetail}
            anchorLoading={anchorLoading}
            anchorError={anchorError}
            hotels={results}
            selectedHotelId={selectedHotelId}
            nearbySuggestions={nearbySuggestions}
            nearbyLoading={nearbyLoading}
            nearbyMessage={nearbyMessage}
            onCreateCompSet={handleCreateCompSet}
            onSelectCompSet={handleSelectCompSet}
            onAddMember={handleAddMember}
            onDeleteMember={handleDeleteMember}
          />
        </aside>
      </section>
    </main>
  );
}
