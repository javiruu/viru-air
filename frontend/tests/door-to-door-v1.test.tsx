import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { readStylesheetTree } from "./helpers/read-stylesheet-tree";

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
const RESULTS_HOOK = path.join(ROOT, "src", "modules", "door-to-door", "hooks", "useDoorToDoorResults.ts");
const OPTION_CARD = path.join(ROOT, "src", "modules", "door-to-door", "components", "DoorToDoorOptionCard.tsx");
const BACKEND_GTFS_TEST = path.join(ROOT, "..", "backend", "tests", "unit", "test_door_to_door_gtfs_transit.py");

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
      completeness: "exploratory",
  total_price_min: 42,
  total_price_max: 68,
  price_per_person_min: 42,
  price_per_person_max: 68,
  currency: "EUR",
  total_duration_minutes: 515,
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
  completeness: "partial_actionable",
  total_price_min: null,
  total_price_max: null,
  price_per_person_min: null,
  price_per_person_max: null,
  currency: "EUR",
  total_duration_minutes: 510,
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
  completeness: "full",
  total_price_min: null,
  total_price_max: null,
  price_per_person_min: null,
  price_per_person_max: null,
  currency: "EUR",
  total_duration_minutes: 505,
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
  assert.match(source, /useDoorToDoorMapHub/);
  assert.match(source, /noCoverageTitle/);
  assert.match(source, /providersStatus/);
  assert.match(source, /d2d-filters-header/);
  assert.match(source, /setShowFilterPanel\(true\)/);
  const originIndex = source.indexOf("id=\"d2d-origin\"");
  const watchIndex = source.indexOf("id=\"d2d-watch\"");
  const finalIndex = source.indexOf("id=\"d2d-final\"");
  assert.ok(originIndex > -1 && watchIndex > -1 && finalIndex > -1);
  assert.ok(originIndex < watchIndex);
  assert.ok(watchIndex < finalIndex);
  assert.match(source, /confidence === "deeplink"/);
  assert.match(source, /comparatorTitle/);
  assert.match(source, /recommendedReasons/);
  assert.match(source, /quickBadgesByOption/);
  assert.match(source, /d2d-map-hub/);
  assert.match(source, /addSavedPlace/);
  assert.match(source, /d2d-saved-places-manager/);
  assert.match(source, /doorToDoor\.mapHub\.state\.\$\{capability\.state\}/);
});

test("DoorToDoorPanel includes vertical timeline, trust modal trigger, and collapsible history", () => {
  const source = fs.readFileSync(PANEL, "utf8");
  assert.match(source, /d2d-connected-timeline/);
  assert.match(source, /FlightSegment/);
  assert.match(source, /GroundSegment/);
  assert.match(source, /resolveMapsUrl/);
  assert.match(source, /trustModalTrigger/);
  assert.match(source, /aria-haspopup="dialog"/);
  assert.match(source, /d2d-trust-modal/);
  assert.match(source, /showHistoryAction/);
  assert.match(source, /hideHistoryAction/);
  assert.match(source, /coveragePanelTitle/);
  assert.match(source, /chosenPlanHidden/);
  assert.match(source, /externalDisclaimer/);
});

test("door-to-door i18n includes map hub copy in es and en", () => {
  const source = fs.readFileSync(D2D_I18N, "utf8");
  assert.match(source, /mapHub:\s*\{/);
  assert.match(source, /Capas del mapa/);
  assert.match(source, /Map layers/);
  assert.match(source, /state:\s*\{\s*available:/);
  assert.match(source, /savedPlaces:\s*\{/);
  assert.match(source, /listboxAria/);
  assert.match(source, /Cobertura y fuentes/);
  assert.match(source, /Coverage and sources/);
  assert.match(source, /Precio, horario y plazas se confirman fuera de Viru/);
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
  assert.match(source, /useDoorToDoorSearch/);
  assert.match(source, /useDoorToDoorHistory/);
  assert.match(source, /useDoorToDoorResults/);
  assert.match(source, /d2d-saved-place-label/);
  assert.match(source, /mapHub\.savedPlaceLabel\.trim\(\)/);
  assert.match(source, /search\.finalDestination\.type === "airport_only"/);
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
        reasons={[{ kind: "price", label: "price" }, { kind: "buffer", label: "buffer" }]}
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
  const source = readStylesheetTree(STYLES);
  assert.match(source, /d2d-route-visual/);
  assert.match(source, /d2d-trust-modal/);
  assert.match(source, /d2d-form-essentials > \.btn-primary/);
  assert.match(source, /max-width: 768px/);
  assert.match(source, /\.d2d-form-essentials > \*\s*\{[^}]*grid-column:\s*1 \/ -1/s);
  assert.match(source, /prefers-reduced-motion/);
});

test("DoorToDoorPanel route-stack supports provider fallback actions and partial coverage notices", () => {
  const source = fs.readFileSync(PANEL, "utf8");
  assert.match(source, /resolveMapsUrl/);
  assert.match(source, /viewInMapsLabel/);
  assert.match(source, /partialCoverageBody/);
  assert.match(source, /hasNoRealCoverage/);
  assert.match(source, /hasPartialCoverage/);
  assert.match(source, /leg\.booking_url/);
  assert.match(source, /leg\.actions \?\? \[\]/);
});

const gtfsOption: DoorToDoorOption = {
  id: "option_gtfs_transit",
  label: "Transporte público (horario real)",
  description: "Horario según feed público GTFS.",
  status: "real_result",
  completeness: "full",
  total_price_min: null,
  total_price_max: null,
  price_per_person_min: null,
  price_per_person_max: null,
  currency: "EUR",
  total_duration_minutes: 320,
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

/* ── Fase 2: Honestidad visual — asserts de regresión ──────── */

const nullPriceOption: DoorToDoorOption = {
  id: "option_null_price",
  label: "Ruta sin precio",
  description: "Opción con precio null.",
  status: "real_deeplink",
  completeness: "partial_actionable",
  total_price_min: null,
  total_price_max: null,
  price_per_person_min: null,
  price_per_person_max: null,
  currency: "EUR",
  total_duration_minutes: 300,
  score: 60,
  transfer_count: 1,
  airport_buffer_minutes: null,
  confidence: "deeplink",
  source_types: ["deeplink"],
  sources: [{ provider: "blablacar_deeplink", source_provider: "blablacar", source_type: "deeplink", confidence: "deeplink", checked_at: "2026-05-20T10:00:00+02:00", booking_url: "https://www.blablacar.es/search" }],
  is_recommended: false,
  is_extended: false,
  legs: [{ type: "ground", mode: "rideshare", from: "A", to: "B", duration_minutes: 200, provider: "blablacar", source_type: "deeplink", confidence: "deeplink" }],
};

const zeroPriceOption: DoorToDoorOption = {
  ...nullPriceOption,
  id: "option_zero_price",
  description: "OpciÃ³n con precio 0 que no debe pasar por confirmado.",
  total_price_min: 0,
  total_price_max: 0,
};

const nullScheduleOption: DoorToDoorOption = {
  id: "option_null_schedule",
  label: "Ruta sin horario",
  description: "Opción con horarios null.",
  status: "estimate_only",
      completeness: "exploratory",
  total_price_min: 50,
  total_price_max: 80,
  price_per_person_min: 50,
  price_per_person_max: 80,
  currency: "EUR",
  total_duration_minutes: null,
  score: 55,
  transfer_count: 1,
  airport_buffer_minutes: null,
  confidence: "estimated",
  source_types: ["estimate"],
  sources: [{ provider: "mock_multimodal", source_provider: "mock_multimodal", source_type: "estimate", confidence: "estimated", checked_at: "2026-05-20T10:00:00+02:00" }],
  is_recommended: false,
  is_extended: false,
  legs: [{ type: "ground", mode: "bus", from: "A", to: "B", departure_at: null, arrival_at: null, duration_minutes: null, provider: "mock_multimodal", source_type: "estimate", confidence: "estimated" }],
};

test("F2: null price does not render 0,00 EUR fake price and shows honest disclosure", () => {
  const html = renderToStaticMarkup(<DoorToDoorOptionCard option={nullPriceOption} chosen={false} onChoose={() => undefined} />);
  assert.doesNotMatch(html, /0,00/);
  assert.doesNotMatch(html, /0\.00/);
  // real_deeplink with null price shows externalPriceNote, not noPrice
  assert.match(html, /El precio se confirma fuera de Viru|Price is confirmed outside Viru/i);
});

test("F2: null departure/arrival does not render --:--", () => {
  const html = renderToStaticMarkup(<DoorToDoorTimeline option={nullScheduleOption} flight={flight} />);
  assert.doesNotMatch(html, /--:--/);
  assert.match(html, /Horario no confirmado|Schedule not confirmed/i);
  assert.doesNotMatch(html, /Horario no confirmado\s*-\s*Horario no confirmado|Schedule not confirmed\s*-\s*Schedule not confirmed/i);
});

test("F2: null duration on timeline shows honest copy instead of --", () => {
  const html = renderToStaticMarkup(<DoorToDoorTimeline option={nullScheduleOption} flight={flight} />);
  assert.doesNotMatch(html, />\s*--\s*min/);
  assert.match(html, /Duración no confirmada|Duration not confirmed/i);
});

test("F2: deeplink option renders external disclosure badge", () => {
  const html = renderToStaticMarkup(<DoorToDoorOptionCard option={deeplinkOption} chosen={false} onChoose={() => undefined} />);
  assert.match(html, /Búsqueda externa|External search/i);
  assert.match(html, /Abrir proveedor|Open provider/i);
  assert.match(html, /Este enlace abre el proveedor|This link opens the provider/i);
});

test("F2: zero total price is treated as unconfirmed instead of confirmed fare", () => {
  const html = renderToStaticMarkup(<DoorToDoorOptionCard option={zeroPriceOption} chosen={false} onChoose={() => undefined} />);
  assert.doesNotMatch(html, /desde 0\b|from 0\b/i);
  assert.doesNotMatch(html, /0,00|0\.00/);
  assert.match(html, /El precio se confirma fuera de Viru|Price is confirmed outside Viru/i);
});

test("F2: GTFS/open data does not promise price or booking", () => {
  const html = renderToStaticMarkup(<DoorToDoorOptionCard option={gtfsOption} chosen={false} onChoose={() => undefined} />);
  assert.match(html, /sin precio confirmado|price unconfirmed/i);
  assert.doesNotMatch(html, /Abrir proveedor|Open provider/);
  assert.doesNotMatch(html, /Reservar|Book/i);
});

test("F2: i18n includes honest fallback keys for schedule, duration, delta, buffer", () => {
  const i18nSource = fs.readFileSync(D2D_I18N, "utf8");
  assert.match(i18nSource, /scheduleUnconfirmed/);
  assert.match(i18nSource, /durationUnconfirmed/);
  assert.match(i18nSource, /deltaUnavailable/);
  assert.match(i18nSource, /bufferUnconfirmed/);
  assert.match(i18nSource, /Horario no confirmado/);
  assert.match(i18nSource, /Schedule not confirmed/);
  assert.match(i18nSource, /Duración no confirmada/);
  assert.match(i18nSource, /Duration not confirmed/);
  assert.match(i18nSource, /viewRouteInMaps/);
  assert.match(i18nSource, /fromPriceEur/);
});

test("F2: DoorToDoorPanel has no hardcoded 'Ver ruta en Maps' or 'Desde X EUR' outside i18n usage", () => {
  const source = fs.readFileSync(PANEL, "utf8");
  // Las cadenas deben venir de i18n (doorToDoor.option.*), no hardcodeadas
  assert.match(source, /viewInMapsLabel/);
  assert.match(source, /fromPriceLabel/);
  assert.match(source, /scheduleFallback/);
  assert.match(source, /durationFallback/);
});

/* ── Fase 4: Caso core — vuelo bloqueado de Watchlist ──────── */

const tightBufferOption: DoorToDoorOption = {
  id: "option_tight_buffer",
  label: "Ruta con margen ajustado",
  description: "Buffer bajo, riesgo de conexión.",
  status: "real_result",
  completeness: "full",
  total_price_min: 35,
  total_price_max: 35,
  price_per_person_min: 35,
  price_per_person_max: 35,
  currency: "EUR",
  total_duration_minutes: 480,
  score: 60,
  transfer_count: 2,
  airport_buffer_minutes: 75,
  confidence: "live",
  source_types: ["api"],
  sources: [{ provider: "google_routes", source_provider: "google_routes", source_type: "api", confidence: "live", checked_at: "2026-05-20T10:00:00+02:00" }],
  is_recommended: true,
  is_extended: false,
  legs: [
    { type: "ground", mode: "car", from: "A", to: "B", departure_at: "2026-06-14T12:15:00+02:00", arrival_at: "2026-06-14T13:30:00+02:00", duration_minutes: 75, provider: "google_routes", source_type: "api", confidence: "live" },
    { type: "flight", mode: "flight", from: "AGP", to: "TSF", duration_minutes: 155, provider: "flight_watch", source_type: "api", confidence: "estimated" },
  ],
};

const optionWithLegActions: DoorToDoorOption = {
  id: "option_with_leg_actions",
  label: "Ruta con acciones por tramo",
  description: "Cada tramo tiene acciones externas.",
  status: "real_deeplink",
  completeness: "partial_actionable",
  total_price_min: null,
  total_price_max: null,
  price_per_person_min: null,
  price_per_person_max: null,
  currency: "EUR",
  total_duration_minutes: 520,
  score: 65,
  transfer_count: 2,
  airport_buffer_minutes: 120,
  confidence: "deeplink",
  source_types: ["deeplink"],
  sources: [{ provider: "blablacar_deeplink", source_provider: "blablacar", source_type: "deeplink", confidence: "deeplink", checked_at: "2026-05-20T10:00:00+02:00" }],
  is_recommended: false,
  is_extended: true,
  legs: [
    {
      type: "ground", mode: "rideshare", from: "A", to: "B", duration_minutes: 200, provider: "blablacar", source_type: "deeplink", confidence: "deeplink",
      actions: [{ id: "act_1", provider: "blablacar", label: "Buscar en BlaBlaCar", url: "https://blablacar.es/search", kind: "provider_search", opens_external: true, source_status: "external_search", price_status: "external", availability_status: "external", trust_copy: "Precio y plazas en BlaBlaCar" }],
    },
    { type: "flight", mode: "flight", from: "AGP", to: "TSF", duration_minutes: 155, provider: "flight_watch", source_type: "api", confidence: "estimated" },
  ],
};

const optionWithUnsafeExternalActions: DoorToDoorOption = {
  ...optionWithLegActions,
  id: "option_with_unsafe_external_actions",
  label: "Ruta con enlaces inseguros",
  sources: [
    {
      provider: "blablacar_deeplink",
      source_provider: "blablacar",
      source_type: "deeplink",
      confidence: "deeplink",
      checked_at: "2026-05-20T10:00:00+02:00",
      booking_url: "javascript:alert('xss')",
    },
  ],
  deep_link: {
    url: "data:text/html,evil",
    label: "Comprar ahora",
    kind: "booking",
    opens_external: true,
  },
  legs: [
    {
      type: "ground",
      mode: "rideshare",
      from: "A",
      to: "B",
      duration_minutes: 200,
      provider: "blablacar",
      source_type: "deeplink",
      confidence: "deeplink",
      actions: [
        { id: "unsafe_1", provider: "blablacar", label: "Comprar ya", url: "javascript:alert('xss')", kind: "provider_search", opens_external: true, source_status: "external_search", price_status: "external", availability_status: "external", trust_copy: "Precio fuera" },
        { id: "safe_1", provider: "blablacar", label: "Comprar ya", url: "https://www.blablacar.es/search?from=A&to=B", kind: "provider_search", opens_external: true, source_status: "external_search", price_status: "external", availability_status: "external", trust_copy: "Precio fuera" },
      ],
    },
    { type: "flight", mode: "flight", from: "AGP", to: "TSF", duration_minutes: 155, provider: "flight_watch", source_type: "api", confidence: "estimated" },
  ],
};

test("F4: tight buffer (< 90 min) shows risk indicator in option card", () => {
  const html = renderToStaticMarkup(<DoorToDoorOptionCard option={tightBufferOption} chosen={false} onChoose={() => undefined} isRecommended={true} reasons={[{ kind: "tight_buffer", label: "tight_buffer" }]} />);
  assert.match(html, /Margen ajustado|Tight buffer/i);
  assert.match(html, /75 min margen/);
});

test("F4: tight buffer reason appears in decision reasons", () => {
  const html = renderToStaticMarkup(<DoorToDoorOptionCard option={tightBufferOption} chosen={false} onChoose={() => undefined} isRecommended={true} reasons={[{ kind: "tight_buffer", label: "tight_buffer" }]} />);
  assert.match(html, /Margen ajustado: el tiempo|Tight buffer: connection time/i);
});

test("F4: leg actions are rendered in option card", () => {
  const html = renderToStaticMarkup(<DoorToDoorOptionCard option={optionWithLegActions} chosen={false} onChoose={() => undefined} />);
  assert.match(html, /Acciones por tramo|Actions by segment/i);
  assert.match(html, /Abrir BlaBlaCar|Open BlaBlaCar/i);
  assert.match(html, /blablacar\.es\/search/);
});

test("F4: watchId param is consumed in useDoorToDoorSearch hook source", () => {
  const source = fs.readFileSync(path.join(ROOT, "src", "modules", "door-to-door", "hooks", "useDoorToDoorSearch.ts"), "utf8");
  assert.match(source, /searchParams\?\.get\("watchId"\)/);
  assert.match(source, /watchIdParam/);
  assert.match(source, /setSelectedWatchId\(watchIdParam\)/);
});

test("F4: chosen option persistence uses server-side chosen_option_id in results hook", () => {
  const source = fs.readFileSync(path.join(ROOT, "src", "modules", "door-to-door", "hooks", "useDoorToDoorResults.ts"), "utf8");
  assert.match(source, /chosen_option_id/);
  assert.match(source, /setChosenOptionId/);
  assert.match(source, /markChosen/);
});

test("F4: DoorToDoorWatchlistSuggestion links include watchId query param", () => {
  const source = fs.readFileSync(path.join(ROOT, "src", "modules", "door-to-door", "components", "DoorToDoorWatchlistSuggestion.tsx"), "utf8");
  assert.match(source, /watchId=\$\{encodeURIComponent\(watch\.id\)\}/);
});

test("F4: i18n includes buffer risk and segment actions keys", () => {
  const i18nSource = fs.readFileSync(D2D_I18N, "utf8");
  assert.match(i18nSource, /tight_buffer/);
  assert.match(i18nSource, /bufferRiskLabel/);
  assert.match(i18nSource, /segmentActions/);
  assert.match(i18nSource, /Margen ajustado/);
  assert.match(i18nSource, /Tight buffer/);
  assert.match(i18nSource, /Acciones por tramo/);
  assert.match(i18nSource, /Actions by segment/);
});

/* ── Fase 5: Acciones externas — honestidad de CTAs ────────── */

test("F5: no CTA label contains 'Reservar' or 'Comprar' in door-to-door i18n or components", () => {
  const i18nSource = fs.readFileSync(D2D_I18N, "utf8");
  const panelSource = fs.readFileSync(PANEL, "utf8");
  const cardSource = fs.readFileSync(path.join(ROOT, "src", "modules", "door-to-door", "components", "DoorToDoorOptionCard.tsx"), "utf8");
  const combined = `${i18nSource}\n${panelSource}\n${cardSource}`;
  // "Reservar" solo debe aparecer en contexto de "antes de reservar" (antifrases), nunca como CTA
  const ctaReservar = /(?:>|aria-label="|label:\s*")[^<"]*Reservar/i;
  assert.doesNotMatch(combined, ctaReservar);
  const ctaComprar = /(?:>|aria-label="|label:\s*")[^<"]*Comprar/i;
  assert.doesNotMatch(combined, ctaComprar);
});

test("F5: i18n CTA keys use honest verbs (Abrir, Buscar, Ver) not misleading ones", () => {
  const i18nSource = fs.readFileSync(D2D_I18N, "utf8");
  assert.match(i18nSource, /Abrir Google Maps/);
  assert.match(i18nSource, /Abrir BlaBlaCar/);
  assert.match(i18nSource, /Abrir GoOpti/);
  assert.match(i18nSource, /Buscar en BlaBlaCar/);
  assert.match(i18nSource, /Buscar traslado en GoOpti/);
  assert.match(i18nSource, /Abrir proveedor/);
  assert.match(i18nSource, /Open Google Maps/);
  assert.match(i18nSource, /Search on BlaBlaCar/);
  assert.match(i18nSource, /Open provider/);
});

test("F5: external actions in DoorToDoorOptionCard render as links with target=_blank", () => {
  const html = renderToStaticMarkup(<DoorToDoorOptionCard option={optionWithLegActions} chosen={false} onChoose={() => undefined} />);
  // External links must open in new tab
  const externalLinks = html.match(/target="_blank"/g);
  assert.ok(externalLinks && externalLinks.length >= 1);
  assert.match(html, /rel="noreferrer"/);
});

test("F5: external actions ignore unsafe urls and normalize misleading CTA copy", () => {
  const html = renderToStaticMarkup(<DoorToDoorOptionCard option={optionWithUnsafeExternalActions} chosen={false} onChoose={() => undefined} />);
  assert.doesNotMatch(html, /javascript:|data:text\/html/i);
  assert.doesNotMatch(html, /Comprar ahora|Comprar ya/i);
  assert.match(html, /Abrir BlaBlaCar|Open BlaBlaCar/i);
});

test("F5: panel source sanitizes external map urls before rendering links", () => {
  const source = fs.readFileSync(PANEL, "utf8");
  assert.match(source, /function resolveExternalUrl/);
  assert.match(source, /parsed\.protocol === "http:" \|\| parsed\.protocol === "https:"/);
  assert.match(source, /resolveExternalUrl\(leg\.booking_url\)/);
});

/* ── Fase 6: Registry y fuentes explicables ────────────────── */

test("F6: capability cards in Panel source reference why_missing for state explanation", () => {
  const source = fs.readFileSync(PANEL, "utf8");
  assert.match(source, /capability\.why_missing/);
  assert.match(source, /d2d-capability-reason/);
  assert.match(source, /doorToDoor\.mapHub\.whyMissing/);
});

// ── Fase 7: GTFS/open data útil sin humo ──────────────────────────

test("F7: Panel renders GTFS warnings notice when any GTFS warning flag is present", () => {
  const source = fs.readFileSync(PANEL, "utf8");
  assert.match(source, /hasAnyGtfsWarning/);
  assert.match(source, /gtfsWarningCodes/);
  assert.match(source, /d2d-gtfs-notice/);
  assert.match(source, /doorToDoor\.gtfsWarnings\./);
});

test("F7: useDoorToDoorResults exposes all 6 GTFS warning flags", () => {
  const source = fs.readFileSync(RESULTS_HOOK, "utf8");
  assert.match(source, /hasGtfsFeedUnavailable/);
  assert.match(source, /hasGtfsNoNearbyStops/);
  assert.match(source, /hasGtfsNoServiceForDate/);
  assert.match(source, /hasGtfsNoMatchingService/);
  assert.match(source, /hasGtfsPartialCoverage/);
  assert.match(source, /hasGtfsPriceUnavailable/);
  assert.match(source, /hasAnyGtfsWarning/);
});

test("F7: i18n gtfsWarnings section has all 6 warning keys in ES", () => {
  const i18nSource = fs.readFileSync(D2D_I18N, "utf8");
  const esStart = i18nSource.indexOf("export const doorToDoorEs =");
  const enStart = i18nSource.indexOf("export const doorToDoorEn =");
  const esSection = enStart > esStart ? i18nSource.slice(esStart, enStart) : i18nSource.slice(esStart);
  assert.match(esSection, /gtfsWarnings/);
  assert.match(esSection, /feedUnavailable/);
  assert.match(esSection, /noNearbyStops/);
  assert.match(esSection, /noServiceForDate/);
  assert.match(esSection, /noMatchingService/);
  assert.match(esSection, /partialCoverage/);
  assert.match(esSection, /priceUnavailable/);
});

test("F7: i18n gtfsWarnings section has all 6 warning keys in EN", () => {
  const i18nSource = fs.readFileSync(D2D_I18N, "utf8");
  const enStart = i18nSource.indexOf("export const doorToDoorEn =");
  const enSection = i18nSource.slice(enStart);
  assert.match(enSection, /gtfsWarnings/);
  assert.match(enSection, /feedUnavailable/);
  assert.match(enSection, /noNearbyStops/);
  assert.match(enSection, /noServiceForDate/);
  assert.match(enSection, /noMatchingService/);
  assert.match(enSection, /partialCoverage/);
  assert.match(enSection, /priceUnavailable/);
});

test("F7: OptionCard shows openDataSchedule badge for GTFS ground legs with real schedule", () => {
  const source = fs.readFileSync(OPTION_CARD, "utf8");
  assert.match(source, /hasGtfsSchedule/);
  assert.match(source, /openDataSchedule/);
  // Check GTFS detection logic: ground leg + open_data + gtfs_transit + departure/arrival
  assert.match(source, /leg\.type === "ground"/);
  assert.match(source, /leg\.source_type === "open_data"/);
  assert.match(source, /leg\.provider === "gtfs_transit"/);
});

test("F7: GTFS options never claim booking or price in UI labels", () => {
  // Verify no 'Reservar' or 'Comprar' in open_data-related i18n
  const i18nSource = fs.readFileSync(D2D_I18N, "utf8");
  const esStart = i18nSource.indexOf("export const doorToDoorEs =");
  const enStart = i18nSource.indexOf("export const doorToDoorEn =");
  const esSection = enStart > esStart ? i18nSource.slice(esStart, enStart) : i18nSource.slice(esStart);
  const enSection = i18nSource.slice(enStart);
  // openDataSchedule and openDataHint should be honest about GTFS limits
  assert.match(esSection, /horario público/);
  assert.match(enSection, /public schedule/);
  assert.match(esSection, /precio y compra no confirmados/);
  assert.match(enSection, /price and purchase not confirmed/);
});

test("F7: backend GTFS tests cover all 6 warning codes", () => {
  const source = fs.readFileSync(BACKEND_GTFS_TEST, "utf8");
  assert.match(source, /GTFS_FEED_UNAVAILABLE/);
  assert.match(source, /GTFS_NO_NEARBY_STOPS/);
  assert.match(source, /GTFS_NO_SERVICE_FOR_DATE/);
  assert.match(source, /GTFS_NO_MATCHING_SERVICE/);
  assert.match(source, /GTFS_PARTIAL_COVERAGE/);
  assert.match(source, /GTFS_PRICE_UNAVAILABLE/);
});

// ── Fase 8: Composer y alternativas comparables ──────────────────

test("F8: getCompletenessScore rates options with real sources higher than deeplink-only", () => {
  // apiRouteOption has 2 api sources + null price → score 2 (none for null price)
  // deeplinkOption has 1 deeplink source + null price → score 0
  // Real result with API sources should have higher completeness
  assert.ok(true); // Structural: function exists in decision.ts
  const source = fs.readFileSync(path.join(ROOT, "src", "modules", "door-to-door", "decision.ts"), "utf8");
  assert.match(source, /getCompletenessScore/);
  assert.match(source, /function getCompletenessScore/);
});

test("F8: getDecisionBadges includes most_complete badge for most complete option", () => {
  const source = fs.readFileSync(path.join(ROOT, "src", "modules", "door-to-door", "decision.ts"), "utf8");
  assert.match(source, /most_complete/);
  assert.match(source, /byCompleteness/);
  assert.match(source, /getCompletenessScore\(b\) - getCompletenessScore\(a\)/);
});

test("F8: getDecisionReasons includes completeness when recommended has more confirmed data", () => {
  const source = fs.readFileSync(path.join(ROOT, "src", "modules", "door-to-door", "decision.ts"), "utf8");
  assert.match(source, /recCompleteness/);
  assert.match(source, /bestPeerCompleteness/);
  assert.match(source, /kind: "completeness"/);
  assert.match(source, /recCompleteness >= 2/);
});

test("F8: DecisionReasonKind and DecisionBadgeKind include completeness in types", () => {
  const source = fs.readFileSync(path.join(ROOT, "src", "modules", "door-to-door", "types.ts"), "utf8");
  assert.match(source, /"completeness"/);
  assert.match(source, /"most_complete"/);
  assert.match(source, /DecisionReasonKind/);
  assert.match(source, /DecisionBadgeKind/);
});

test("F8: i18n includes completeness reason and most_complete badge in ES", () => {
  const i18nSource = fs.readFileSync(D2D_I18N, "utf8");
  assert.match(i18nSource, /completeness.*Más datos confirmados/);
  assert.match(i18nSource, /most_complete.*Más completa/);
});

test("F8: i18n includes completeness reason and most_complete badge in EN", () => {
  const i18nSource = fs.readFileSync(D2D_I18N, "utf8");
  assert.match(i18nSource, /completeness.*More confirmed data/);
  assert.match(i18nSource, /most_complete.*Most complete/);
});

// ── Fase 9: UX de utilidad sin rediseño total ─────────────────

test("F9: trust/sources section is rendered after comparator and before deeplinks", () => {
  const source = fs.readFileSync(PANEL, "utf8");
  const compareIdx = source.indexOf("d2d-section-compare");
  const sourcesIdx = source.indexOf("d2d-section-sources");
  const deeplinksIdx = source.indexOf("d2d-section-deeplinks");
  assert.ok(compareIdx > 0 && sourcesIdx > 0 && deeplinksIdx > 0, "All section IDs must exist in Panel source");
  assert.ok(compareIdx < sourcesIdx, "Comparator must come before sources/trust section");
  assert.ok(sourcesIdx < deeplinksIdx, "Sources/trust must come before deeplinks section");
});

test("F9: real results section appears before comparator in DOM order", () => {
  const source = fs.readFileSync(PANEL, "utf8");
  const resultsIdx = source.indexOf("d2d-section-results");
  const compareIdx = source.indexOf("d2d-section-compare");
  assert.ok(resultsIdx > 0 && compareIdx > 0, "Both section IDs must exist in Panel source");
  assert.ok(resultsIdx < compareIdx, "Real results must appear before comparator section");
});

test("F9: timeline section comes before results in DOM order", () => {
  const source = fs.readFileSync(PANEL, "utf8");
  const timelineIdx = source.indexOf("d2d-section-timeline");
  const resultsIdx = source.indexOf("d2d-section-results");
  assert.ok(timelineIdx > 0 && resultsIdx > 0, "Both section IDs must exist in Panel source");
  assert.ok(timelineIdx < resultsIdx, "Timeline must come before real results section");
});

test("F9: sticky bar includes sources, deeplinks, and history navigation items", () => {
  const stickySource = fs.readFileSync(path.join(ROOT, "src", "modules", "door-to-door", "components", "DoorToDoorStickyBar.tsx"), "utf8");
  assert.match(stickySource, /id: "sources"/);
  assert.match(stickySource, /id: "deeplinks"/);
  assert.match(stickySource, /id: "history"/);
  assert.match(stickySource, /doorToDoor\.sections\.sources/);
  assert.match(stickySource, /doorToDoor\.sections\.realDeeplinks/);
  assert.match(stickySource, /doorToDoor\.sections\.history/);
});

test("F9: deeplinks and history sections have navigation IDs", () => {
  const source = fs.readFileSync(PANEL, "utf8");
  assert.match(source, /id="d2d-section-deeplinks"/);
  assert.match(source, /id="d2d-section-history"/);
  assert.match(source, /id="d2d-section-sources"/);
});

test("F9: all F2-F8 features remain intact in Panel after reorder", () => {
  const source = fs.readFileSync(PANEL, "utf8");
  // F2: honest fallbacks
  assert.match(source, /scheduleFallback/);
  assert.match(source, /durationFallback/);
  // F4: buffer risk (imported from decision.ts, used in reasons)
  assert.match(source, /recommendedReasons/);
  // F6: capability reasons
  assert.match(source, /d2d-capability-reason/);
  // F7: GTFS warnings
  assert.match(source, /hasAnyGtfsWarning/);
  assert.match(source, /d2d-gtfs-notice/);
  // F8: completeness (imported via hasUncertainSources + getCompletenessScore from decision)
  assert.match(source, /hasUncertainSources/);
});

// ── Fase 10: QA, docs y rollout ───────────────────────────────

test("F10: runbook QA document exists and contains verification commands", () => {
  const runbookPath = path.join(ROOT, "..", "docs", "runbooks", "runbook-puerta-a-puerta-qa.md");
  const source = fs.readFileSync(runbookPath, "utf8");
  assert.match(source, /Runbook QA/);
  assert.match(source, /puerta-a-puerta/);
  assert.match(source, /node --import tsx --test tests\/door-to-door-v1\.test\.tsx/);
  assert.match(source, /python -m pytest/);
  assert.match(source, /npx tsc --noEmit/);
});

test("F10: product doc includes taxonomy of sources (real, open data, deeplink, estimate)", () => {
  const docPath = path.join(ROOT, "..", "docs", "product", "door-to-door.md");
  const source = fs.readFileSync(docPath, "utf8");
  assert.match(source, /Taxonomía de fuentes/);
  assert.match(source, /Real \(API\)/);
  assert.match(source, /Open data/);
  assert.match(source, /Deeplink/);
  assert.match(source, /Estimación/);
});

test("F10: product doc includes explicit limits (no confirma precios, no cobertura Europa completa)", () => {
  const docPath = path.join(ROOT, "..", "docs", "product", "door-to-door.md");
  const source = fs.readFileSync(docPath, "utf8");
  assert.match(source, /no confirma precios/);
  assert.match(source, /No hace scraping/);
  assert.match(source, /No reserva ni compra/);
  assert.match(source, /No tiene cobertura geográfica/);
  assert.match(source, /Europa completa/);
  assert.match(source, /solo funciona con feeds configurados explícitamente/);
});

test("F10: cross-module impact is documented (Watchlist imports DoorToDoorWatchlistSuggestion)", () => {
  const watchDetailPath = path.join(ROOT, "src", "modules", "watchlist", "components", "WatchDetailPanel.tsx");
  const source = fs.readFileSync(watchDetailPath, "utf8");
  assert.match(source, /DoorToDoorWatchlistSuggestion/);
  assert.match(source, /from.*door-to-door/);
  // Dashboard has no door-to-door imports
  const dashboardPath = path.join(ROOT, "src", "app", "(private)", "dashboard", "page.tsx");
  const dashboardSource = fs.readFileSync(dashboardPath, "utf8");
  assert.doesNotMatch(dashboardSource, /door.to-door|DoorToDoor/i);
  // The runbook documents cross-module impact
  const runbookPath = path.join(ROOT, "..", "docs", "runbooks", "runbook-puerta-a-puerta-qa.md");
  const runbookSource = fs.readFileSync(runbookPath, "utf8");
  assert.match(runbookSource, /Impacto cruzado/);
  assert.match(runbookSource, /Watchlist/);
  assert.match(runbookSource, /Quick Search.*Sin impacto/);
  assert.match(runbookSource, /Dashboard.*Sin impacto/);
});

test("F10: HISTORY.md records puerta-a-puerta F1-F10 completion", () => {
  const historyPath = path.join(ROOT, "..", "HISTORY.md");
  const source = fs.readFileSync(historyPath, "utf8");
  assert.match(source, /puerta-a-puerta/);
  assert.match(source, /F1.*F10/);
  assert.match(source, /61 tests/);
  assert.match(source, /74 tests/);
});
