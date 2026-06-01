"use client";

import { useEffect, useMemo, useState } from "react";

import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { useI18n } from "@/i18n";

import {
  addHotelCompSetMember,
  createHotelCompSet,
  createHotelWatchlistItem,
  getHotelCompSetDetail,
  getHotelRates,
  ingestHotelsMock,
  listHotelCompSets,
  searchHotels,
} from "./api";
import { HotelCompSetPanel, HotelEmptyState } from "./components/HotelCompSetPanel";
import { HotelResultCard, HotelSearchPanel } from "./components/HotelSearchPanel";
import { HotelParitySignal, HotelPriceTimeline, HotelProviderStatusPill } from "./components/HotelTimelineAndSignals";
import type { HotelCompSetDetailOut, HotelCompSetOut, HotelRateOut, HotelSearchOut } from "./types";

export function HotelRadarPage() {
  const { t } = useI18n();
  const { notify } = useNotificationCenter();

  const [query, setQuery] = useState("");
  const [city, setCity] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<HotelSearchOut[]>([]);
  const [selectedHotelId, setSelectedHotelId] = useState<string | null>(null);
  const [rates, setRates] = useState<HotelRateOut[]>([]);
  const [compSets, setCompSets] = useState<HotelCompSetOut[]>([]);
  const [selectedCompSet, setSelectedCompSet] = useState<HotelCompSetDetailOut | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const selectedHotel = useMemo(() => results.find((item) => item.id === selectedHotelId) ?? null, [results, selectedHotelId]);

  async function refreshCompSets() {
    const next = await listHotelCompSets();
    setCompSets(next);
  }

  async function handleSearch() {
    setLoading(true);
    setErrorMessage(null);
    try {
      const list = await searchHotels({ q: query || undefined, city: city || undefined, limit: 30 });
      setResults(list);
      if (!list.some((item) => item.id === selectedHotelId)) {
        setSelectedHotelId(list[0]?.id ?? null);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : t("shared.errors.generic");
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
      await handleSearch();
      await refreshCompSets();
    } catch (error) {
      const message = error instanceof Error ? error.message : t("shared.errors.generic");
      setErrorMessage(message);
      notify({ tone: "error", title: message });
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
      const message = error instanceof Error ? error.message : t("shared.errors.generic");
      notify({ tone: "error", title: message });
    }
  }

  useEffect(() => {
    refreshCompSets().catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!selectedHotelId) {
      setRates([]);
      return;
    }
    getHotelRates(selectedHotelId)
      .then(setRates)
      .catch(() => setRates([]));
  }, [selectedHotelId]);

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

      <HotelSearchPanel
        query={query}
        city={city}
        loading={loading}
        onQueryChange={setQuery}
        onCityChange={setCity}
        onSearch={handleSearch}
        onIngest={handleIngest}
      />

      {errorMessage ? <section className="notice notice-error section-gap" role="status">{errorMessage}</section> : null}

      <section className="hoteles-layout section-gap">
        <div className="hoteles-main-column">
          <section className="panel panel-soft">
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
              <div className="section-gap-sm">
                <strong>{selectedHotel.canonical_name}</strong>
                <p className="panel-note">{selectedHotel.city}, {selectedHotel.country_code}</p>
              </div>
            ) : (
              <p className="panel-note section-gap-sm">{t("hotels.selected.empty")}</p>
            )}
          </section>

          <HotelParitySignal rates={rates} />

          <HotelCompSetPanel
            compSets={compSets}
            selectedCompSet={selectedCompSet}
            hotels={results}
            selectedHotelId={selectedHotelId}
            onCreateCompSet={handleCreateCompSet}
            onSelectCompSet={handleSelectCompSet}
            onAddMember={handleAddMember}
          />
        </aside>
      </section>
    </main>
  );
}

