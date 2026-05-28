"use client";

import React, { FormEvent, KeyboardEvent, useCallback, useEffect, useId, useMemo, useRef, useState } from "react";

import { Compass, ExternalLink, Layers3, MapPin, Navigation, Route, ShieldAlert, ShieldCheck } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";

import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { useI18n } from "@/i18n";
import {
  chooseDoorToDoorOption,
  fetchDoorToDoorHistory,
  fetchDoorToDoorProviderStatus,
  fetchDoorToDoorSuggestions,
  fetchSavedDoorToDoorLocation,
  searchDoorToDoor,
} from "@/modules/door-to-door/api";
import { DoorToDoorEmptyState } from "@/modules/door-to-door/components/DoorToDoorEmptyState";
import { DoorToDoorErrorState } from "@/modules/door-to-door/components/DoorToDoorErrorState";
import { DoorToDoorFilters } from "@/modules/door-to-door/components/DoorToDoorFilters";
import { DoorToDoorLoadingState } from "@/modules/door-to-door/components/DoorToDoorLoadingState";
import { DoorToDoorOptionCard } from "@/modules/door-to-door/components/DoorToDoorOptionCard";
import { getAlternativeDeltas, getDecisionBadges, getDecisionReasons, hasUncertainSources } from "@/modules/door-to-door/decision";
import { buildMapCapabilities, filterSavedPlacesForWatch } from "@/modules/door-to-door/mapHub";
import type {
  DoorToDoorHistoryItem,
  DoorToDoorLocation,
  DoorToDoorMapCapability,
  DoorToDoorSavedPlace,
  OptionDeltaSummary,
  DoorToDoorOption,
  DoorToDoorMapCapabilityKey,
  DoorToDoorProviderStatus,
  DoorToDoorPreferences,
  DoorToDoorResponse,
  DoorToDoorSuggestion,
  DoorToDoorSuggestionsMeta,
} from "@/modules/door-to-door/types";
import { apiFetch } from "@/modules/shared/api";
import type { Watch } from "@/modules/watchlist/types";

const DEFAULT_PREFERENCES: DoorToDoorPreferences = {
  min_airport_buffer_minutes: 120,
  max_price: 80,
  passengers: 1,
  luggage: "cabin",
  allow_bus: true,
  allow_train: true,
  allow_rideshare: true,
  allow_shuttle: true,
  allow_taxi: false,
  allow_car: true,
  public_transport_only: false,
  sort_by: "best_balance",
};

type TrustTone = "success" | "warning";

type SegmentNode = {
  id: string;
  title: string;
  route: string;
  timing: string;
  badge: string;
  actions: Array<{ href: string; label: string; ariaLabel: string }>;
};

type CapabilitySectionKey = "layers" | "alternatives" | "arrival" | "visual" | "saved";

type CapabilityCard = {
  key: DoorToDoorMapCapabilityKey;
  section: CapabilitySectionKey;
  titleKey: string;
  descriptionKey: string;
};

const CAPABILITY_CARDS: CapabilityCard[] = [
  { key: "navigation", section: "layers", titleKey: "doorToDoor.mapHub.cards.navigation.title", descriptionKey: "doorToDoor.mapHub.cards.navigation.description" },
  { key: "traffic", section: "layers", titleKey: "doorToDoor.mapHub.cards.traffic.title", descriptionKey: "doorToDoor.mapHub.cards.traffic.description" },
  { key: "transit", section: "layers", titleKey: "doorToDoor.mapHub.cards.transit.title", descriptionKey: "doorToDoor.mapHub.cards.transit.description" },
  { key: "alternatives", section: "alternatives", titleKey: "doorToDoor.mapHub.cards.alternatives.title", descriptionKey: "doorToDoor.mapHub.cards.alternatives.description" },
  { key: "eco_route", section: "alternatives", titleKey: "doorToDoor.mapHub.cards.eco_route.title", descriptionKey: "doorToDoor.mapHub.cards.eco_route.description" },
  { key: "nearby_pois", section: "arrival", titleKey: "doorToDoor.mapHub.cards.nearby_pois.title", descriptionKey: "doorToDoor.mapHub.cards.nearby_pois.description" },
  { key: "incidents", section: "arrival", titleKey: "doorToDoor.mapHub.cards.incidents.title", descriptionKey: "doorToDoor.mapHub.cards.incidents.description" },
  { key: "street_view_preview", section: "visual", titleKey: "doorToDoor.mapHub.cards.street_view_preview.title", descriptionKey: "doorToDoor.mapHub.cards.street_view_preview.description" },
  { key: "offline", section: "visual", titleKey: "doorToDoor.mapHub.cards.offline.title", descriptionKey: "doorToDoor.mapHub.cards.offline.description" },
  { key: "saved_places", section: "saved", titleKey: "doorToDoor.mapHub.cards.saved_places.title", descriptionKey: "doorToDoor.mapHub.cards.saved_places.description" },
];

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

function formatHistoryDate(value: string, localeTag: string) {
  return new Intl.DateTimeFormat(localeTag, { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

function formatClock(value: string | null | undefined, localeTag: string) {
  if (!value) return "--:--";
  return new Intl.DateTimeFormat(localeTag, { hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

function formatDurationLabel(minutes: number | null | undefined) {
  if (minutes == null) return "--";
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hours <= 0) return `${mins} min`;
  return `${hours}h ${String(mins).padStart(2, "0")}m`;
}

function formatDelta(value: number | null, unit = "") {
  if (value == null) return "--";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value}${unit}`;
}

function normalizeLabel(value: string) {
  return value.trim().replace(/\s+/g, " ").toLocaleLowerCase();
}

function deriveTrustTone(option: DoorToDoorOption | null): TrustTone {
  if (!option) return "warning";
  const confirmed = option.sources.filter(
    (source) =>
      (source.source_type === "api" || source.source_type === "open_data" || source.source_type === "maps") &&
      (source.confidence === "live" || source.confidence === "cached"),
  ).length;
  const uncertain = option.sources.filter(
    (source) =>
      source.source_type === "deeplink" ||
      source.source_type === "estimate" ||
      source.source_type === "mock" ||
      source.confidence === "estimated" ||
      source.confidence === "deeplink" ||
      source.confidence === "unavailable",
  ).length;
  if (confirmed > 0 && confirmed >= uncertain) return "success";
  return "warning";
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

export function DoorToDoorPanel() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { t, localeTag } = useI18n();
  const { notify } = useNotificationCenter();
  const watchIdParam = searchParams?.get("watchId") || "";
  const defaultOrigin = useMemo<DoorToDoorLocation>(() => ({ type: "city", label: t("doorToDoor.defaults.origin"), lat: 36.834, lng: -2.463 }), [t]);
  const defaultDestination = useMemo<DoorToDoorLocation>(() => ({ type: "city", label: t("doorToDoor.defaults.destination") }), [t]);
  const [watches, setWatches] = useState<Watch[]>([]);
  const [selectedWatchId, setSelectedWatchId] = useState(watchIdParam);
  const [origin, setOrigin] = useState<DoorToDoorLocation>(defaultOrigin);
  const [finalDestination, setFinalDestination] = useState<DoorToDoorLocation>(defaultDestination);
  const [preferences, setPreferences] = useState<DoorToDoorPreferences>(DEFAULT_PREFERENCES);
  const [saveOrigin, setSaveOrigin] = useState(false);
  const [status, setStatus] = useState<"empty" | "loading" | "success" | "partial" | "error" | "no_coverage">("empty");
  const [response, setResponse] = useState<DoorToDoorResponse | null>(null);
  const [chosenOptionId, setChosenOptionId] = useState<string>("");
  const [history, setHistory] = useState<DoorToDoorHistoryItem[]>([]);
  const [providerStatus, setProviderStatus] = useState<DoorToDoorProviderStatus[]>([]);
  const [isMobile, setIsMobile] = useState(false);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [showTrustModal, setShowTrustModal] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [openActionsNodeId, setOpenActionsNodeId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [savedPlaces, setSavedPlaces] = useState<DoorToDoorSavedPlace[]>([]);
  const [savedPlaceLabel, setSavedPlaceLabel] = useState("");
  const [savedPlaceNote, setSavedPlaceNote] = useState("");
  const requestIdRef = useRef(0);
  const visibleSavedPlaces = useMemo(() => filterSavedPlacesForWatch(savedPlaces, selectedWatchId), [savedPlaces, selectedWatchId]);

  useEffect(() => {
    setSelectedWatchId(watchIdParam);
  }, [watchIdParam]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const raw = window.localStorage.getItem("viru_d2d_saved_places_v1");
      if (!raw) return;
      const parsed = JSON.parse(raw) as DoorToDoorSavedPlace[];
      if (Array.isArray(parsed)) setSavedPlaces(parsed.slice(0, 12));
    } catch {
      setSavedPlaces([]);
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem("viru_d2d_saved_places_v1", JSON.stringify(savedPlaces.slice(0, 12)));
  }, [savedPlaces]);

  useEffect(() => {
    setOrigin((current) => (current.label ? current : defaultOrigin));
    setFinalDestination((current) => (current.label ? current : defaultDestination));
  }, [defaultDestination, defaultOrigin]);

  useEffect(() => {
    fetchDoorToDoorProviderStatus()
      .then((items) => setProviderStatus(items))
      .catch(() => setProviderStatus([]));
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const media = window.matchMedia("(max-width: 980px)");
    const sync = () => {
      const mobile = media.matches;
      setIsMobile(mobile);
      setShowAdvancedFilters((current) => (mobile ? current : true));
    };
    sync();
    media.addEventListener("change", sync);
    return () => media.removeEventListener("change", sync);
  }, []);

  useEffect(() => {
    apiFetch<Watch[]>("/watchlist")
      .then((items) => {
        setWatches(items);
        setSelectedWatchId((current) => current || watchIdParam || items[0]?.id || "");
      })
      .catch(() => setWatches([]));
    fetchSavedDoorToDoorLocation()
      .then((saved) => {
        if (saved) setOrigin({ type: saved.type, label: saved.label, lat: saved.lat, lng: saved.lng });
      })
      .catch(() => undefined);
  }, [watchIdParam]);

  useEffect(() => {
    if (!selectedWatchId) return;
    fetchDoorToDoorHistory(selectedWatchId)
      .then((items) => setHistory(items))
      .catch(() => setHistory([]));
  }, [selectedWatchId, chosenOptionId, response?.summary.history_id]);

  useEffect(() => {
    setShowHistory(false);
  }, [selectedWatchId]);

  useEffect(() => {
    if (!isMobile) setOpenActionsNodeId(null);
  }, [isMobile]);

  const selectedWatch = useMemo(() => watches.find((watch) => watch.id === selectedWatchId) || null, [watches, selectedWatchId]);
  const isSubmitBlocked = status === "loading" || !selectedWatch;

  useEffect(() => {
    if (!selectedWatch) return;
    setFinalDestination((current) => {
      if (current.type !== "airport_only") return current;
      const nextLabel = t("doorToDoor.defaults.airportOnly", { iata: selectedWatch.destination_iata || "TSF" });
      if (current.label === nextLabel) return current;
      return { ...current, label: nextLabel };
    });
  }, [selectedWatch, t]);

  const realResults = useMemo(() => response?.options.filter((o) => o.status === "real_result") ?? [], [response]);
  const realDeeplinks = useMemo(() => response?.options.filter((o) => o.status === "real_deeplink") ?? [], [response]);
  const estimateOptions = useMemo(() => response?.options.filter((o) => o.status === "estimate_only") ?? [], [response]);

  const hasEstimates = estimateOptions.length > 0;

  const attemptedRoute = `${origin.label || "-"} -> ${selectedWatch?.origin_iata || "AGP"} -> ${selectedWatch?.destination_iata || "TSF"} -> ${finalDestination.label || "-"}`;
  const providerStatusSummary = useMemo(() => {
    const enabled = providerStatus.filter((provider) => provider.enabled);
    const realEnabled = enabled.filter((provider) => provider.source_type !== "mock" && provider.source_type !== "estimate");
    const estimateEnabled = enabled.filter((provider) => provider.source_type === "mock" || provider.source_type === "estimate");
    return { enabled: enabled.length, realEnabled: realEnabled.length, estimateEnabled: estimateEnabled.length };
  }, [providerStatus]);
  const mapCapabilities = useMemo(() => buildMapCapabilities(response, providerStatus), [response, providerStatus]);
  const mapCapabilitiesBySection = useMemo(() => {
    return {
      layers: CAPABILITY_CARDS.filter((card) => card.section === "layers"),
      alternatives: CAPABILITY_CARDS.filter((card) => card.section === "alternatives"),
      arrival: CAPABILITY_CARDS.filter((card) => card.section === "arrival"),
      visual: CAPABILITY_CARDS.filter((card) => card.section === "visual"),
      saved: CAPABILITY_CARDS.filter((card) => card.section === "saved"),
    };
  }, []);
  const capabilityStatusClass = useCallback((state: DoorToDoorMapCapability["state"]) => {
    if (state === "available") return "success";
    if (state === "partial") return "warning";
    if (state === "unavailable") return "error";
    return "info";
  }, []);

  const selectedPlan = useMemo(() => {
    if (!response) return null;
    return (
      response.options.find((option) => option.id === chosenOptionId) ||
      response.options.find((option) => option.id === response.summary.chosen_option_id) ||
      response.options.find((option) => option.id === response.summary.recommended_option_id) ||
      response.options[0] ||
      null
    );
  }, [response, chosenOptionId]);
  const quickBadgesByOption = useMemo(() => {
    if (!response) return {};
    return getDecisionBadges(response.options);
  }, [response]);

  const recommendedOption = useMemo(() => {
    if (!response) return null;
    return response.options.find((option) => option.id === response.summary.recommended_option_id) || response.options[0] || null;
  }, [response]);

  const recommendedReasons = useMemo(() => {
    if (!response || !recommendedOption) return [];
    return getDecisionReasons(recommendedOption, response.options);
  }, [response, recommendedOption]);

  const alternativeDeltas = useMemo<OptionDeltaSummary[]>(() => {
    if (!response || !recommendedOption) return [];
    return getAlternativeDeltas(recommendedOption, response.options);
  }, [response, recommendedOption]);

  const trustTone = useMemo(() => deriveTrustTone(selectedPlan), [selectedPlan]);

  const segmentLinks = useMemo(() => {
    if (!selectedWatch) return null;
    const originLabel = origin.label;
    const destLabel = finalDestination.label;
    const originIata = selectedWatch.origin_iata;
    const destIata = selectedWatch.destination_iata;
    const travelDate = selectedWatch.travel_date_local;

    const mapsOutbound = `https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(originLabel)}&destination=${encodeURIComponent(originIata + " Airport")}&travelmode=driving&dir_action=navigate`;
    const mapsInbound = destLabel ? `https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(destIata + " Airport")}&destination=${encodeURIComponent(destLabel)}&travelmode=driving&dir_action=navigate` : null;
    const blablacarOption = response?.options.find((option) => option.id === "option_blablacar_deeplink");
    const gooptiOption = response?.options.find((option) => option.id === "option_goopti_deeplink");

    const blablacarUrl =
      blablacarOption?.deep_link?.url ||
      blablacarOption?.sources.find((source) => source.provider === "blablacar_deeplink" && source.booking_url)?.booking_url ||
      null;
    const gooptiUrl =
      gooptiOption?.deep_link?.url ||
      gooptiOption?.sources.find((source) => source.provider === "goopti_deeplink" && source.booking_url)?.booking_url ||
      (destLabel ? `https://www.goopti.com/es/?pickup=${encodeURIComponent("Aeropuerto de " + destIata)}&dropoff=${encodeURIComponent(destLabel)}&date=${travelDate || ""}` : null);

    return { mapsOutbound, mapsInbound, blablacarUrl, gooptiUrl };
  }, [selectedWatch, origin.label, finalDestination.label, response?.options]);

  const timelineNodes = useMemo<SegmentNode[]>(() => {
    if (!selectedWatch || !segmentLinks || !response) return [];
    const groundLegs = selectedPlan?.legs.filter((leg) => leg.type === "ground") || [];
    const outboundLeg = groundLegs[0];
    const inboundLeg = groundLegs.length > 1 ? groundLegs[groundLegs.length - 1] : null;
    const flightLeg = selectedPlan?.legs.find((leg) => leg.type === "flight") || null;

    const nodes: SegmentNode[] = [
      {
        id: "outbound",
        title: t("doorToDoor.sections.segmentOutbound"),
        route: `${origin.label} -> ${selectedWatch.origin_iata}`,
        timing: `${formatClock(outboundLeg?.departure_at, localeTag)} - ${formatClock(outboundLeg?.arrival_at, localeTag)}`,
        badge: formatDurationLabel(outboundLeg?.duration_minutes),
        actions: [
          { href: segmentLinks.mapsOutbound, label: t("doorToDoor.sections.openMapsShort"), ariaLabel: t("doorToDoor.sections.openGoogleMaps") },
          ...(segmentLinks.blablacarUrl ? [{ href: segmentLinks.blablacarUrl, label: t("doorToDoor.sections.openBlaBlaCarShort"), ariaLabel: t("doorToDoor.sections.openBlaBlaCarAction") }] : []),
        ],
      },
      {
        id: "flight",
        title: t("doorToDoor.sections.segmentFlight"),
        route: `${selectedWatch.origin_iata} -> ${selectedWatch.destination_iata}`,
        timing: `${formatClock(response.flight.departure_at, localeTag)} - ${formatClock(response.flight.arrival_at, localeTag)}`,
        badge: formatDurationLabel(flightLeg?.duration_minutes),
        actions: [],
      },
    ];

    if (finalDestination.type !== "airport_only") {
      nodes.push({
        id: "inbound",
        title: t("doorToDoor.sections.segmentInbound"),
        route: `${selectedWatch.destination_iata} -> ${finalDestination.label}`,
        timing: `${formatClock(inboundLeg?.departure_at, localeTag)} - ${formatClock(inboundLeg?.arrival_at, localeTag)}`,
        badge: formatDurationLabel(inboundLeg?.duration_minutes),
        actions: [
          ...(segmentLinks.mapsInbound ? [{ href: segmentLinks.mapsInbound, label: t("doorToDoor.sections.openMapsShort"), ariaLabel: t("doorToDoor.sections.openGoogleMaps") }] : []),
          ...(segmentLinks.gooptiUrl ? [{ href: segmentLinks.gooptiUrl, label: t("doorToDoor.sections.openGoOptiShort"), ariaLabel: t("doorToDoor.sections.openGoOptiAction") }] : []),
        ],
      });
    }

    return nodes;
  }, [selectedWatch, segmentLinks, response, selectedPlan, finalDestination.type, finalDestination.label, origin.label, t, localeTag]);

  const calculate = useCallback(async () => {
    if (!selectedWatch) {
      setStatus("empty");
      setErrorMessage(t("doorToDoor.chooseWatchedRoute"));
      return;
    }
    const normalizedOrigin = normalizeLabel(origin.label);
    const normalizedDestination = normalizeLabel(finalDestination.label);
    if (normalizedOrigin.length < 2 || normalizedDestination.length < 2) {
      setStatus("empty");
      setErrorMessage(t("doorToDoor.states.emptyBodyWithWatch"));
      notify({ tone: "error", title: t("doorToDoor.states.emptyTitleWithWatch") });
      return;
    }
    if (finalDestination.type !== "airport_only" && normalizedOrigin === normalizedDestination) {
      setStatus("empty");
      setErrorMessage(t("doorToDoor.states.emptyBodyWithWatch"));
      notify({ tone: "error", title: t("doorToDoor.states.emptyTitleWithWatch") });
      return;
    }
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    setStatus("loading");
    setErrorMessage("");
    try {
      const data = await searchDoorToDoor({
        flight_watch_id: selectedWatch.id,
        origin,
        final_destination: finalDestination,
        preferences,
        save_origin_as_default: saveOrigin,
      });
      if (requestId !== requestIdRef.current) return;
      setResponse(data);
      setChosenOptionId(data.summary.chosen_option_id || "");
      const noCoverageWarning = data.warnings.some((warning) => warning.code === "NO_COVERAGE");
      if (data.options.length === 0 || noCoverageWarning) {
        setStatus("no_coverage");
      } else if (data.warnings.length > 0) {
        setStatus("partial");
      } else {
        setStatus("success");
      }
      setOpenActionsNodeId(null);
    } catch (error) {
      if (requestId !== requestIdRef.current) return;
      setErrorMessage(error instanceof Error ? error.message : "Error inesperado");
      setStatus("error");
    }
  }, [finalDestination, notify, origin, preferences, saveOrigin, selectedWatch, t]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (status === "loading") return;
    await calculate();
  }

  async function markChosen(option: DoorToDoorOption) {
    if (!response?.summary.history_id) return;
    try {
      await chooseDoorToDoorOption({
        historyId: response.summary.history_id,
        optionId: option.id,
        optionLabel: option.label,
        optionSummary: {
          total_price_min: option.total_price_min,
          total_price_max: option.total_price_max,
          risk_level: option.risk_level,
          total_duration_minutes: option.total_duration_minutes,
        },
      });
      setChosenOptionId(option.id);
      notify({ tone: "success", title: t("doorToDoor.option.chosenSaved") });
    } catch {
      notify({ tone: "error", title: t("doorToDoor.option.chosenError") });
    }
  }

  function renderCapabilityCard(card: CapabilityCard) {
    const capability = mapCapabilities.find((item) => item.key === card.key);
    if (!capability) return null;
    return (
      <article key={card.key} className={`d2d-map-card is-${capability.state}`}>
        <div className="d2d-map-card-head">
          <strong>{t(card.titleKey)}</strong>
          <span className={`status-pill ${capabilityStatusClass(capability.state)}`}>
            {t(`doorToDoor.mapHub.state.${capability.state}`)}
          </span>
        </div>
        <p>{t(card.descriptionKey)}</p>
        <div className="d2d-map-card-meta">
          <span>{t("doorToDoor.mapHub.source")}: {capability.source_type}</span>
          <span>{t("doorToDoor.mapHub.confidence")}: {t(`doorToDoor.source.${capability.confidence}`)}</span>
          {capability.why_missing ? <span>{t("doorToDoor.mapHub.pending")}: {capability.why_missing}</span> : null}
        </div>
      </article>
    );
  }

  function addSavedPlace() {
    const label = savedPlaceLabel.trim();
    const note = savedPlaceNote.trim();
    if (!label) return;
    const duplicate = savedPlaces.some((item) => {
      const sameScope = (item.watch_id || "") === (selectedWatchId || "");
      return sameScope && normalizeLabel(item.label) === normalizeLabel(label);
    });
    if (duplicate) {
      notify({ tone: "warning", title: t("doorToDoor.mapHub.savedPlaces.savedToast") });
      return;
    }
    const item: DoorToDoorSavedPlace = {
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      label,
      note,
      created_at: new Date().toISOString(),
      watch_id: selectedWatchId || null,
    };
    setSavedPlaces((current) => [item, ...current].slice(0, 12));
    setSavedPlaceLabel("");
    setSavedPlaceNote("");
    notify({ tone: "success", title: t("doorToDoor.mapHub.savedPlaces.savedToast") });
  }

  function removeSavedPlace(id: string) {
    setSavedPlaces((current) => current.filter((item) => item.id !== id));
    notify({ tone: "success", title: t("doorToDoor.mapHub.savedPlaces.deletedToast") });
  }

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
            <strong>{selectedWatch ? `${selectedWatch.origin_iata} -> ${selectedWatch.destination_iata}` : t("doorToDoor.noFlight")}</strong>
            <small>{selectedWatch?.travel_date_local || t("doorToDoor.chooseWatchedRoute")}</small>
          </div>
        </div>

        <form className="panel panel-soft d2d-form d2d-form-essentials" onSubmit={onSubmit}>
          <div className="d2d-section-head d2d-essentials-head">
            <h2>{t("doorToDoor.form.essentialsTitle")}</h2>
          </div>
          <LocationInput id="d2d-origin" label={t("doorToDoor.form.origin")} value={origin} onChange={setOrigin} field="origin" watchId={selectedWatchId} />
          <label className="field qs-label" htmlFor="d2d-watch">
            <span>{t("doorToDoor.form.watch")}</span>
            <select id="d2d-watch" className="qs-input-neutral" value={selectedWatchId} onChange={(event) => setSelectedWatchId(event.target.value)}>
              <option value="">{t("doorToDoor.form.selectWatch")}</option>
              {watches.map((watch) => (
                <option key={watch.id} value={watch.id}>{watch.origin_iata} {"->"} {watch.destination_iata} - {watch.travel_date_local}</option>
              ))}
            </select>
          </label>
          <LocationInput id="d2d-final" label={t("doorToDoor.form.finalDestination")} value={finalDestination} onChange={setFinalDestination} field="destination" watchId={selectedWatchId} />
          <label className="field d2d-checkbox-field">
            <input type="checkbox" checked={finalDestination.type === "airport_only"} onChange={(event) => setFinalDestination(event.target.checked ? { type: "airport_only", label: t("doorToDoor.defaults.airportOnly", { iata: selectedWatch?.destination_iata || "TSF" }) } : defaultDestination)} />
            {t("doorToDoor.form.airportOnly")}
          </label>
          <label className="field d2d-checkbox-field">
            <input type="checkbox" checked={saveOrigin} onChange={(event) => setSaveOrigin(event.target.checked)} />
            {t("doorToDoor.form.saveOrigin")}
          </label>
          <button className="btn-primary" type="submit" disabled={isSubmitBlocked}>{t("doorToDoor.cta")}</button>
        </form>
      </section>

      <section className="d2d-decision-grid">
        <div className="panel panel-soft d2d-route-stack">
          <div className="d2d-section-head">
            <h2>{t("doorToDoor.timeline.title")}</h2>
            {response?.flight.flight_time_confidence === "estimated" ? (
              <span className="status-pill warning">{t("doorToDoor.timeline.estimatedSchedule")}</span>
            ) : null}
          </div>
          {timelineNodes.length === 0 ? <p className="panel-note">{t("doorToDoor.timeline.empty")}</p> : (
            <ol className="d2d-segment-timeline" aria-label={t("doorToDoor.timeline.title")}>
              {timelineNodes.map((node) => (
                <li key={node.id} className="list-row d2d-segment-row">
                  <div className="d2d-segment-node" aria-hidden="true" />
                  <div className="d2d-segment-main">
                    <strong>{node.title}</strong>
                    <p className="d2d-segment-route">{node.route}</p>
                    <p className="d2d-segment-time">{node.timing}</p>
                  </div>
                  <div className="d2d-segment-meta">
                    <span className="status-pill state-info">{node.badge}</span>
                    {node.actions.length > 0 ? (
                      <>
                        {isMobile ? (
                          <button
                            type="button"
                            className="btn-ghost btn-compact d2d-actions-toggle"
                            aria-expanded={openActionsNodeId === node.id}
                            aria-controls={`d2d-actions-${node.id}`}
                            onClick={() => setOpenActionsNodeId((current) => (current === node.id ? null : node.id))}
                          >
                            {t("doorToDoor.sections.moreActions")}
                          </button>
                        ) : null}
                        <div
                          id={`d2d-actions-${node.id}`}
                          className={`row-actions d2d-row-actions ${isMobile && openActionsNodeId === node.id ? "is-open" : ""}`}
                          role="group"
                          aria-label={t("doorToDoor.sections.actionsTitle")}
                        >
                          {node.actions.map((action) => (
                            <a key={`${node.id}-${action.href}`} className="btn-secondary btn-compact" href={action.href} target="_blank" rel="noreferrer" aria-label={action.ariaLabel}>
                              <ExternalLink size={14} aria-hidden="true" />
                              <span>{action.label}</span>
                            </a>
                          ))}
                        </div>
                      </>
                    ) : null}
                  </div>
                </li>
              ))}
            </ol>
          )}
        </div>

        <aside className="panel panel-soft d2d-settings-aside">
          <details className="d2d-filters-collapse" open={!isMobile || showAdvancedFilters} onToggle={(event) => setShowAdvancedFilters((event.currentTarget as HTMLDetailsElement).open)}>
            <summary>
              <strong>{t("doorToDoor.form.decisionSettings")}</strong>
              <span>{t("doorToDoor.filters.collapseHint")}</span>
            </summary>
            <DoorToDoorFilters preferences={preferences} onChange={setPreferences} embedded={true} />
          </details>
        </aside>
      </section>

      <section className="panel panel-soft d2d-map-hub" aria-label={t("doorToDoor.mapHub.title")}>
        <div className="d2d-section-head">
          <h2>{t("doorToDoor.mapHub.title")}</h2>
          <span>{t("doorToDoor.mapHub.subtitle")}</span>
        </div>
        <p className="panel-note">{t("doorToDoor.mapHub.summary")}</p>

        <div className="d2d-map-hub-grid">
          <section className="d2d-map-section">
            <header>
              <h3><Layers3 size={16} aria-hidden="true" /> {t("doorToDoor.mapHub.sections.layers")}</h3>
              <p>{t("doorToDoor.mapHub.sections.layersBody")}</p>
            </header>
            <div className="d2d-map-cards">{mapCapabilitiesBySection.layers.map(renderCapabilityCard)}</div>
          </section>

          <section className="d2d-map-section">
            <header>
              <h3><Route size={16} aria-hidden="true" /> {t("doorToDoor.mapHub.sections.alternatives")}</h3>
              <p>{t("doorToDoor.mapHub.sections.alternativesBody")}</p>
            </header>
            <div className="d2d-map-cards">{mapCapabilitiesBySection.alternatives.map(renderCapabilityCard)}</div>
          </section>

          <section className="d2d-map-section">
            <header>
              <h3><Compass size={16} aria-hidden="true" /> {t("doorToDoor.mapHub.sections.arrival")}</h3>
              <p>{t("doorToDoor.mapHub.sections.arrivalBody")}</p>
            </header>
            <div className="d2d-map-cards">{mapCapabilitiesBySection.arrival.map(renderCapabilityCard)}</div>
          </section>

          <section className="d2d-map-section">
            <header>
              <h3><Navigation size={16} aria-hidden="true" /> {t("doorToDoor.mapHub.sections.visual")}</h3>
              <p>{t("doorToDoor.mapHub.sections.visualBody")}</p>
            </header>
            <div className="d2d-map-cards">{mapCapabilitiesBySection.visual.map(renderCapabilityCard)}</div>
          </section>

          <section className="d2d-map-section">
            <header>
              <h3><MapPin size={16} aria-hidden="true" /> {t("doorToDoor.mapHub.sections.saved")}</h3>
              <p>{t("doorToDoor.mapHub.sections.savedBody")}</p>
            </header>
            <div className="d2d-map-cards">{mapCapabilitiesBySection.saved.map(renderCapabilityCard)}</div>
            <div className="d2d-saved-places-manager">
              <label className="field qs-label" htmlFor="d2d-saved-place-label">
                <span>{t("doorToDoor.mapHub.savedPlaces.label")}</span>
                <input
                  id="d2d-saved-place-label"
                  className="qs-input-neutral"
                  value={savedPlaceLabel}
                  onChange={(event) => setSavedPlaceLabel(event.target.value)}
                  placeholder={t("doorToDoor.mapHub.savedPlaces.labelPlaceholder")}
                />
              </label>
              <label className="field qs-label" htmlFor="d2d-saved-place-note">
                <span>{t("doorToDoor.mapHub.savedPlaces.note")}</span>
                <input
                  id="d2d-saved-place-note"
                  className="qs-input-neutral"
                  value={savedPlaceNote}
                  onChange={(event) => setSavedPlaceNote(event.target.value)}
                  placeholder={t("doorToDoor.mapHub.savedPlaces.notePlaceholder")}
                />
              </label>
              <button type="button" className="btn-secondary btn-compact" onClick={addSavedPlace} disabled={!savedPlaceLabel.trim()}>
                {t("doorToDoor.mapHub.savedPlaces.add")}
              </button>
              <div className="d2d-saved-places-list">
                {visibleSavedPlaces.length === 0 ? <p className="panel-note">{t("doorToDoor.mapHub.savedPlaces.empty")}</p> : null}
                {visibleSavedPlaces.map((item) => (
                  <article key={item.id} className="d2d-saved-place-item">
                    <div>
                      <strong>{item.label}</strong>
                      {item.note ? <p>{item.note}</p> : null}
                    </div>
                    <button type="button" className="btn-ghost btn-compact" onClick={() => removeSavedPlace(item.id)}>
                      {t("doorToDoor.mapHub.savedPlaces.remove")}
                    </button>
                  </article>
                ))}
              </div>
            </div>
          </section>
        </div>
      </section>

      {status === "empty" ? <DoorToDoorEmptyState hasWatch={Boolean(selectedWatch)} /> : null}
      {status === "loading" ? <DoorToDoorLoadingState /> : null}
      {status === "error" ? <DoorToDoorErrorState message={errorMessage} onRetry={calculate} /> : null}
      {status === "no_coverage" ? (
        <section className="notice notice-warning d2d-no-coverage">
          <div>
            <strong>{t("doorToDoor.states.noCoverageTitle")}</strong>
            <p>{t("doorToDoor.states.noCoverageBody")}</p>
            <p className="panel-note"><strong>{t("doorToDoor.sections.attemptedRoute")}:</strong> {attemptedRoute}</p>
            <p className="panel-note"><strong>{t("doorToDoor.sections.providersStatus")}:</strong> {t("doorToDoor.sections.providersMix", { enabled: providerStatusSummary.enabled, real: providerStatusSummary.realEnabled, estimate: providerStatusSummary.estimateEnabled })}</p>
          </div>
          <button className="btn-secondary btn-compact" type="button" onClick={() => setPreferences({ ...preferences, min_airport_buffer_minutes: 150, max_price: null, allow_shuttle: true, allow_rideshare: true })}>{t("doorToDoor.states.noCoverageCta")}</button>
        </section>
      ) : null}

      {response && response.options.length > 0 ? (
        <>
          <section className="panel panel-soft d2d-chosen-trust">
            <div className="d2d-section-head">
              <h2>{t("doorToDoor.option.chosen")}</h2>
              <button
                type="button"
                className={`status-pill ${trustTone}`}
                onClick={() => setShowTrustModal(true)}
                aria-haspopup="dialog"
                aria-controls="d2d-trust-modal"
                aria-label={t("doorToDoor.sections.trustModalTrigger")}
              >
                {trustTone === "success" ? <ShieldCheck size={14} aria-hidden="true" /> : <ShieldAlert size={14} aria-hidden="true" />}
                <span>{trustTone === "success" ? t("doorToDoor.sections.trustConfirmed") : t("doorToDoor.sections.trustEstimated")}</span>
              </button>
            </div>
            {selectedPlan ? (
              <p className="panel-note">
                <strong>{selectedPlan.label}</strong>
                {" · "}
                {selectedPlan.total_price_min ?? "--"}-{selectedPlan.total_price_max ?? "--"} {selectedPlan.currency}
              </p>
            ) : (
              <p className="panel-note">{t("doorToDoor.sections.trustNoPlan")}</p>
            )}
          </section>

          {realResults.length > 0 ? (
            <section className="d2d-results-section">
              <div className="d2d-section-head">
                <h2>{t("doorToDoor.sections.realResults")}</h2>
                <span className="status-pill success">{realResults.length}</span>
              </div>
              <div className="d2d-options-stack">
                {realResults.map((option) => (
                  <DoorToDoorOptionCard
                    key={option.id}
                    option={option}
                    chosen={option.id === chosenOptionId}
                    quickBadges={quickBadgesByOption[option.id] ?? []}
                    reasons={option.id === recommendedOption?.id ? recommendedReasons : []}
                    trustInline={option.id === recommendedOption?.id && hasUncertainSources(option)}
                    onChoose={() => markChosen(option)}
                  />
                ))}
              </div>
            </section>
          ) : null}

          {recommendedOption && alternativeDeltas.length > 0 ? (
            <section className="panel panel-soft d2d-option-comparator">
              <details className="d2d-compare-collapse" open={!isMobile}>
                <summary>
                  <strong>{t("doorToDoor.option.comparatorTitle")}</strong>
                </summary>
                <div className="d2d-compare-table" role="table" aria-label={t("doorToDoor.option.comparatorTitle")}>
                  {alternativeDeltas.map((delta) => (
                    <article key={delta.option_id} className="d2d-compare-row" role="row">
                      <strong className="d2d-compare-option">{delta.option_label}</strong>
                      <span className={`d2d-compare-metric ${delta.delta_price != null && delta.delta_price <= 0 ? "is-better" : "is-worse"}`}>
                        {t("doorToDoor.option.compare.price")}: {formatDelta(delta.delta_price, " EUR")}
                      </span>
                      <span className={`d2d-compare-metric ${delta.delta_duration_minutes != null && delta.delta_duration_minutes <= 0 ? "is-better" : "is-worse"}`}>
                        {t("doorToDoor.option.compare.duration")}: {formatDelta(delta.delta_duration_minutes, "m")}
                      </span>
                      <span className={`d2d-compare-metric ${delta.delta_buffer_minutes != null && delta.delta_buffer_minutes >= 0 ? "is-better" : "is-worse"}`}>
                        {t("doorToDoor.option.compare.buffer")}: {formatDelta(delta.delta_buffer_minutes, "m")}
                      </span>
                      <span className={`d2d-compare-metric ${delta.risk_change === "better" ? "is-better" : delta.risk_change === "worse" ? "is-worse" : ""}`}>
                        {t("doorToDoor.option.compare.risk")}: {t(`doorToDoor.option.compareRisk.${delta.risk_change}`)}
                      </span>
                    </article>
                  ))}
                </div>
              </details>
            </section>
          ) : null}

          {realDeeplinks.length > 0 ? (
            <section className="d2d-results-section">
              <div className="d2d-section-head">
                <h2>{t("doorToDoor.sections.realDeeplinks")}</h2>
                <span className="status-pill info">{realDeeplinks.length}</span>
              </div>
              <p className="panel-note">{t("doorToDoor.sections.limitedComparisonBody")}</p>
              <div className="d2d-options-stack">
                {realDeeplinks.map((option) => (
                  <DoorToDoorOptionCard
                    key={option.id}
                    option={option}
                    chosen={option.id === chosenOptionId}
                    quickBadges={quickBadgesByOption[option.id] ?? []}
                    onChoose={() => markChosen(option)}
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
                {estimateOptions.map((option) => (
                  <DoorToDoorOptionCard
                    key={option.id}
                    option={option}
                    chosen={option.id === chosenOptionId}
                    quickBadges={quickBadgesByOption[option.id] ?? []}
                    onChoose={() => markChosen(option)}
                  />
                ))}
              </div>
            </section>
          ) : null}
        </>
      ) : null}

      <section className="panel panel-soft d2d-history-panel">
        <div className="action-row d2d-history-action-row">
          <button type="button" className="btn-secondary" onClick={() => setShowHistory((current) => !current)} aria-expanded={showHistory} aria-controls="d2d-history-content">
            {showHistory ? t("doorToDoor.sections.hideHistoryAction") : t("doorToDoor.sections.showHistoryAction")}
          </button>
        </div>
        {showHistory ? (
          <div id="d2d-history-content" className="d2d-history-content" aria-live="polite">
            <div className="panel-header"><h2 className="panel-title">{t("doorToDoor.sections.history")}</h2></div>
            {history.length === 0 ? <p className="panel-note">{t("doorToDoor.sections.historyEmpty")}</p> : (
              <div className="d2d-history-list">
                {history.map((item) => (
                  <article key={item.id}>
                    <strong>{item.origin_label} {"->"} {item.final_destination_label}</strong>
                    <span>{formatHistoryDate(item.created_at, localeTag)} - {item.recommended_label || t("doorToDoor.history.noRecommendation")} - {item.total_price_min ?? "--"}-{item.total_price_max ?? "--"} EUR - {item.risk_level || "--"}</span>
                    {item.chosen_option_id ? <em>{t("doorToDoor.history.chosen")}</em> : null}
                  </article>
                ))}
              </div>
            )}
          </div>
        ) : null}
      </section>

      {showTrustModal ? (
        <div className="modal-overlay d2d-trust-overlay" onClick={() => setShowTrustModal(false)}>
          <section id="d2d-trust-modal" className="modal-card d2d-trust-modal" role="dialog" aria-modal="true" aria-label={t("doorToDoor.sections.trustModalTitle")} onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <h2>{t("doorToDoor.sections.trustModalTitle")}</h2>
              <button type="button" className="modal-close" onClick={() => setShowTrustModal(false)} aria-label={t("shared.actions.close")}>x</button>
            </div>
            <p className="panel-note">{trustTone === "success" ? t("doorToDoor.sections.trustModalBodyConfirmed") : t("doorToDoor.sections.trustModalBodyEstimated")}</p>
            <p className="panel-note">{t("doorToDoor.sections.trustModalBodyAction")}</p>
          </section>
        </div>
      ) : null}
    </main>
  );
}
