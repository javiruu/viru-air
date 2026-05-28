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
  status: "estimate_only",
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
  source_types: ["estimate"],
  sources: [{ provider: "mock_multimodal", source_provider: "mock_multimodal", source_type: "estimate", confidence: "estimated", checked_at: "2026-05-20T10:00:00+02:00" }],
  is_recommended: true,
  is_extended: false,
  legs: [
    { type: "ground", mode: "bus", from: "Almería", to: "Aeropuerto de Málaga AGP", departure_at: "2026-06-14T08:10:00+02:00", arrival_at: "2026-06-14T12:00:00+02:00", duration_minutes: 230, price_min: 18, price_max: 28, provider: "mock_multimodal", source_type: "estimate", confidence: "estimated" },
    { type: "flight", mode: "flight", from: "AGP", to: "TSF", departure_at: "2026-06-14T14:20:00+02:00", arrival_at: "2026-06-14T16:55:00+02:00", duration_minutes: 155, provider: "flight_watch", source_type: "estimate", confidence: "estimated" },
    { type: "ground", mode: "shuttle", from: "Treviso Airport TSF", to: "Treviso centro", departure_at: "2026-06-14T17:30:00+02:00", arrival_at: "2026-06-14T18:10:00+02:00", duration_minutes: 40, price_min: 12, price_max: 20, provider: "mock_multimodal", source_type: "estimate", confidence: "estimated" },
  ],
};

const deeplinkOption: DoorToDoorOption = {
  id: "option_blablacar_deeplink",
  label: "Ruta con BlaBlaCar",
  description: "Enlace directo para tramo terrestre de salida. Precio final en proveedor.",
  status: "real_deeplink",
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

const deeplinkWithApiDurationOption: DoorToDoorOption = {
  ...deeplinkOption,
  id: "option_blablacar_deeplink_with_api",
  sources: [
    ...deeplinkOption.sources,
    {
      provider: "google_routes",
      source_provider: "google_routes",
      source_type: "api",
      confidence: "live",
      checked_at: "2026-05-20T10:00:00+02:00",
    },
  ],
};

const apiRouteOption: DoorToDoorOption = {
  id: "option_google_routes",
  label: "Duración real de ruta terrestre",
  description: "Duración y distancia calculadas con proveedor de rutas.",
  status: "real_result",
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
  assert.match(source, /noCoverageTitle/);
  assert.match(source, /providersStatus/);
  assert.match(source, /d2d-filters-collapse/);
  assert.match(source, /open=\{!isMobile \|\| showAdvancedFilters\}/);
  const originIndex = source.indexOf("id=\"d2d-origin\"");
  const watchIndex = source.indexOf("id=\"d2d-watch\"");
  const finalIndex = source.indexOf("id=\"d2d-final\"");
  assert.ok(originIndex > -1 && watchIndex > -1 && finalIndex > -1);
  assert.ok(originIndex < watchIndex);
  assert.ok(watchIndex < finalIndex);
  assert.match(source, /option_blablacar_deeplink/);
  assert.match(source, /deep_link/);
  assert.match(source, /comparatorTitle/);
  assert.match(source, /recommendedReasons/);
  assert.match(source, /quickBadgesByOption/);
  assert.match(source, /filterSavedPlacesForWatch/);
  assert.match(source, /d2d-map-hub/);
  assert.match(source, /viru_d2d_saved_places_v1/);
  assert.match(source, /addSavedPlace/);
  assert.match(source, /d2d-saved-places-manager/);
  assert.match(source, /doorToDoor\.mapHub\.state\.\$\{capability\.state\}/);
  assert.match(source, /warnings\.some\(\(warning\) => warning\.code === "NO_COVERAGE"\)/);
});

test("DoorToDoorPanel includes vertical timeline, trust modal trigger, and collapsible history", () => {
  const source = fs.readFileSync(PANEL, "utf8");
  assert.match(source, /d2d-segment-timeline/);
  assert.match(source, /status-pill state-info/);
  assert.match(source, /openActionsNodeId/);
  assert.match(source, /d2d-actions-toggle/);
  assert.match(source, /moreActions/);
  assert.match(source, /trustModalTrigger/);
  assert.match(source, /aria-haspopup="dialog"/);
  assert.match(source, /d2d-trust-modal/);
  assert.match(source, /showHistoryAction/);
  assert.match(source, /hideHistoryAction/);
  assert.match(source, /aria-expanded=\{showHistory\}/);
  assert.match(source, /mapCapabilitiesBySection/);
});

test("door-to-door i18n includes map hub copy in es and en", () => {
  const source = fs.readFileSync(D2D_I18N, "utf8");
  assert.match(source, /mapHub:\s*\{/);
  assert.match(source, /Capas del mapa/);
  assert.match(source, /Map layers/);
  assert.match(source, /state:\s*\{\s*available:/);
  assert.match(source, /savedPlaces:\s*\{/);
  assert.match(source, /listboxAria/);
});

test("DoorToDoorPanel guards keyboard navigation when autocomplete has no suggestions", () => {
  const source = fs.readFileSync(PANEL, "utf8");
  assert.match(source, /if \(suggestions\.length === 0\)/);
  assert.match(source, /event\.key === "ArrowDown" \|\| event\.key === "ArrowUp" \|\| event\.key === "Enter"/);
  assert.match(source, /event\.preventDefault\(\)/);
});

test("DoorToDoorPanel clears stale geo metadata on manual input and localizes listbox aria", () => {
  const source = fs.readFileSync(PANEL, "utf8");
  assert.match(source, /lat:\s*null/);
  assert.match(source, /lng:\s*null/);
  assert.match(source, /place_id:\s*null/);
  assert.match(source, /doorToDoor\.autocomplete\.listboxAria/);
});

test("DoorToDoorPanel guards stale requests, invalid submits, and duplicate saved places", () => {
  const source = fs.readFileSync(PANEL, "utf8");
  assert.match(source, /requestIdRef/);
  assert.match(source, /historyRequestIdRef/);
  assert.match(source, /resolveActiveOption/);
  assert.match(source, /chosenFromServer/);
  assert.match(source, /recommendedFromServer/);
  assert.match(source, /requestId !== requestIdRef\.current/);
  assert.match(source, /requestId !== historyRequestIdRef\.current/);
  assert.match(source, /normalizeLabel\(origin\.label\)/);
  assert.match(source, /normalizeLabel\(finalDestination\.label\)/);
  assert.match(source, /finalDestination\.type !== "airport_only" && normalizedOrigin === normalizedDestination/);
  assert.match(source, /status === "loading"/);
  assert.match(source, /duplicate = savedPlaces\.some/);
  assert.match(source, /await refreshHistory\(\)/);
  assert.match(source, /setResponse\(null\)/);
  assert.match(source, /setStatus\("empty"\)/);
});

test("Door-to-door suggestions support abortable requests", () => {
  const panelSource = fs.readFileSync(PANEL, "utf8");
  const apiSource = fs.readFileSync(API, "utf8");
  assert.match(panelSource, /new AbortController\(\)/);
  assert.match(panelSource, /controller\.abort\(\)/);
  assert.match(panelSource, /error\.name === "AbortError"/);
  assert.match(apiSource, /signal\?: AbortSignal/);
  assert.match(apiSource, /\/door-to-door\/suggestions\?\$\{params\.toString\(\)\}/);
  assert.match(apiSource, /\{\s*signal\s*\}/);
});

test("Door-to-door option, radar, filters, and timeline render mock and flight-estimated cues", () => {
  const html = renderToStaticMarkup(
    <>
      <DoorToDoorFilters preferences={preferences} onChange={() => undefined} />
      <DoorToDoorOptionCard
        option={mockOption}
        chosen={true}
        reasons={[{ kind: "price", label: "price" }, { kind: "risk", label: "risk" }]}
        quickBadges={[{ kind: "fastest", label: "fastest" }]}
        trustInline={true}
        onChoose={() => undefined}
      />
      <DoorToDoorRouteVisual option={mockOption} flight={flight} />
      <DoorToDoorTimeline option={mockOption} flight={flight} />
    </>,
  );
  assert.match(html, /Margen de conexión/);
  assert.match(html, /Límite de precio/);
  assert.match(html, /Estimación/);
  assert.match(html, /Horario estimado/);
  assert.match(html, /role="switch"/);
  assert.match(html, /Por qué esta ruta/);
  assert.match(html, /Más rápida/);
  assert.match(html, /Confirma precio y disponibilidad fuera de Viru/);
});

test("Door-to-door deeplink option renders open-provider CTA and handles null price", () => {
  const html = renderToStaticMarkup(<DoorToDoorOptionCard option={deeplinkOption} chosen={false} onChoose={() => undefined} />);
  assert.match(html, /precio/);
  assert.match(html, /Abrir proveedor/);
  assert.match(html, /se confirma fuera de Viru|sin precio confirmado/i);
  assert.match(html, /8h30/);
  assert.match(html, /https:\/\/www\.blablacar\.es\/search/);
  assert.doesNotMatch(html, /Recomendada/);
  assert.doesNotMatch(html, /is-recommended/);
});

test("Door-to-door api option renders real duration and keeps price unconfirmed", () => {
  const html = renderToStaticMarkup(<DoorToDoorOptionCard option={apiRouteOption} chosen={false} onChoose={() => undefined} />);
  assert.match(html, /duración real/);
  assert.match(html, /sin precio confirmado/);
  assert.doesNotMatch(html, /desde \\d+/);
});

test("Door-to-door deeplink option with Google Routes enrichment shows real-duration badge", () => {
  const html = renderToStaticMarkup(<DoorToDoorOptionCard option={deeplinkWithApiDurationOption} chosen={false} onChoose={() => undefined} />);
  assert.match(html, /duración real/);
  assert.match(html, /8h30/);
});

test("Door-to-door i18n includes provider-specific CTAs and source disclosure", () => {
  const i18nSource = fs.readFileSync(D2D_I18N, "utf8");
  assert.match(i18nSource, /openBlaBlaCar/);
  assert.match(i18nSource, /openGoOpti/);
  assert.match(i18nSource, /Abrir BlaBlaCar/);
  assert.match(i18nSource, /Abrir GoOpti/);
  assert.match(i18nSource, /Open BlaBlaCar/);
  assert.match(i18nSource, /Open GoOpti/);
  assert.match(i18nSource, /noCoverageBody/);
  assert.match(i18nSource, /noRealCoverageTitle/);
  assert.match(i18nSource, /Datos estimados/);
  assert.match(i18nSource, /showHistoryAction/);
  assert.match(i18nSource, /trustModalTitle/);
  assert.match(i18nSource, /openMapsShort/);
  assert.match(i18nSource, /moreActions/);
  assert.match(i18nSource, /blablacarAlwaysVisibleHint/);
});

test("Door-to-door module has no mojibake markers", () => {
  const source = `${readAllDoorToDoorSource()}\n${fs.readFileSync(D2D_I18N, "utf8")}`;
  assert.doesNotMatch(source, new RegExp("[\\u00c3\\u00c2\\ufffd]|\\u00e2"));
});

test("Door-to-door styles include responsive radar and mobile decision layout hooks", () => {
  const source = fs.readFileSync(STYLES, "utf8");
  assert.match(source, /d2d-route-visual/);
  assert.match(source, /d2d-decision-grid/);
  assert.match(source, /d2d-segment-timeline/);
  assert.match(source, /d2d-actions-toggle/);
  assert.match(source, /d2d-row-actions\.is-open/);
  assert.match(source, /d2d-trust-modal/);
  assert.match(source, /d2d-option-compact-grid/);
  assert.match(source, /d2d-form-essentials > \.btn-primary/);
  assert.match(source, /max-width: 680px/);
  assert.match(source, /prefers-reduced-motion/);
});

test("DoorToDoorPanel route-stack supports provider fallback actions and partial coverage notices", () => {
  const source = fs.readFileSync(PANEL, "utf8");
  assert.match(source, /openProviderAction/);
  assert.match(source, /partialCoverageBody/);
  assert.match(source, /hasNoRealCoverage/);
  assert.match(source, /hasPartialCoverage/);
  assert.match(source, /outboundLeg\?\.booking_url/);
  assert.match(source, /inboundLeg\?\.booking_url/);
  assert.match(source, /segmentLinks\.blablacarUrl && !outboundBooking/);
  assert.match(source, /segmentLinks\.gooptiUrl && !inboundBooking/);
});

const gtfsOption: DoorToDoorOption = {
  id: "option_gtfs_transit",
  label: "Transporte público (horario real)",
  description: "Horario según feed público GTFS.",
  status: "real_result",
  total_price_min: null,
  total_price_max: null,
  price_per_person_min: null,
  price_per_person_max: null,
  currency: "EUR",
  total_duration_minutes: 320,
  risk_level: "medium",
  score: 68,
  transfer_count: 1,
  airport_buffer_minutes: 130,
  confidence: "cached",
  source_types: ["open_data"],
  sources: [
    {
      provider: "gtfs_transit",
      source_provider: "ctan_andalucia",
      source_type: "open_data",
      confidence: "cached",
      checked_at: "2026-05-20T10:00:00+02:00",
      booking_url: null,
    },
  ],
  is_recommended: false,
  is_extended: false,
  legs: [
    {
      type: "ground",
      mode: "bus",
      from: "Almería",
      to: "Aeropuerto de Málaga AGP",
      departure_at: "2026-06-14T07:30:00+02:00",
      arrival_at: "2026-06-14T11:00:00+02:00",
      duration_minutes: 210,
      provider: "gtfs_transit",
      source_type: "open_data",
      confidence: "cached",
    },
    {
      type: "flight",
      mode: "flight",
      from: "AGP",
      to: "TSF",
      duration_minutes: 155,
      provider: "flight_watch",
      source_type: "api",
      confidence: "estimated",
    },
  ],
};

test("Door-to-door GTFS transit option renders public schedule and handles null price", () => {
  const html = renderToStaticMarkup(<DoorToDoorOptionCard option={gtfsOption} chosen={false} onChoose={() => undefined} />);
  assert.match(html, /sin precio confirmado/);
  assert.match(html, /Datos abiertos/);
  assert.match(html, /Transporte público/);
  assert.doesNotMatch(html, /Abrir proveedor/);
});

test("Door-to-door i18n includes GTFS open data strings", () => {
  const i18nSource = fs.readFileSync(D2D_I18N, "utf8");
  assert.match(i18nSource, /openData/);
  assert.match(i18nSource, /Datos abiertos/);
  assert.match(i18nSource, /Open data/);
  assert.match(i18nSource, /openDataSchedule/);
  assert.match(i18nSource, /horario público/);
  assert.match(i18nSource, /public schedule/);
  assert.match(i18nSource, /openDataHint/);
  assert.match(i18nSource, /GTFS\/Open Data/);
});
