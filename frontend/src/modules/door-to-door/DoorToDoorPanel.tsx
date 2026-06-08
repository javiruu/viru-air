"use client";

import React, { FormEvent, KeyboardEvent, useCallback, useEffect, useId, useRef, useState } from "react";

import { Car, ExternalLink, MapPin, Plane, ShieldAlert, ShieldCheck, TrainFront } from "lucide-react";
import { useRouter } from "next/navigation";

import { useI18n } from "@/i18n";
import {
  fetchDoorToDoorSuggestions,
} from "@/modules/door-to-door/api";
import { DoorToDoorEmptyState } from "@/modules/door-to-door/components/DoorToDoorEmptyState";
import { DoorToDoorErrorState } from "@/modules/door-to-door/components/DoorToDoorErrorState";
import { DoorToDoorFilters } from "@/modules/door-to-door/components/DoorToDoorFilters";
import { DoorToDoorLoadingState } from "@/modules/door-to-door/components/DoorToDoorLoadingState";
import { DoorToDoorOptionCard } from "@/modules/door-to-door/components/DoorToDoorOptionCard";
import { DoorToDoorFilterPanel } from "@/modules/door-to-door/components/DoorToDoorFilterPanel";
import { DoorToDoorRouteVisual } from "@/modules/door-to-door/components/DoorToDoorRouteVisual";
import { DoorToDoorStickyBar } from "@/modules/door-to-door/components/DoorToDoorStickyBar";
import { hasUncertainSources } from "@/modules/door-to-door/decision";
import { useDoorToDoorHistory } from "@/modules/door-to-door/hooks/useDoorToDoorHistory";
import { useDoorToDoorMapHub } from "@/modules/door-to-door/hooks/useDoorToDoorMapHub";
import { useDoorToDoorResults } from "@/modules/door-to-door/hooks/useDoorToDoorResults";
import { useDoorToDoorSearch } from "@/modules/door-to-door/hooks/useDoorToDoorSearch";
import type {
  DoorToDoorLeg,
  DoorToDoorLocation,
  DoorToDoorMapCapability,
  DoorToDoorMapCapabilityKey,
  DoorToDoorSuggestion,
  DoorToDoorSuggestionsMeta,
} from "@/modules/door-to-door/types";

/* ── UI helpers ────────────────────────────────────────────── */

function formatHistoryDate(value: string, localeTag: string) {
  return new Intl.DateTimeFormat(localeTag, { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

function formatClock(value: string | null | undefined, localeTag: string, fallback?: string) {
  if (!value) return fallback ?? "--:--";
  return new Intl.DateTimeFormat(localeTag, { hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

function formatDurationLabel(minutes: number | null | undefined, fallback?: string) {
  if (minutes == null) return fallback ?? "--";
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hours <= 0) return `${mins} min`;
  return `${hours}h ${String(mins).padStart(2, "0")}m`;
}

function formatDelta(value: number | null, unit = "", fallback?: string) {
  if (value == null) return fallback ?? "--";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value}${unit}`;
}

function autocompleteStatusCopy(meta: DoorToDoorSuggestionsMeta, t: ReturnType<typeof useI18n>["t"]) {
  if (meta.degraded_reason === "google_unavailable_using_open_data") {
    return t("doorToDoor.autocomplete.degradedUsingOpenData");
  }
  if (meta.degraded_reason === "no_results_available") {
    return t("doorToDoor.autocomplete.degradedNoResults");
  }
  return t("doorToDoor.autocomplete.degraded");
}

function resolveGroundIcon(mode: DoorToDoorLeg["mode"]) {
  if (mode === "car" || mode === "taxi" || mode === "rideshare" || mode === "shuttle") {
    return <Car size={16} aria-hidden="true" />;
  }
  return <TrainFront size={16} aria-hidden="true" />;
}

function resolveMapsUrl(leg: DoorToDoorLeg) {
  if (leg.booking_url) return leg.booking_url;
  const mapAction = (leg.actions ?? []).find((action) => action.provider === "google_maps");
  return mapAction?.url ?? null;
}

/* ── Sub‑components ────────────────────────────────────────── */

function useSuggestionSearch(
  value: string,
  sessionToken: string,
  field: "origin" | "destination",
  watchId: string,
) {
  const [suggestions, setSuggestions] = useState<DoorToDoorSuggestion[]>([]);
  const [meta, setMeta] = useState<DoorToDoorSuggestionsMeta>({
    provider_status: "api_live",
    degraded_reason: null,
    used_region_codes: [],
  });
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    const query = value.trim();
    if (query.length < 2) {
      setSuggestions([]);
      setLoading(false);
      return;
    }
    let alive = true;
    const controller = new AbortController();
    setLoading(true);
    const timeoutId = window.setTimeout(() => {
      fetchDoorToDoorSuggestions(query, sessionToken, field, watchId || undefined, controller.signal)
      .then((payload) => {
        if (!alive) return;
        setSuggestions(payload.items.slice(0, 8));
        setMeta(payload.meta);
      })
      .catch((error) => {
        if (!alive) return;
        if (error instanceof DOMException && error.name === "AbortError") return;
        setSuggestions([]);
        setMeta({ provider_status: "provider_error", degraded_reason: "suggestions_fetch_failed", used_region_codes: [] });
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    }, 180);
    return () => {
      alive = false;
      controller.abort();
      window.clearTimeout(timeoutId);
    };
  }, [value, sessionToken, field, watchId]);
  return { suggestions, loading, meta };
}

function LocationInput({
  id,
  label,
  value,
  onChange,
  field,
  watchId,
}: {
  id: string;
  label: string;
  value: DoorToDoorLocation;
  onChange: (location: DoorToDoorLocation) => void;
  field: "origin" | "destination";
  watchId: string;
}) {
  const { t } = useI18n();
  const [focused, setFocused] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const sessionTokenRef = useRef<string>("");
  const listboxId = useId();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const newSessionToken = useCallback(() => {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") return crypto.randomUUID();
    return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }, []);
  const [sessionToken, setSessionToken] = useState("");
  const { suggestions, loading, meta } = useSuggestionSearch(value.label, sessionToken, field, watchId);
  const hasSuggestions = suggestions.length > 0;
  const hasQuery = value.label.trim().length >= 2;
  const showAutocomplete = focused && (loading || hasSuggestions || hasQuery);

  useEffect(() => {
    setActiveIndex(-1);
  }, [value.label, suggestions.length]);
  useEffect(() => {
    setSessionToken("");
    sessionTokenRef.current = "";
    setActiveIndex(-1);
  }, [watchId, field]);

  const selectSuggestion = useCallback((suggestion: DoorToDoorSuggestion) => {
    onChange(suggestion);
    setFocused(false);
    setActiveIndex(-1);
    setSessionToken("");
    sessionTokenRef.current = "";
  }, [onChange]);

  const ensureSessionToken = useCallback(() => {
    if (!sessionTokenRef.current) {
      const token = newSessionToken();
      sessionTokenRef.current = token;
      setSessionToken(token);
    }
  }, [newSessionToken]);

  function onInputKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (suggestions.length === 0) {
      if (event.key === "ArrowDown" || event.key === "ArrowUp" || event.key === "Enter") {
        event.preventDefault();
      }
      return;
    }
    if (!showAutocomplete) {
      if (event.key === "ArrowDown" && hasSuggestions) {
        event.preventDefault();
        setActiveIndex(0);
      }
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((current) => (current + 1) % suggestions.length);
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((current) => (current <= 0 ? suggestions.length - 1 : current - 1));
      return;
    }
    if (event.key === "Enter" && activeIndex >= 0 && activeIndex < suggestions.length) {
      event.preventDefault();
      selectSuggestion(suggestions[activeIndex]);
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      setFocused(false);
      setActiveIndex(-1);
    }
  }

  return (
    <label className="field d2d-autocomplete qs-label" htmlFor={id}>
      <span>{label}</span>
      <div className="qs-input-wrap">
        <span className="qs-input-prefix" aria-hidden="true">
          <span className="qs-input-icon">
            <MapPin size={16} strokeWidth={2} />
          </span>
        </span>
        <input
          ref={inputRef}
          id={id}
          className="qs-input qs-input-with-action"
          value={value.label}
          onChange={(event) => onChange({
            type: value.type || "city",
            label: event.target.value,
            lat: null,
            lng: null,
            place_id: null,
          })}
          onFocus={() => {
            setFocused(true);
            ensureSessionToken();
          }}
          onBlur={() => window.setTimeout(() => setFocused(false), 120)}
          onKeyDown={onInputKeyDown}
          autoComplete="off"
          role="combobox"
          aria-expanded={showAutocomplete}
          aria-autocomplete="list"
          aria-controls={listboxId}
          aria-activedescendant={activeIndex >= 0 ? `${id}-option-${activeIndex}` : undefined}
        />
        <button
          type="button"
          className="qs-input-inline-action"
          onClick={() => inputRef.current?.focus()}
          tabIndex={-1}
          aria-hidden="true"
        >
          <MapPin size={14} strokeWidth={2.5} />
        </button>
        {showAutocomplete ? (
          <ul id={listboxId} className="qs-autocomplete" role="listbox" aria-label={t("doorToDoor.autocomplete.listboxAria", { label })}>
            {loading && suggestions.length === 0 ? (
              <li role="option" aria-selected={false} className="qs-autocomplete-item">
                <span>{t("doorToDoor.autocomplete.loading")}</span>
              </li>
            ) : null}
            {!loading && suggestions.length === 0 ? (
              <li role="option" aria-selected={false} className="qs-autocomplete-item">
                <span>
                  {meta.provider_status === "fallback_active"
                    ? t("doorToDoor.autocomplete.fallbackResults")
                    : t("doorToDoor.autocomplete.noSuggestions")}
                </span>
              </li>
            ) : null}
            {suggestions.map((suggestion, index) => (
              <li key={suggestion.id} id={`${id}-option-${index}`} role="option" aria-selected={index === activeIndex}>
                <button
                  type="button"
                  className="qs-autocomplete-item"
                  data-active={index === activeIndex ? "true" : "false"}
                  onMouseDown={(event) => event.preventDefault()}
                  onMouseEnter={() => setActiveIndex(index)}
                  onClick={() => selectSuggestion(suggestion)}
                >
                  <strong>{suggestion.label}</strong>
                  <span>{suggestion.subtitle}</span>
                </button>
              </li>
            ))}
          </ul>
        ) : null}
        {focused && !loading && value.label.trim().length >= 2 && meta.provider_status !== "api_live" ? (
          <p className="d2d-autocomplete-status">
            {autocompleteStatusCopy(meta, t)}
          </p>
        ) : null}
      </div>
    </label>
  );
}

function FlightSegment({ leg, localeTag, scheduleFallback, durationFallback }: { leg: DoorToDoorLeg; localeTag: string; scheduleFallback: string; durationFallback: string }) {
  return (
    <article className="d2d-leg-card d2d-leg-flight">
      <div className="d2d-leg-card-inner">
        <div className="d2d-segment-main">
          <strong>
            <Plane size={16} aria-hidden="true" /> {leg.from} {"->"} {leg.to}
          </strong>
          <p className="d2d-segment-time">
            {formatClock(leg.departure_at, localeTag, scheduleFallback)} - {formatClock(leg.arrival_at, localeTag, scheduleFallback)} · {formatDurationLabel(leg.duration_minutes, durationFallback)}
          </p>
        </div>
      </div>
    </article>
  );
}

function GroundSegment({ leg, localeTag, scheduleFallback, durationFallback, viewInMapsLabel, fromPriceLabel }: { leg: DoorToDoorLeg; localeTag: string; scheduleFallback: string; durationFallback: string; viewInMapsLabel: string; fromPriceLabel: string }) {
  const mapsUrl = resolveMapsUrl(leg);
  const isDeepLink = leg.confidence === "deeplink";
  const modeClass = `d2d-leg-${leg.mode}`;
  return (
    <article className={`d2d-leg-card d2d-leg-ground ${modeClass}`}>
      <div className="d2d-leg-card-inner">
        <div className="d2d-segment-main">
          <strong>{resolveGroundIcon(leg.mode)} {leg.from} {"->"} {leg.to}</strong>
          {!isDeepLink ? (
            <p className="d2d-segment-time">
              {formatClock(leg.departure_at, localeTag, scheduleFallback)} - {formatClock(leg.arrival_at, localeTag, scheduleFallback)}
              {leg.duration_minutes != null ? ` · ${formatDurationLabel(leg.duration_minutes, durationFallback)}` : ""}
              {leg.price_min != null ? ` · ${fromPriceLabel.replace("{price}", String(leg.price_min))}` : ""}
            </p>
          ) : null}
        </div>
        <div className="d2d-segment-meta">
          {isDeepLink && mapsUrl ? (
            <a className="btn-secondary btn-compact" href={mapsUrl} target="_blank" rel="noreferrer">
              <ExternalLink size={14} aria-hidden="true" />
              <span>{viewInMapsLabel}</span>
            </a>
          ) : null}
        </div>
      </div>
    </article>
  );
}

/* ── Capability cards (shared) ──────────────────────────────── */

type CapabilityCard = {
  key: DoorToDoorMapCapabilityKey;
  titleKey: string;
  descriptionKey: string;
};

const CAPABILITY_CARDS: CapabilityCard[] = [
  { key: "navigation", titleKey: "doorToDoor.mapHub.cards.navigation.title", descriptionKey: "doorToDoor.mapHub.cards.navigation.description" },
  { key: "traffic", titleKey: "doorToDoor.mapHub.cards.traffic.title", descriptionKey: "doorToDoor.mapHub.cards.traffic.description" },
  { key: "transit", titleKey: "doorToDoor.mapHub.cards.transit.title", descriptionKey: "doorToDoor.mapHub.cards.transit.description" },
  { key: "alternatives", titleKey: "doorToDoor.mapHub.cards.alternatives.title", descriptionKey: "doorToDoor.mapHub.cards.alternatives.description" },
  { key: "eco_route", titleKey: "doorToDoor.mapHub.cards.eco_route.title", descriptionKey: "doorToDoor.mapHub.cards.eco_route.description" },
  { key: "nearby_pois", titleKey: "doorToDoor.mapHub.cards.nearby_pois.title", descriptionKey: "doorToDoor.mapHub.cards.nearby_pois.description" },
  { key: "incidents", titleKey: "doorToDoor.mapHub.cards.incidents.title", descriptionKey: "doorToDoor.mapHub.cards.incidents.description" },
  { key: "street_view_preview", titleKey: "doorToDoor.mapHub.cards.street_view_preview.title", descriptionKey: "doorToDoor.mapHub.cards.street_view_preview.description" },
  { key: "offline", titleKey: "doorToDoor.mapHub.cards.offline.title", descriptionKey: "doorToDoor.mapHub.cards.offline.description" },
  { key: "saved_places", titleKey: "doorToDoor.mapHub.cards.saved_places.title", descriptionKey: "doorToDoor.mapHub.cards.saved_places.description" },
];

/* ── Main component ─────────────────────────────────────────── */

export function DoorToDoorPanel() {
  const router = useRouter();
  const { t, localeTag } = useI18n();

  /* ── Hooks ─────────────────────────────────────────────── */
  const search = useDoorToDoorSearch();
  const [triggerVersion, setTriggerVersion] = useState(0);
  const history = useDoorToDoorHistory(search.selectedWatchId, triggerVersion);
  const results = useDoorToDoorResults(search.response, history.refreshHistory);
  const mapHub = useDoorToDoorMapHub(search.response, search.selectedWatchId);

  /* ── Local UI state ────────────────────────────────────── */
  const [isMobile, setIsMobile] = useState(false);
  const [showFilterPanel, setShowFilterPanel] = useState(false);
  const [showTrustModal, setShowTrustModal] = useState(false);
  const [activeSection, setActiveSection] = useState("results");

  useEffect(() => {
    if (typeof window === "undefined") return;
    const media = window.matchMedia("(max-width: 980px)");
    const sync = () => {
      setIsMobile(media.matches);
    };
    sync();
    media.addEventListener("change", sync);
    return () => media.removeEventListener("change", sync);
  }, []);

  /* ── Derived data ──────────────────────────────────────── */
  const hasEstimates = results.estimateOptions.length > 0;
  const attemptedRoute = `${search.origin.label || "-"} -> ${search.selectedWatch?.origin_iata || "AGP"} -> ${search.selectedWatch?.destination_iata || "TSF"} -> ${search.finalDestination.label || "-"}`;
  const timelineLegs = results.selectedPlan?.legs ?? [];

  const capabilityStatusClass = useCallback((state: DoorToDoorMapCapability["state"]) => {
    if (state === "available") return "success";
    if (state === "partial") return "warning";
    if (state === "unavailable") return "error";
    return "info";
  }, []);

  /* ── Handlers ──────────────────────────────────────────── */
  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (search.status === "loading") return;
    await search.calculate();
    setTriggerVersion((v) => v + 1);
  }

  function scrollToSection(sectionId: string) {
    setActiveSection(sectionId);
    const el = document.getElementById(`d2d-section-${sectionId}`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      el.setAttribute("tabindex", "-1");
      el.focus({ preventScroll: true });
    }
  }

  /* ── Render ────────────────────────────────────────────── */
  return (
    <main className="shell d2d-page" id="main-content">
      <div className="page-header d2d-page-header">
        <button className="btn-ghost" type="button" onClick={() => router.push("/dashboard")}>{t("shared.actions.back")}</button>
        <div className="page-title">
          <h1>{t("doorToDoor.title")}</h1>
          <p>{t("doorToDoor.subtitle")}</p>
        </div>
        <span className="status-pill info">{t("doorToDoor.flightIntelligence")}</span>
      </div>

      <section className="panel d2d-ops-panel">
        <div className="d2d-hero">
          <div>
            <h2>{t("doorToDoor.heroTitle")}</h2>
            <p>{t("doorToDoor.heroBody")}</p>
          </div>
          <div className="d2d-hero-ticket" aria-label={t("doorToDoor.selectedFlight")}>
            <span>{t("doorToDoor.form.preparationTitle")}</span>
            <strong>{search.selectedWatch ? `${search.selectedWatch.origin_iata} -> ${search.selectedWatch.destination_iata}` : t("doorToDoor.noFlight")}</strong>
            <small>{search.selectedWatch?.travel_date_local || t("doorToDoor.chooseWatchedRoute")}</small>
          </div>
        </div>

        <form className="panel panel-soft d2d-form d2d-form-essentials" onSubmit={onSubmit}>
          <div className="d2d-section-head d2d-essentials-head">
            <h2>{t("doorToDoor.form.essentialsTitle")}</h2>
          </div>
          <LocationInput id="d2d-origin" label={t("doorToDoor.form.origin")} value={search.origin} onChange={search.setOrigin} field="origin" watchId={search.selectedWatchId} />
          <label className="field qs-label" htmlFor="d2d-watch">
            <span>{t("doorToDoor.form.watch")}</span>
            <select id="d2d-watch" className="qs-input-neutral" value={search.selectedWatchId} onChange={(event) => search.setSelectedWatchId(event.target.value)}>
              <option value="">{t("doorToDoor.form.selectWatch")}</option>
              {search.watches.map((watch) => (
                <option key={watch.id} value={watch.id}>{watch.origin_iata} {"->"} {watch.destination_iata} - {watch.travel_date_local}</option>
              ))}
            </select>
          </label>
          <LocationInput id="d2d-final" label={t("doorToDoor.form.finalDestination")} value={search.finalDestination} onChange={search.setFinalDestination} field="destination" watchId={search.selectedWatchId} />
          <label className="field d2d-checkbox-field">
            <input type="checkbox" checked={search.finalDestination.type === "airport_only"} onChange={(event) => search.setFinalDestination(event.target.checked ? { type: "airport_only", label: t("doorToDoor.defaults.airportOnly", { iata: search.selectedWatch?.destination_iata || "TSF" }) } : search.defaultDestination)} />
            {t("doorToDoor.form.airportOnly")}
          </label>
          <label className="field d2d-checkbox-field">
            <input type="checkbox" checked={search.saveOrigin} onChange={(event) => search.setSaveOrigin(event.target.checked)} />
            {t("doorToDoor.form.saveOrigin")}
          </label>
          <button className="btn-primary" type="submit" disabled={search.isSubmitBlocked}>{t("doorToDoor.cta")}</button>
        </form>
      </section>

      <section className="d2d-decision-grid" id="d2d-section-timeline">
        <div className="panel panel-soft d2d-route-stack">
          <div className="d2d-section-head">
            <h2>{t("doorToDoor.sections.tripSummary")}</h2>
            {search.response?.flight.flight_time_confidence === "estimated" ? (
              <span className="status-pill warning">{t("doorToDoor.timeline.estimatedSchedule")}</span>
            ) : null}
          </div>
          {timelineLegs.length > 0 ? (
            <DoorToDoorRouteVisual option={results.selectedPlan} flight={search.response?.flight ?? null} />
          ) : null}
          {timelineLegs.length === 0 ? <p className="panel-note">{t("doorToDoor.timeline.empty")}</p> : (
            <ol className="d2d-connected-timeline" aria-label={t("doorToDoor.timeline.title")}>
              {timelineLegs.map((leg, index) => (
                <li key={`${leg.type}-${leg.mode}-${index}`} className={`d2d-timeline-leg ${leg.type === "flight" ? "is-flight" : "is-ground"}`}>
                  {index > 0 ? <span className="d2d-timeline-connector" aria-hidden="true" /> : null}
                  {leg.type === "flight" ? (
                    <FlightSegment leg={leg} localeTag={localeTag} scheduleFallback={t("doorToDoor.option.scheduleUnconfirmed")} durationFallback={t("doorToDoor.option.durationUnconfirmed")} />
                  ) : (
                    <GroundSegment leg={leg} localeTag={localeTag} scheduleFallback={t("doorToDoor.option.scheduleUnconfirmed")} durationFallback={t("doorToDoor.option.durationUnconfirmed")} viewInMapsLabel={t("doorToDoor.option.viewRouteInMaps")} fromPriceLabel={t("doorToDoor.option.fromPriceEur")} />
                  )}
                </li>
              ))}
            </ol>
          )}
        </div>

        <aside className="panel panel-soft d2d-settings-aside">
          <div className="d2d-filters-header">
            <strong>{t("doorToDoor.form.decisionSettings")}</strong>
            <span className="panel-note">{t("doorToDoor.filters.collapseHint")}</span>
          </div>
          <button
            type="button"
            className="btn-secondary btn-compact"
            onClick={() => setShowFilterPanel(true)}
          >
            {t("doorToDoor.filters.showFilters")}
          </button>
        </aside>
      </section>



      {search.status === "empty" ? <DoorToDoorEmptyState hasWatch={Boolean(search.selectedWatch)} /> : null}
      {search.status === "loading" ? <DoorToDoorLoadingState /> : null}
      {search.status === "error" ? <DoorToDoorErrorState message={search.errorMessage} onRetry={search.calculate} /> : null}
      {search.status === "no_coverage" ? (
        <section className="notice notice-warning d2d-no-coverage">
          <div>
            <strong>{t("doorToDoor.states.noCoverageTitle")}</strong>
            <p>{t("doorToDoor.states.noCoverageBody")}</p>
            <p className="panel-note"><strong>{t("doorToDoor.sections.attemptedRoute")}:</strong> {attemptedRoute}</p>
            <p className="panel-note"><strong>{t("doorToDoor.sections.providersStatus")}:</strong> {t("doorToDoor.sections.providersMix", { enabled: mapHub.providerStatusSummary.enabled, real: mapHub.providerStatusSummary.realEnabled, estimate: mapHub.providerStatusSummary.estimateEnabled })}</p>
          </div>
          <button className="btn-secondary btn-compact" type="button" onClick={() => search.setPreferences({ ...search.preferences, min_airport_buffer_minutes: 150, max_price: null, allow_shuttle: true, allow_rideshare: true })}>{t("doorToDoor.states.noCoverageCta")}</button>
        </section>
      ) : null}

      {search.response && results.hasNoRealCoverage ? (
        <section className="notice notice-warning d2d-no-coverage">
          <div>
            <strong>{t("doorToDoor.states.noRealCoverageTitle")}</strong>
            <p>{t("doorToDoor.states.noRealCoverageBody")}</p>
            <p className="panel-note"><strong>{t("doorToDoor.sections.providersStatus")}:</strong> {t("doorToDoor.sections.providersMix", { enabled: mapHub.providerStatusSummary.enabled, real: mapHub.providerStatusSummary.realEnabled, estimate: mapHub.providerStatusSummary.estimateEnabled })}</p>
          </div>
        </section>
      ) : null}

      {search.response && results.hasPartialCoverage ? (
        <section className="notice notice-info">
          <p>{t("doorToDoor.sections.partialCoverageBody")}</p>
        </section>
      ) : null}

      {search.response && results.hasAnyGtfsWarning ? (
        <section className="notice notice-info d2d-gtfs-notice">
          <div>
            <strong>{t("doorToDoor.mapHub.cards.transit.title")}</strong>
            <ul className="d2d-warning-list">
              {results.gtfsWarningCodes.map((code) => {
                const i18nKey: string = (() => {
                  if (code === "GTFS_FEED_UNAVAILABLE") return "doorToDoor.gtfsWarnings.feedUnavailable";
                  if (code === "GTFS_NO_NEARBY_STOPS") return "doorToDoor.gtfsWarnings.noNearbyStops";
                  if (code === "GTFS_NO_SERVICE_FOR_DATE") return "doorToDoor.gtfsWarnings.noServiceForDate";
                  if (code === "GTFS_NO_MATCHING_SERVICE") return "doorToDoor.gtfsWarnings.noMatchingService";
                  if (code === "GTFS_PARTIAL_COVERAGE") return "doorToDoor.gtfsWarnings.partialCoverage";
                  if (code === "GTFS_PRICE_UNAVAILABLE") return "doorToDoor.gtfsWarnings.priceUnavailable";
                  return "";
                })();
                return i18nKey ? <li key={code}>{t(i18nKey as any)}</li> : null;
              })}
            </ul>
          </div>
        </section>
      ) : null}

      {search.response && search.response.options.length > 0 && !results.hasNoCoverage ? (
        <>
          <div id="d2d-results-sentinel" aria-hidden="true" />
          <DoorToDoorStickyBar
            plan={results.selectedPlan}
            trustTone={results.trustTone}
            activeSection={activeSection}
            onSectionClick={scrollToSection}
          />

          {results.realResults.length > 0 ? (
            <section className="d2d-results-section" id="d2d-section-results">
              <div className="d2d-section-head">
                <h2>{t("doorToDoor.sections.realResults")}</h2>
                <span className="status-pill success">{results.realResults.length}</span>
              </div>
              <div className="d2d-options-stack">
                {results.realResults.map((option) => (
                  <DoorToDoorOptionCard
                    key={option.id}
                    option={option}
                    chosen={option.id === results.chosenOptionId}
                    isRecommended={option.id === results.recommendedOption?.id}
                    quickBadges={results.quickBadgesByOption[option.id] ?? []}
                    reasons={option.id === results.recommendedOption?.id ? results.recommendedReasons : []}
                    trustInline={option.id === results.recommendedOption?.id && hasUncertainSources(option)}
                    onChoose={() => results.markChosen(option)}
                  />
                ))}
              </div>
            </section>
          ) : null}

          {results.recommendedOption && results.alternativeDeltas.length > 0 ? (
            <section className="panel panel-soft d2d-option-comparator" id="d2d-section-compare">
              <details className="d2d-compare-collapse" open={!isMobile}>
                <summary>
                  <strong>{t("doorToDoor.option.comparatorTitle")}</strong>
                  <span className="panel-note">{t("doorToDoor.option.comparatorSubtitle", { baseline: results.recommendedOption?.label || "" })}</span>
                </summary>
                <div className="d2d-compare-chart" role="list" aria-label={t("doorToDoor.option.comparatorTitle")}>
                  {results.alternativeDeltas.map((delta) => (
                    <div key={delta.option_id} className="d2d-compare-row-bar" role="listitem">
                      <strong className="d2d-compare-option">{delta.option_label}</strong>
                      <div className="d2d-compare-bars">
                        {/* Price */}
                        <div className="d2d-compare-bar-group">
                          <span className="d2d-compare-bar-label">{t("doorToDoor.option.compare.price")}</span>
                          <div className="d2d-compare-bar-track">
                            <div
                              className={`d2d-compare-bar-fill ${delta.delta_price != null && delta.delta_price <= 0 ? "is-better" : "is-worse"}`}
                              style={{ width: delta.delta_price != null ? `${Math.min((Math.abs(delta.delta_price) / 50) * 100, 100)}%` : "0%" }}
                            />
                          </div>
                          <span className={`d2d-compare-delta ${delta.delta_price != null && delta.delta_price <= 0 ? "is-better" : "is-worse"}`}>
                            {formatDelta(delta.delta_price, " €", t("doorToDoor.option.deltaUnavailable"))}
                          </span>
                        </div>
                        {/* Duration */}
                        <div className="d2d-compare-bar-group">
                          <span className="d2d-compare-bar-label">{t("doorToDoor.option.compare.duration")}</span>
                          <div className="d2d-compare-bar-track">
                            <div
                              className={`d2d-compare-bar-fill ${delta.delta_duration_minutes != null && delta.delta_duration_minutes <= 0 ? "is-better" : "is-worse"}`}
                              style={{ width: delta.delta_duration_minutes != null ? `${Math.min((Math.abs(delta.delta_duration_minutes) / 60) * 100, 100)}%` : "0%" }}
                            />
                          </div>
                          <span className={`d2d-compare-delta ${delta.delta_duration_minutes != null && delta.delta_duration_minutes <= 0 ? "is-better" : "is-worse"}`}>
                            {formatDelta(delta.delta_duration_minutes, "m", t("doorToDoor.option.deltaUnavailable"))}
                          </span>
                        </div>
                        {/* Buffer */}
                        <div className="d2d-compare-bar-group">
                          <span className="d2d-compare-bar-label">{t("doorToDoor.option.compare.buffer")}</span>
                          <div className="d2d-compare-bar-track">
                            <div
                              className={`d2d-compare-bar-fill ${delta.delta_buffer_minutes != null && delta.delta_buffer_minutes >= 0 ? "is-better" : "is-worse"}`}
                              style={{ width: delta.delta_buffer_minutes != null ? `${Math.min((Math.abs(delta.delta_buffer_minutes) / 30) * 100, 100)}%` : "0%" }}
                            />
                          </div>
                          <span className={`d2d-compare-delta ${delta.delta_buffer_minutes != null && delta.delta_buffer_minutes >= 0 ? "is-better" : "is-worse"}`}>
                            {formatDelta(delta.delta_buffer_minutes, "m", t("doorToDoor.option.deltaUnavailable"))}
                          </span>
                        </div>
                        <div className="d2d-compare-bar-group">
                          <span className="d2d-compare-bar-label">{t("doorToDoor.option.compare.transfers")}</span>
                          <div className="d2d-compare-bar-track">
                            <div
                              className={`d2d-compare-bar-fill ${delta.delta_transfer_count != null && delta.delta_transfer_count <= 0 ? "is-better" : "is-worse"}`}
                              style={{ width: delta.delta_transfer_count != null ? `${Math.min(Math.abs(delta.delta_transfer_count) * 35, 100)}%` : "0%" }}
                            />
                          </div>
                          <span className={`d2d-compare-delta ${delta.delta_transfer_count != null && delta.delta_transfer_count <= 0 ? "is-better" : "is-worse"}`}>
                            {formatDelta(delta.delta_transfer_count, "", t("doorToDoor.option.deltaUnavailable"))}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </details>
            </section>
          ) : null}

          <section id="d2d-section-sources" className="panel panel-soft d2d-chosen-trust">
            <div className="d2d-section-head">
              <h2>{t("doorToDoor.sections.sources")}</h2>
              <button
                type="button"
                className={`status-pill ${results.trustTone}`}
                onClick={() => setShowTrustModal(true)}
                aria-haspopup="dialog"
                aria-controls="d2d-trust-modal"
                aria-label={t("doorToDoor.sections.trustModalTrigger")}
              >
                {results.trustTone === "success" ? <ShieldCheck size={14} aria-hidden="true" /> : <ShieldAlert size={14} aria-hidden="true" />}
                <span>{results.trustTone === "success" ? t("doorToDoor.sections.trustConfirmed") : t("doorToDoor.sections.trustEstimated")}</span>
              </button>
            </div>
            <p className="panel-note"><strong>{t("doorToDoor.sections.providersStatus")}:</strong> {t("doorToDoor.sections.providersMix", { enabled: mapHub.providerStatusSummary.enabled, real: mapHub.providerStatusSummary.realEnabled, estimate: mapHub.providerStatusSummary.estimateEnabled })}</p>
            {results.hasChosenPlan && results.selectedPlan ? (
              <p className="panel-note">
                <strong>{results.selectedPlan.label}</strong>
                {" · "}
                {results.selectedPlan.total_price_min != null && results.selectedPlan.total_price_max != null
                  ? <>{results.selectedPlan.total_price_min}-{results.selectedPlan.total_price_max} {results.selectedPlan.currency}</>
                  : t("doorToDoor.option.noPrice")}
              </p>
            ) : (
              <p className="panel-note">{t("doorToDoor.sections.chosenPlanHidden")}</p>
            )}
          </section>

          {results.realDeeplinks.length > 0 ? (
            <section id="d2d-section-deeplinks" className="d2d-results-section">
              <div className="d2d-section-head">
                <h2>{t("doorToDoor.sections.realDeeplinks")}</h2>
                <span className="status-pill info">{results.realDeeplinks.length}</span>
              </div>
              <p className="panel-note">{t("doorToDoor.sections.limitedComparisonBody")}</p>
              <p className="panel-note">{t("doorToDoor.sections.externalDisclaimer")}</p>
              <div className="d2d-options-stack">
                {results.realDeeplinks.map((option) => (
                  <DoorToDoorOptionCard
                    key={option.id}
                    option={option}
                    chosen={option.id === results.chosenOptionId}
                    isRecommended={option.id === results.recommendedOption?.id}
                    quickBadges={results.quickBadgesByOption[option.id] ?? []}
                    onChoose={() => results.markChosen(option)}
                  />
                ))}
              </div>
            </section>
          ) : null}

          {hasEstimates ? (
            <section className="panel panel-soft d2d-estimate-section">
              <div className="d2d-section-head">
                <h2>{t("doorToDoor.sections.estimateOnly")}</h2>
                <span className="status-pill warning">{t("doorToDoor.sections.trustEstimated")}</span>
              </div>
              <p className="panel-note">{t("doorToDoor.sections.estimateExplanation")}</p>
              <div className="d2d-options-stack">
                {results.estimateOptions.map((option) => (
                  <DoorToDoorOptionCard
                    key={option.id}
                    option={option}
                    chosen={option.id === results.chosenOptionId}
                    isRecommended={option.id === results.recommendedOption?.id}
                    quickBadges={results.quickBadgesByOption[option.id] ?? []}
                    onChoose={() => results.markChosen(option)}
                  />
                ))}
              </div>
            </section>
          ) : null}
        </>
      ) : null}

      <section className="panel panel-soft d2d-map-hub" id="d2d-section-maphub" aria-label={t("doorToDoor.sections.coveragePanelTitle")}>
        <div className="d2d-section-head">
          <h2>{t("doorToDoor.sections.coveragePanelTitle")}</h2>
          <span className="panel-note">{t("doorToDoor.sections.coveragePanelBody")}</span>
        </div>

        {/* Horizontal capability cards — always visible */}
        <div className="d2d-map-hub-scroll" role="list" aria-label={t("doorToDoor.mapHub.summary")}>
          {CAPABILITY_CARDS.map((card) => {
            const capability = mapHub.mapCapabilities.find((item) => item.key === card.key);
            if (!capability) return null;
            return (
              <article
                key={card.key}
                role="listitem"
                className={`d2d-map-card d2d-map-card-horizontal is-${capability.state}`}
              >
                <div className="d2d-map-card-icon">
                  {capability.state === "available" ? (
                    <span className="d2d-capability-dot is-live" aria-hidden="true" />
                  ) : null}
                  <span className={`d2d-capability-state-icon is-${capability.state}`} aria-hidden="true">
                    {capability.state === "available" ? "✓" : capability.state === "partial" ? "◐" : "○"}
                  </span>
                </div>
                <strong>{t(card.titleKey)}</strong>
                <p>{t(card.descriptionKey)}</p>
                {capability.state !== "available" && capability.why_missing ? (
                  <p className="d2d-capability-reason">{t(`doorToDoor.mapHub.whyMissing.${capability.why_missing}` as any)}</p>
                ) : null}
                <span className={`status-pill ${capabilityStatusClass(capability.state)} d2d-capability-pill`}>
                  {t(`doorToDoor.mapHub.state.${capability.state}`)}
                </span>
              </article>
            );
          })}
        </div>

        {/* Saved Places section — always visible */}
        <div className="d2d-saved-places-section">
          <header>
            <h3><MapPin size={16} aria-hidden="true" /> {t("doorToDoor.mapHub.sections.saved")}</h3>
            <p className="panel-note">{t("doorToDoor.mapHub.sections.savedBody")}</p>
          </header>
          <div className="d2d-saved-places-manager">
            <label className="field qs-label" htmlFor="d2d-saved-place-label">
              <span>{t("doorToDoor.mapHub.savedPlaces.label")}</span>
              <input
                id="d2d-saved-place-label"
                className="qs-input-neutral"
                value={mapHub.savedPlaceLabel}
                onChange={(event) => mapHub.setSavedPlaceLabel(event.target.value)}
                placeholder={t("doorToDoor.mapHub.savedPlaces.labelPlaceholder")}
              />
            </label>
            <label className="field qs-label" htmlFor="d2d-saved-place-note">
              <span>{t("doorToDoor.mapHub.savedPlaces.note")}</span>
              <input
                id="d2d-saved-place-note"
                className="qs-input-neutral"
                value={mapHub.savedPlaceNote}
                onChange={(event) => mapHub.setSavedPlaceNote(event.target.value)}
                placeholder={t("doorToDoor.mapHub.savedPlaces.notePlaceholder")}
              />
            </label>
            <button type="button" className="btn-secondary btn-compact" onClick={mapHub.addSavedPlace} disabled={!mapHub.savedPlaceLabel.trim()}>
              {t("doorToDoor.mapHub.savedPlaces.add")}
            </button>
            <div className="d2d-saved-places-list">
              {mapHub.visibleSavedPlaces.length === 0 ? <p className="panel-note">{t("doorToDoor.mapHub.savedPlaces.empty")}</p> : null}
              {mapHub.visibleSavedPlaces.map((item) => (
                <article key={item.id} className="d2d-saved-place-item">
                  <div>
                    <strong>{item.label}</strong>
                    {item.note ? <p>{item.note}</p> : null}
                  </div>
                  <button type="button" className="btn-ghost btn-compact" onClick={() => mapHub.removeSavedPlace(item.id)}>
                    {t("doorToDoor.mapHub.savedPlaces.remove")}
                  </button>
                </article>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section id="d2d-section-history" className="panel panel-soft d2d-history-panel">
        <div className="action-row d2d-history-action-row">
          <button type="button" className="btn-secondary" onClick={() => history.setShowHistory((current) => !current)} aria-expanded={history.showHistory} aria-controls="d2d-history-content">
            {history.showHistory ? t("doorToDoor.sections.hideHistoryAction") : t("doorToDoor.sections.showHistoryAction")}
          </button>
        </div>
        {history.showHistory ? (
          <div id="d2d-history-content" className="d2d-history-content" aria-live="polite">
            <div className="panel-header"><h2 className="panel-title">{t("doorToDoor.sections.history")}</h2></div>
            {history.history.length === 0 ? <p className="panel-note">{t("doorToDoor.sections.historyEmpty")}</p> : (
              <div className="d2d-history-list">
                {history.history.map((item) => (
                  <article key={item.id}>
                    <strong>{item.origin_label} {"->"} {item.final_destination_label}</strong>
                    <span>{formatHistoryDate(item.created_at, localeTag)} - {item.recommended_label || t("doorToDoor.history.noRecommendation")} - {item.total_price_min != null && item.total_price_max != null ? `${item.total_price_min}-${item.total_price_max} EUR` : t("doorToDoor.option.noPrice")}</span>
                    {item.chosen_option_id ? <em>{t("doorToDoor.history.chosen")}</em> : null}
                  </article>
                ))}
              </div>
            )}
          </div>
        ) : null}
      </section>

      <DoorToDoorFilterPanel
        open={showFilterPanel}
        onClose={() => setShowFilterPanel(false)}
        preferences={search.preferences}
        onChange={search.setPreferences}
      />

      {showTrustModal ? (
        <div className="modal-overlay d2d-trust-overlay" onClick={() => setShowTrustModal(false)}>
          <section id="d2d-trust-modal" className="modal-card d2d-trust-modal" role="dialog" aria-modal="true" aria-label={t("doorToDoor.sections.trustModalTitle")} onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <h2>{t("doorToDoor.sections.trustModalTitle")}</h2>
              <button type="button" className="modal-close" onClick={() => setShowTrustModal(false)} aria-label={t("shared.actions.close")}>x</button>
            </div>
            <p className="panel-note">{results.trustTone === "success" ? t("doorToDoor.sections.trustModalBodyConfirmed") : t("doorToDoor.sections.trustModalBodyEstimated")}</p>
            <p className="panel-note">{t("doorToDoor.sections.trustModalBodyAction")}</p>
          </section>
        </div>
      ) : null}
    </main>
  );
}
