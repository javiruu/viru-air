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
  fetchDoorToDoorSuggestions,
  fetchSavedDoorToDoorLocation,
  searchDoorToDoor,
} from "@/modules/door-to-door/api";
import { DoorToDoorEmptyState } from "@/modules/door-to-door/components/DoorToDoorEmptyState";
import { DoorToDoorErrorState } from "@/modules/door-to-door/components/DoorToDoorErrorState";
import { DoorToDoorFilters } from "@/modules/door-to-door/components/DoorToDoorFilters";
import { DoorToDoorLoadingState } from "@/modules/door-to-door/components/DoorToDoorLoadingState";
import { DoorToDoorOptionCard } from "@/modules/door-to-door/components/DoorToDoorOptionCard";
import { DoorToDoorRouteVisual } from "@/modules/door-to-door/components/DoorToDoorRouteVisual";
import { DoorToDoorTimeline } from "@/modules/door-to-door/components/DoorToDoorTimeline";
import type {
  DoorToDoorHistoryItem,
  DoorToDoorLocation,
  DoorToDoorLocationType,
  DoorToDoorOption,
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

const DEFAULT_ORIGIN: DoorToDoorLocation = { type: "city", label: "Almería", lat: 36.834, lng: -2.463 };
const DEFAULT_DESTINATION: DoorToDoorLocation = { type: "city", label: "Treviso centro" };

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

export function DoorToDoorPanel() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { t } = useI18n();
  const { notify } = useNotificationCenter();
  const watchIdParam = searchParams?.get("watchId") || "";
  const [watches, setWatches] = useState<Watch[]>([]);
  const [selectedWatchId, setSelectedWatchId] = useState(watchIdParam);
  const [origin, setOrigin] = useState<DoorToDoorLocation>(DEFAULT_ORIGIN);
  const [finalDestination, setFinalDestination] = useState<DoorToDoorLocation>(DEFAULT_DESTINATION);
  const [preferences, setPreferences] = useState<DoorToDoorPreferences>(DEFAULT_PREFERENCES);
  const [saveOrigin, setSaveOrigin] = useState(false);
  const [status, setStatus] = useState<"empty" | "loading" | "success" | "partial" | "error" | "no_coverage">("empty");
  const [response, setResponse] = useState<DoorToDoorResponse | null>(null);
  const [selectedOptionId, setSelectedOptionId] = useState<string>("");
  const [chosenOptionId, setChosenOptionId] = useState<string>("");
  const [history, setHistory] = useState<DoorToDoorHistoryItem[]>([]);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    apiFetch<Watch[]>("/watchlist")
      .then((items) => {
        setWatches(items);
        if (!selectedWatchId && items[0]) setSelectedWatchId(items[0].id);
      })
      .catch(() => setWatches([]));
    fetchSavedDoorToDoorLocation()
      .then((saved) => {
        if (saved) setOrigin({ type: saved.type, label: saved.label, lat: saved.lat, lng: saved.lng });
      })
      .catch(() => undefined);
  }, [selectedWatchId]);

  useEffect(() => {
    if (!selectedWatchId) return;
    fetchDoorToDoorHistory(selectedWatchId)
      .then((items) => setHistory(items))
      .catch(() => setHistory([]));
  }, [selectedWatchId, chosenOptionId, response?.summary.history_id]);

  const selectedWatch = useMemo(() => watches.find((watch) => watch.id === selectedWatchId) || null, [watches, selectedWatchId]);
  const selectedOption = useMemo(() => response?.options.find((option) => option.id === selectedOptionId) || response?.options[0] || null, [response, selectedOptionId]);
  const primaryOptions = response?.options.filter((option) => !option.is_extended).slice(0, 3) ?? [];
  const extendedOptions = response?.options.filter((option) => option.is_extended).slice(0, 5) ?? [];

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
      setSelectedOptionId(data.summary.recommended_option_id || data.options[0]?.id || "");
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
      notify({ tone: "success", title: "Plan elegido guardado" });
    } catch {
      notify({ tone: "error", title: "No se pudo guardar la elección" });
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
        <span className="status-pill info">Flight intelligence</span>
      </div>

      <section className="panel d2d-hero">
        <div>
          <span className="d2d-mini-kicker">AGP · TSF · puerta real</span>
          <h2>{t("doorToDoor.heroTitle")}</h2>
          <p>{t("doorToDoor.heroBody")}</p>
        </div>
        <div className="d2d-hero-ticket" aria-label="Resumen de vuelo seleccionado">
          <span>Vuelo seleccionado</span>
          <strong>{selectedWatch ? `${selectedWatch.origin_iata} → ${selectedWatch.destination_iata}` : "Sin vuelo"}</strong>
          <small>{selectedWatch?.travel_date_local || "Elige una ruta vigilada"}</small>
        </div>
      </section>

      <form className="panel panel-soft d2d-form" onSubmit={onSubmit}>
        <label className="field" htmlFor="d2d-watch">
          Vuelo guardado
          <select id="d2d-watch" className="prefs-control" value={selectedWatchId} onChange={(event) => setSelectedWatchId(event.target.value)}>
            <option value="">Seleccionar vuelo…</option>
            {watches.map((watch) => (
              <option key={watch.id} value={watch.id}>{watch.origin_iata} → {watch.destination_iata} · {watch.travel_date_local}</option>
            ))}
          </select>
        </label>
        <LocationInput id="d2d-origin" label="Origen terrestre" value={origin} onChange={setOrigin} />
        <LocationInput id="d2d-final" label="Destino final al aterrizar" value={finalDestination} onChange={setFinalDestination} />
        <label className="field d2d-checkbox-field">
          <input type="checkbox" checked={finalDestination.type === "airport_only"} onChange={(event) => setFinalDestination(event.target.checked ? { type: "airport_only", label: `Solo aeropuerto ${selectedWatch?.destination_iata || "TSF"}` } : DEFAULT_DESTINATION)} />
          Terminar solo en el aeropuerto de llegada
        </label>
        <label className="field d2d-checkbox-field">
          <input type="checkbox" checked={saveOrigin} onChange={(event) => setSaveOrigin(event.target.checked)} />
          ¿Quieres guardar este origen para futuros vuelos? Puedes borrarlo cuando quieras en Preferencias.
        </label>
        <button className="btn-primary" type="submit" disabled={!selectedWatch || status === "loading"}>{t("doorToDoor.cta")}</button>
      </form>

      <DoorToDoorFilters preferences={preferences} onChange={setPreferences} />

      {status === "empty" ? <DoorToDoorEmptyState hasWatch={Boolean(selectedWatch)} /> : null}
      {status === "loading" ? <DoorToDoorLoadingState /> : null}
      {status === "error" ? <DoorToDoorErrorState message={errorMessage} onRetry={calculate} /> : null}
      {status === "no_coverage" ? (
        <section className="notice notice-warning d2d-no-coverage">
          <div>
            <strong>No hay cobertura suficiente para esta ruta.</strong>
            <p>Prueba a subir el margen, permitir shuttle/coche compartido o terminar solo en aeropuerto.</p>
          </div>
          <button className="btn-secondary btn-compact" type="button" onClick={() => setPreferences({ ...preferences, min_airport_buffer_minutes: 150, allow_shuttle: true, allow_rideshare: true })}>Aplicar ajustes sugeridos</button>
        </section>
      ) : null}

      {response && response.options.length > 0 ? (
        <>
          <section className="notice notice-info d2d-success-copy" role="status" aria-live="polite">
            <strong>{status === "partial" ? "Fuente parcial" : "Ruta completa calculada."}</strong>
            <span>{status === "partial" ? "No todas las fuentes están activas; revisa precio, margen y riesgo antes de decidir." : "Revisa precio, margen y riesgo antes de decidir."}</span>
          </section>

          <section className="d2d-decision-grid">
            <div className="d2d-options-stack">
              <div className="d2d-section-head">
                <h2>Opciones principales</h2>
                <span>{response.options.length} rutas mock normalizadas</span>
              </div>
              {primaryOptions.map((option) => (
                <DoorToDoorOptionCard key={option.id} option={option} selected={option.id === selectedOption?.id} chosen={option.id === chosenOptionId} onSelect={() => setSelectedOptionId(option.id)} onChoose={() => markChosen(option)} />
              ))}
              {extendedOptions.length > 0 ? (
                <div className="d2d-extended-list">
                  <h3>Ranking extendido</h3>
                  {extendedOptions.map((option) => (
                    <DoorToDoorOptionCard key={option.id} option={option} selected={option.id === selectedOption?.id} chosen={option.id === chosenOptionId} onSelect={() => setSelectedOptionId(option.id)} onChoose={() => markChosen(option)} />
                  ))}
                </div>
              ) : null}
            </div>
            <div className="d2d-route-stack">
              <DoorToDoorRouteVisual option={selectedOption} flight={response.flight} />
              <DoorToDoorTimeline option={selectedOption} flight={response.flight} />
            </div>
          </section>

          <section className="panel panel-soft d2d-sources-panel">
            <div className="panel-header"><h2 className="panel-title">Fuentes y confianza</h2></div>
            {response.warnings.map((warning) => <p key={`${warning.code}-${warning.provider || "global"}`} className="panel-note"><strong>{warning.code}:</strong> {warning.message}</p>)}
          </section>
        </>
      ) : null}

      <section className="panel panel-soft d2d-history-panel">
        <div className="panel-header"><h2 className="panel-title">Últimos cálculos</h2></div>
        {history.length === 0 ? <p className="panel-note">Aún no hay cálculos guardados para este vuelo.</p> : (
          <div className="d2d-history-list">
            {history.map((item) => (
              <article key={item.id}>
                <strong>{item.origin_label} → {item.final_destination_label}</strong>
                <span>{item.recommended_label || "Sin recomendación"} · {item.total_price_min ?? "--"}-{item.total_price_max ?? "--"} € · {item.risk_level || "--"}</span>
                {item.chosen_option_id ? <em>Plan elegido</em> : null}
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
