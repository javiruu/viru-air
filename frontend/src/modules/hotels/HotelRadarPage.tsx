"use client";

import { useEffect, useMemo, useState } from "react";

import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { useI18n } from "@/i18n";

import {
  addHotelCompSetMember,
  createHotelCompSet,
  createHotelWatchlistItem,
  getHotelCompSetDetail,
  getHotelDetail,
  getHotelNearbySuggestions,
  getHotelRates,
  HotelsRequestError,
  ingestHotelsMock,
  listHotelCompSets,
  searchHotels,
} from "./api";
import { HotelCompSetPanel, HotelEmptyState } from "./components/HotelCompSetPanel";
import { HotelResultCard, HotelSearchPanel } from "./components/HotelSearchPanel";
import { HotelParitySignal, HotelPriceTimeline, HotelProviderStatusPill } from "./components/HotelTimelineAndSignals";
import type {
  HotelCompSetDetailOut,
  HotelCompSetOut,
  HotelDetailOut,
  HotelNearbySuggestionOut,
  HotelRateOut,
  HotelSearchOut,
} from "./types";

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
  const [compSets, setCompSets] = useState<HotelCompSetOut[]>([]);
  const [selectedCompSet, setSelectedCompSet] = useState<HotelCompSetDetailOut | null>(null);
  const [nearbySuggestions, setNearbySuggestions] = useState<HotelNearbySuggestionOut[]>([]);
  const [nearbyLoading, setNearbyLoading] = useState(false);
  const [nearbyMessage, setNearbyMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const selectedHotel = useMemo(() => results.find((item) => item.id === selectedHotelId) ?? null, [results, selectedHotelId]);
  const selectedCompSetAnchor = useMemo(
    () => results.find((item) => item.id === selectedCompSet?.anchor_hotel_id) ?? null,
    [results, selectedCompSet],
  );
  const featureDisabled = Boolean(errorMessage && errorMessage.includes("HOTEL_FEATURE_ENABLED"));

  function resolveHotelMessage(error: unknown): string {
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
      return error.message;
    }
    if (error instanceof Error && error.message.includes("HOTEL_FEATURE_ENABLED")) {
      return t("hotels.messages.featureDisabled");
    }
    return error instanceof Error ? error.message : t("shared.errors.generic");
  }

  async function refreshCompSets() {
    const next = await listHotelCompSets();
    setCompSets(next);
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
      const message = resolveHotelMessage(error);
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
      await refreshCompSets();
    } catch (error) {
      const message = resolveHotelMessage(error);
      setErrorMessage(message);
      notify({ tone: "error", title: message });
    } finally {
      setLoading(false);
    }
  }

  async function handleAddWatch(hotelId: string) {
    try {
      await createHotelWatchlistItem({ hotel_id: hotelId, label: t("hotels.watchlist.defaultLabel") });
      notify({ tone: "success", title: t("hotels.messages.watchAdded") });
    } catch (error) {
      const message = error instanceof Error ? error.message : t("shared.errors.generic");
      notify({ tone: "error", title: message });
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
      const message = resolveHotelMessage(error);
      notify({ tone: "error", title: message });
    }
  }

  useEffect(() => {
    refreshCompSets().catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!selectedHotelId) {
      setHotelDetail(null);
      setRates([]);
      return;
    }
    setLoadingRates(true);
    Promise.all([getHotelDetail(selectedHotelId), getHotelRates(selectedHotelId)])
      .then(([detail, nextRates]) => {
        setHotelDetail(detail);
        setRates(nextRates);
      })
      .catch(() => {
        setHotelDetail(null);
        setRates([]);
      })
      .finally(() => setLoadingRates(false));
  }, [selectedHotelId]);

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
                  onSelect={setSelectedHotelId}
                  onAddWatch={handleAddWatch}
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

          <HotelParitySignal rates={rates} />

          <HotelCompSetPanel
            compSets={compSets}
            selectedCompSet={selectedCompSet}
            selectedCompSetAnchor={selectedCompSetAnchor}
            hotels={results}
            selectedHotelId={selectedHotelId}
            nearbySuggestions={nearbySuggestions}
            nearbyLoading={nearbyLoading}
            nearbyMessage={nearbyMessage}
            onCreateCompSet={handleCreateCompSet}
            onSelectCompSet={handleSelectCompSet}
            onAddMember={handleAddMember}
          />
        </aside>
      </section>
    </main>
  );
}
