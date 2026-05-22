import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { DoorToDoorErrorState } from "../src/modules/door-to-door/components/DoorToDoorErrorState";
import { DoorToDoorFilters } from "../src/modules/door-to-door/components/DoorToDoorFilters";
import { DoorToDoorOptionCard } from "../src/modules/door-to-door/components/DoorToDoorOptionCard";
import { DoorToDoorRouteVisual } from "../src/modules/door-to-door/components/DoorToDoorRouteVisual";
import { DoorToDoorTimeline } from "../src/modules/door-to-door/components/DoorToDoorTimeline";
import type { DoorToDoorFlight, DoorToDoorOption, DoorToDoorPreferences } from "../src/modules/door-to-door/types";

const ROOT = process.cwd();
const PAGE = path.join(ROOT, "src", "app", "(private)", "puerta-a-puerta", "page.tsx");
const PANEL = path.join(ROOT, "src", "modules", "door-to-door", "DoorToDoorPanel.tsx");
const API = path.join(ROOT, "src", "modules", "door-to-door", "api.ts");
const NAV = path.join(ROOT, "src", "modules", "shared", "navigationV1.ts");
const WATCH_DETAIL = path.join(ROOT, "src", "modules", "watchlist", "components", "WatchDetailPanel.tsx");
const STYLES = path.join(ROOT, "src", "styles", "screens.css");
const MODULE_DIR = path.join(ROOT, "src", "modules", "door-to-door");
const D2D_I18N = path.join(ROOT, "src", "i18n", "domains", "doorToDoor.ts");

const flight: DoorToDoorFlight = {
  origin_airport: "AGP",
  destination_airport: "TSF",
  departure_at: "2026-06-14T14:20:00+02:00",
  arrival_at: "2026-06-14T16:55:00+02:00",
  flight_time_confidence: "estimated",
};

const mockOption: DoorToDoorOption = {
  id: "option_best",
  label: "Mejor equilibrio",
  description: "Sales de Almería con margen cómodo antes del vuelo.",
  total_price_min: 42,
  total_price_max: 68,
  price_per_person_min: 42,
  price_per_person_max: 68,
  currency: "EUR",
  total_duration_minutes: 515,
  risk_level: "low",
  score: 86,
  transfer_count: 2,
  airport_buffer_minutes: 140,
  confidence: "estimated",
  source_types: ["mock"],
  sources: [{ provider: "mock_bus", source_provider: "mock_bus", source_type: "mock", confidence: "estimated", checked_at: "2026-05-20T10:00:00+02:00" }],
  is_recommended: true,
  is_extended: false,
  legs: [
    { type: "ground", mode: "bus", from: "Almería", to: "Aeropuerto de Málaga AGP", departure_at: "2026-06-14T08:10:00+02:00", arrival_at: "2026-06-14T12:00:00+02:00", duration_minutes: 230, price_min: 18, price_max: 28, provider: "mock_bus", source_type: "mock", confidence: "estimated" },
    { type: "flight", mode: "flight", from: "AGP", to: "TSF", departure_at: "2026-06-14T14:20:00+02:00", arrival_at: "2026-06-14T16:55:00+02:00", duration_minutes: 155, provider: "flight_watch", source_type: "mock", confidence: "estimated" },
    { type: "ground", mode: "shuttle", from: "Treviso Airport TSF", to: "Treviso centro", departure_at: "2026-06-14T17:30:00+02:00", arrival_at: "2026-06-14T18:10:00+02:00", duration_minutes: 40, price_min: 12, price_max: 20, provider: "mock_shuttle", source_type: "mock", confidence: "estimated" },
  ],
};

const deeplinkOption: DoorToDoorOption = {
  id: "option_blablacar_deeplink",
  label: "Ruta con BlaBlaCar",
  description: "Enlace directo para tramo terrestre de salida. Precio final en proveedor.",
  total_price_min: null,
  total_price_max: null,
  price_per_person_min: null,
  price_per_person_max: null,
  currency: "EUR",
  total_duration_minutes: 510,
  risk_level: "medium",
  score: 71,
  transfer_count: 2,
  airport_buffer_minutes: 130,
  confidence: "deeplink",
  source_types: ["deeplink"],
  sources: [
    {
      provider: "blablacar_deeplink",
      source_provider: "blablacar",
      source_type: "deeplink",
      confidence: "deeplink",
      checked_at: "2026-05-20T10:00:00+02:00",
      booking_url: "https://www.blablacar.es/search?from=Almeria&to=Malaga",
    },
  ],
  is_recommended: false,
  is_extended: true,
  legs: [
    { type: "ground", mode: "rideshare", from: "Almería", to: "Aeropuerto de Málaga AGP", duration_minutes: 230, provider: "blablacar", source_type: "deeplink", confidence: "deeplink", booking_url: "https://www.blablacar.es/search?from=Almeria&to=Malaga" },
    { type: "flight", mode: "flight", from: "AGP", to: "TSF", duration_minutes: 155, provider: "flight_watch", source_type: "api", confidence: "estimated" },
  ],
};

const apiRouteOption: DoorToDoorOption = {
  id: "option_google_routes",
  label: "Duración real de ruta terrestre",
  description: "Duración y distancia calculadas con proveedor de rutas.",
  total_price_min: null,
  total_price_max: null,
  price_per_person_min: null,
  price_per_person_max: null,
  currency: "EUR",
  total_duration_minutes: 505,
  risk_level: "medium",
  score: 72,
  transfer_count: 2,
  airport_buffer_minutes: 130,
  confidence: "live",
  source_types: ["api"],
  sources: [
    {
      provider: "google_routes",
      source_provider: "google_routes",
      source_type: "api",
      confidence: "live",
      checked_at: "2026-05-20T10:00:00+02:00",
    },
  ],
  is_recommended: false,
  is_extended: false,
  legs: [
    { type: "ground", mode: "car", from: "Almería", to: "Aeropuerto de Málaga AGP", duration_minutes: 210, distance_meters: 198000, provider: "google_routes", source_type: "api", confidence: "live" },
    { type: "flight", mode: "flight", from: "AGP", to: "TSF", duration_minutes: 155, provider: "flight_watch", source_type: "api", confidence: "estimated" },
    { type: "ground", mode: "car", from: "Treviso Airport TSF", to: "Treviso centro", duration_minutes: 35, distance_meters: 6000, provider: "google_routes", source_type: "api", confidence: "live" },
  ],
};

const preferences: DoorToDoorPreferences = {
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

function readAllDoorToDoorSource() {
  const files = fs.readdirSync(MODULE_DIR, { recursive: true }).filter((item) => String(item).endsWith(".tsx") || String(item).endsWith(".ts"));
  return files.map((item) => fs.readFileSync(path.join(MODULE_DIR, String(item)), "utf8")).join("\n");
}

test("Puerta a puerta route, nav, watchlist suggestion, and API contract are wired", () => {
  assert.match(fs.readFileSync(PAGE, "utf8"), /DoorToDoorPanel/);
  assert.match(fs.readFileSync(NAV, "utf8"), /\/puerta-a-puerta/);
  assert.match(fs.readFileSync(WATCH_DETAIL, "utf8"), /DoorToDoorWatchlistSuggestion/);
  const apiSource = fs.readFileSync(API, "utf8");
  assert.match(apiSource, /\/door-to-door\/search/);
  assert.match(apiSource, /\/door-to-door\/suggestions/);
  assert.match(apiSource, /\/door-to-door\/saved-location/);
  assert.match(apiSource, /\/door-to-door\/history/);
  assert.match(apiSource, /\/door-to-door\/providers\/status/);
});

test("DoorToDoorPanel includes no-coverage-real handling, provider status and watchId preselect", () => {
  const source = fs.readFileSync(PANEL, "utf8");
  assert.match(source, /watchId/);
  assert.match(source, /fetchDoorToDoorProviderStatus/);
  assert.match(source, /NO_REAL_PROVIDER_COVERAGE/);
  assert.match(source, /noRealCoverageTitle/);
  assert.match(source, /providersStatus/);
  assert.match(source, /noActiveProviders/);
  assert.match(source, /coverageActionsDetail/);
  assert.match(source, /d2d-filters-collapse/);
  assert.match(source, /open=\{!isMobile \|\| showAdvancedFilters\}/);
});

test("Door-to-door option, radar, filters, and timeline render mock and flight-estimated cues", () => {
  const html = renderToStaticMarkup(
    <>
      <DoorToDoorFilters preferences={preferences} onChange={() => undefined} />
      <DoorToDoorOptionCard option={mockOption} selected={true} chosen={true} onSelect={() => undefined} onChoose={() => undefined} />
      <DoorToDoorRouteVisual option={mockOption} flight={flight} />
      <DoorToDoorTimeline option={mockOption} flight={flight} />
    </>,
  );
  assert.match(html, /Precio máximo del grupo/);
  assert.match(html, /Datos estimados/);
  assert.match(html, /Plan elegido/);
  assert.match(html, /Horario estimado/);
});

test("Door-to-door deeplink option renders open-provider CTA and handles null price", () => {
  const html = renderToStaticMarkup(<DoorToDoorOptionCard option={deeplinkOption} selected={false} chosen={false} onSelect={() => undefined} onChoose={() => undefined} />);
  assert.match(html, /sin precio confirmado/);
  assert.match(html, /Abrir proveedor/);
  assert.match(html, /Comparación limitada/);
  assert.match(html, /https:\/\/www\.blablacar\.es\/search/);
  assert.doesNotMatch(html, /Recomendada/);
  assert.doesNotMatch(html, /is-recommended/);
});

test("Door-to-door api option renders real duration and keeps price unconfirmed", () => {
  const html = renderToStaticMarkup(<DoorToDoorOptionCard option={apiRouteOption} selected={false} chosen={false} onSelect={() => undefined} onChoose={() => undefined} />);
  assert.match(html, /duración real/);
  assert.match(html, /sin precio confirmado/);
  assert.doesNotMatch(html, /desde \\d+/);
});

test("Door-to-door error and no coverage copy are i18n backed", () => {
  const html = renderToStaticMarkup(<DoorToDoorErrorState message="" onRetry={() => undefined} />);
  const i18nSource = fs.readFileSync(D2D_I18N, "utf8");
  assert.match(html, /No hemos podido completar todas las fuentes/);
  assert.match(i18nSource, /noCoverageBody/);
  assert.match(i18nSource, /noRealCoverageTitle/);
  assert.match(i18nSource, /Datos estimados/);
  assert.match(i18nSource, /Abrir proveedor/);
});

test("Door-to-door module has no mojibake markers", () => {
  const source = `${readAllDoorToDoorSource()}\n${fs.readFileSync(D2D_I18N, "utf8")}`;
  assert.doesNotMatch(source, new RegExp("[\\u00c3\\u00c2\\ufffd]|\\u00e2"));
});

test("Door-to-door styles include responsive radar and mobile decision layout hooks", () => {
  const source = fs.readFileSync(STYLES, "utf8");
  assert.match(source, /d2d-route-visual/);
  assert.match(source, /d2d-decision-grid/);
  assert.match(source, /d2d-option-compact-grid/);
  assert.match(source, /max-width: 680px/);
  assert.match(source, /prefers-reduced-motion/);
});
