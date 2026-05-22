"use client";

import React, { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { useRouter, useSearchParams } from "next/navigation";

import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { useI18n } from "@/i18n";
import { apiFetch } from "@/modules/shared/api";
import type { Watch } from "@/modules/watchlist/types";
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
import type {
  DoorToDoorHistoryItem,
  DoorToDoorLocation,
  DoorToDoorOption,
  DoorToDoorProviderStatus,
  DoorToDoorPreferences,
  DoorToDoorResponse,
  DoorToDoorSuggestion,
} from "@/modules/door-to-door/types";

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

function useSuggestionSearch(value: string) {
  const [suggestions, setSuggestions] = useState<DoorToDoorSuggestion[]>([]);
  useEffect(() => {
    let alive = true;
    fetchDoorToDoorSuggestions(value)
      .then((items) => {
        if (alive) setSuggestions(items.slice(0, 6));
      })
      .catch(() => {
        if (alive) setSuggestions([]);
      });
    return () => {
      alive = false;
    };
  }, [value]);
  return suggestions;
}

function LocationInput({
  id,
  label,
  value,
  onChange,
}: {
  id: string;
  label: string;
  value: DoorToDoorLocation;
  onChange: (location: DoorToDoorLocation) => void;
}) {
  const [focused, setFocused] = useState(false);
  const suggestions = useSuggestionSearch(value.label);
  return (
    <label className="field d2d-autocomplete" htmlFor={id}>
      {label}
      <input
        id={id}
        className="prefs-control"
        value={value.label}
        onChange={(event) => onChange({ ...value, label: event.target.value, type: value.type || "city" })}
        onFocus={() => setFocused(true)}
        onBlur={() => window.setTimeout(() => setFocused(false), 120)}
        autoComplete="off"
      />
      {focused && suggestions.length > 0 ? (
        <div className="d2d-suggestions" role="listbox" aria-label={`${label}: sugerencias`}>
          {suggestions.map((suggestion) => (
            <button
              key={suggestion.id}
              type="button"
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => {
                onChange(suggestion);
                setFocused(false);
              }}
            >
              <strong>{suggestion.label}</strong>
              <span>{suggestion.subtitle}</span>
            </button>
          ))}
        </div>
      ) : null}
    </label>
  );
}

function formatHistoryDate(value: string, localeTag: string) {
  return new Intl.DateTimeFormat(localeTag, { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
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
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    setSelectedWatchId(watchIdParam);
  }, [watchIdParam]);

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

  const selectedWatch = useMemo(() => watches.find((watch) => watch.id === selectedWatchId) || null, [watches, selectedWatchId]);

  // Group options by status
  const realResults = useMemo(() => response?.options.filter((o) => o.status === "real_result") ?? [], [response]);
  const realDeeplinks = useMemo(() => response?.options.filter((o) => o.status === "real_deeplink") ?? [], [response]);
  const estimateOptions = useMemo(() => response?.options.filter((o) => o.status === "estimate_only") ?? [], [response]);

  const hasResults = realResults.length > 0 || realDeeplinks.length > 0;
  const hasEstimates = estimateOptions.length > 0;

  const attemptedRoute = `${origin.label || "—"} → ${selectedWatch?.origin_iata || "AGP"} → ${selectedWatch?.destination_iata || "TSF"} → ${finalDestination.label || "—"}`;
  const providerStatusSummary = useMemo(() => {
    const enabled = providerStatus.filter((provider) => provider.enabled);
    const realEnabled = enabled.filter((provider) => provider.source_type !== "mock" && provider.source_type !== "estimate");
    const estimateEnabled = enabled.filter((provider) => provider.source_type === "mock" || provider.source_type === "estimate");
    return { enabled: enabled.length, realEnabled: realEnabled.length, estimateEnabled: estimateEnabled.length, enabledNames: enabled.map((provider) => provider.name) };
  }, [providerStatus]);

  const decisionModeLabel = t(`doorToDoor.filters.${preferences.sort_by === "best_balance" ? "bestBalance" : preferences.sort_by === "cheapest" ? "cheapest" : preferences.sort_by === "lowest_risk" ? "lowestRisk" : preferences.sort_by === "fastest" ? "fastest" : "fewestChanges"}`);

  // Build segment deeplinks
  const segmentLinks = useMemo(() => {
    if (!selectedWatch) return null;
    const originLabel = origin.label;
    const destLabel = finalDestination.label;
    const originIata = selectedWatch.origin_iata;
    const destIata = selectedWatch.destination_iata;
    const travelDate = selectedWatch.travel_date_local;

    const mapsOutbound = `https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(originLabel)}&destination=${encodeURIComponent(originIata + " Airport")}&travelmode=driving&dir_action=navigate`;
    const mapsInbound = destLabel ? `https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(destIata + " Airport")}&destination=${encodeURIComponent(destLabel)}&travelmode=driving&dir_action=navigate` : null;
    const blablacarUrl = `https://www.blablacar.es/search?from=${encodeURIComponent(originLabel)}&to=${encodeURIComponent(originIata)}&date=${travelDate || ""}`;
    const gooptiUrl = destLabel ? `https://www.goopti.com/es/?pickup=${encodeURIComponent("Aeropuerto de " + destIata)}&dropoff=${encodeURIComponent(destLabel)}&date=${travelDate || ""}` : null;

    return { mapsOutbound, mapsInbound, blablacarUrl, gooptiUrl };
  }, [selectedWatch, origin.label, finalDestination.label]);

  const calculate = useCallback(async () => {
    if (!selectedWatch) {
      setStatus("empty");
      return;
    }
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
      setResponse(data);
      setChosenOptionId(data.summary.chosen_option_id || "");
      if (data.options.length === 0) {
        setStatus("no_coverage");
      } else if (data.warnings.length > 0) {
        setStatus("partial");
      } else {
        setStatus("success");
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Error inesperado");
      setStatus("error");
    }
  }, [finalDestination, origin, preferences, saveOrigin, selectedWatch]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
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

      {/* --- Form Section --- */}
      <section className="panel d2d-ops-panel">
        <div className="d2d-hero">
          <div>
            <span className="d2d-mini-kicker">{t("doorToDoor.miniKicker")}</span>
            <h2>{t("doorToDoor.heroTitle")}</h2>
            <p>{t("doorToDoor.heroBody")}</p>
          </div>
          <div className="d2d-hero-ticket" aria-label={t("doorToDoor.selectedFlight")}>
            <span>{t("doorToDoor.form.preparationTitle")}</span>
            <strong>{selectedWatch ? `${selectedWatch.origin_iata} → ${selectedWatch.destination_iata}` : t("doorToDoor.noFlight")}</strong>
            <small>{selectedWatch?.travel_date_local || t("doorToDoor.chooseWatchedRoute")}</small>
          </div>
        </div>

        <div className="d2d-ops-summary">
          <span><strong>{t("doorToDoor.form.origin")}:</strong> {origin.label || "—"}</span>
          <span><strong>{t("doorToDoor.form.watch")}:</strong> {selectedWatch ? `${selectedWatch.origin_iata} → ${selectedWatch.destination_iata}` : "—"}</span>
          <span><strong>{t("doorToDoor.form.finalDestination")}:</strong> {finalDestination.label || "—"}</span>
          <span><strong>{t("doorToDoor.filters.minBuffer")}:</strong> {preferences.min_airport_buffer_minutes} min</span>
          <span><strong>{t("doorToDoor.form.decisionMode")}:</strong> {decisionModeLabel}</span>
        </div>

        <form className="panel panel-soft d2d-form d2d-form-essentials" onSubmit={onSubmit}>
          <div className="d2d-section-head d2d-essentials-head">
            <h2>{t("doorToDoor.form.essentialsTitle")}</h2>
          </div>
          <label className="field" htmlFor="d2d-watch">
            {t("doorToDoor.form.watch")}
            <select id="d2d-watch" className="prefs-control" value={selectedWatchId} onChange={(event) => setSelectedWatchId(event.target.value)}>
              <option value="">{t("doorToDoor.form.selectWatch")}</option>
              {watches.map((watch) => (
                <option key={watch.id} value={watch.id}>{watch.origin_iata} → {watch.destination_iata} · {watch.travel_date_local}</option>
              ))}
            </select>
          </label>
          <LocationInput id="d2d-origin" label={t("doorToDoor.form.origin")} value={origin} onChange={setOrigin} />
          <LocationInput id="d2d-final" label={t("doorToDoor.form.finalDestination")} value={finalDestination} onChange={setFinalDestination} />
          <label className="field d2d-checkbox-field">
            <input type="checkbox" checked={finalDestination.type === "airport_only"} onChange={(event) => setFinalDestination(event.target.checked ? { type: "airport_only", label: t("doorToDoor.defaults.airportOnly", { iata: selectedWatch?.destination_iata || "TSF" }) } : defaultDestination)} />
            {t("doorToDoor.form.airportOnly")}
          </label>
          <label className="field d2d-checkbox-field">
            <input type="checkbox" checked={saveOrigin} onChange={(event) => setSaveOrigin(event.target.checked)} />
            {t("doorToDoor.form.saveOrigin")}
          </label>
          <button className="btn-primary" type="submit" disabled={!selectedWatch || status === "loading"}>{t("doorToDoor.cta")}</button>
        </form>

        <details className="panel panel-soft d2d-filters-collapse" open={!isMobile || showAdvancedFilters} onToggle={(event) => setShowAdvancedFilters((event.currentTarget as HTMLDetailsElement).open)}>
          <summary>
            <strong>{t("doorToDoor.form.decisionSettings")}</strong>
            <span>{t("doorToDoor.filters.collapseHint")}</span>
          </summary>
          <DoorToDoorFilters preferences={preferences} onChange={setPreferences} embedded={true} />
        </details>
      </section>

      {/* --- States --- */}
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

      {/* --- Trip Summary --- */}
      {response && response.options.length > 0 ? (
        <>
          <section className="d2d-trip-summary">
            <h2>{t("doorToDoor.sections.tripSummary")}</h2>
            <div className="d2d-trip-flow">
              <span className="d2d-trip-node">{origin.label}</span>
              <span className="d2d-trip-arrow">→</span>
              <span className="d2d-trip-node d2d-trip-airport">{selectedWatch?.origin_iata}</span>
              <span className="d2d-trip-arrow">✈</span>
              <span className="d2d-trip-node d2d-trip-airport">{selectedWatch?.destination_iata}</span>
              <span className="d2d-trip-arrow">→</span>
              <span className="d2d-trip-node">{finalDestination.label}</span>
            </div>
            {response.flight.flight_time_confidence === "estimated" ? (
              <p className="panel-note warning">{t("doorToDoor.gtfsWarnings.feedUnavailable")} — {t("doorToDoor.source.estimated")}</p>
            ) : null}
          </section>

          {/* --- Real Results (GTFS, real APIs) --- */}
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
                    onChoose={() => markChosen(option)}
                  />
                ))}
              </div>
            </section>
          ) : null}

          {/* --- Real Deeplinks (Google Maps, BlaBlaCar, GoOpti) --- */}
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
                    onChoose={() => markChosen(option)}
                  />
                ))}
              </div>
            </section>
          ) : null}

          {/* --- Segment Actions (quick access to external searches) --- */}
          {segmentLinks ? (
            <section className="panel panel-soft d2d-segment-actions">
              <h2>{t("doorToDoor.sections.actionsTitle")}</h2>

              <div className="d2d-segment">
                <strong>{t("doorToDoor.sections.segmentOutbound")}</strong>
                <p>{origin.label} → {selectedWatch?.origin_iata}</p>
                <div className="d2d-segment-links">
                  <a className="btn-secondary btn-compact" href={segmentLinks.mapsOutbound} target="_blank" rel="noreferrer">
                    {t("doorToDoor.sections.openGoogleMaps")}
                  </a>
                  <a className="btn-secondary btn-compact" href={segmentLinks.blablacarUrl} target="_blank" rel="noreferrer">
                    {t("doorToDoor.sections.openBlaBlaCarAction")}
                  </a>
                </div>
              </div>

              <div className="d2d-segment">
                <strong>{t("doorToDoor.sections.segmentFlight")}</strong>
                <p>{selectedWatch?.origin_iata} → {selectedWatch?.destination_iata} · {selectedWatch?.travel_date_local}</p>
                {response.flight.flight_time_confidence === "estimated" ? (
                  <span className="status-pill warning">{t("doorToDoor.timeline.estimatedSchedule")}</span>
                ) : null}
              </div>

              {finalDestination.type !== "airport_only" ? (
                <div className="d2d-segment">
                  <strong>{t("doorToDoor.sections.segmentInbound")}</strong>
                  <p>{selectedWatch?.destination_iata} → {finalDestination.label}</p>
                  <div className="d2d-segment-links">
                    {segmentLinks.mapsInbound ? (
                      <a className="btn-secondary btn-compact" href={segmentLinks.mapsInbound} target="_blank" rel="noreferrer">
                        {t("doorToDoor.sections.openGoogleMaps")}
                      </a>
                    ) : null}
                    {segmentLinks.gooptiUrl ? (
                      <a className="btn-secondary btn-compact" href={segmentLinks.gooptiUrl} target="_blank" rel="noreferrer">
                        {t("doorToDoor.sections.openGoOptiAction")}
                      </a>
                    ) : null}
                  </div>
                </div>
              ) : null}
            </section>
          ) : null}

          {/* --- Estimate Only (fallback at the bottom) --- */}
          {hasEstimates ? (
            <section className="panel panel-soft d2d-estimate-section">
              <div className="d2d-section-head">
                <h2>{t("doorToDoor.sections.estimateOnly")}</h2>
                <span className="status-pill warning">{t("doorToDoor.source.estimated")}</span>
              </div>
              <p className="panel-note">{t("doorToDoor.sections.estimateExplanation")}</p>
              <div className="d2d-options-stack">
                {estimateOptions.map((option) => (
                  <DoorToDoorOptionCard
                    key={option.id}
                    option={option}
                    chosen={option.id === chosenOptionId}
                    onChoose={() => markChosen(option)}
                  />
                ))}
              </div>
            </section>
          ) : null}

          {/* --- Provider Status --- */}
          <section className="panel panel-soft d2d-sources-panel">
            <div className="panel-header"><h2 className="panel-title">{t("doorToDoor.sections.sources")}</h2></div>
            <p className="panel-note">
              <strong>{t("doorToDoor.sections.providersStatus")}:</strong> {t("doorToDoor.sections.providersMix", { enabled: providerStatusSummary.enabled, real: providerStatusSummary.realEnabled, estimate: providerStatusSummary.estimateEnabled })}
            </p>
            {response.warnings.length > 0 ? (
              <div className="d2d-warnings-list">
                {response.warnings.map((warning) => (
                  <p key={`${warning.code}-${warning.provider || "global"}`} className="panel-note">
                    <strong>{warning.code}:</strong> {warning.message}
                  </p>
                ))}
              </div>
            ) : null}
          </section>
        </>
      ) : null}

      {/* --- History --- */}
      <section className="panel panel-soft d2d-history-panel">
        <div className="panel-header"><h2 className="panel-title">{t("doorToDoor.sections.history")}</h2></div>
        {history.length === 0 ? <p className="panel-note">{t("doorToDoor.sections.historyEmpty")}</p> : (
          <div className="d2d-history-list">
            {history.map((item) => (
              <article key={item.id}>
                <strong>{item.origin_label} → {item.final_destination_label}</strong>
                <span>{formatHistoryDate(item.created_at, localeTag)} · {item.recommended_label || t("doorToDoor.history.noRecommendation")} · {item.total_price_min ?? "--"}-{item.total_price_max ?? "--"} € · {item.risk_level || "--"}</span>
                {item.chosen_option_id ? <em>{t("doorToDoor.history.chosen")}</em> : null}
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
