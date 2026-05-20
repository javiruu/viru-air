import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { DoorToDoorOptionCard } from "../src/modules/door-to-door/components/DoorToDoorOptionCard";
import { DoorToDoorRouteVisual } from "../src/modules/door-to-door/components/DoorToDoorRouteVisual";
import { DoorToDoorTimeline } from "../src/modules/door-to-door/components/DoorToDoorTimeline";
import type { DoorToDoorFlight, DoorToDoorOption } from "../src/modules/door-to-door/types";

const ROOT = process.cwd();
const PAGE = path.join(ROOT, "src", "app", "(private)", "puerta-a-puerta", "page.tsx");
const PANEL = path.join(ROOT, "src", "modules", "door-to-door", "DoorToDoorPanel.tsx");
const API = path.join(ROOT, "src", "modules", "door-to-door", "api.ts");
const NAV = path.join(ROOT, "src", "modules", "shared", "navigationV1.ts");
const WATCH_DETAIL = path.join(ROOT, "src", "modules", "watchlist", "components", "WatchDetailPanel.tsx");
const STYLES = path.join(ROOT, "src", "styles", "screens.css");

const flight: DoorToDoorFlight = {
  origin_airport: "AGP",
  destination_airport: "TSF",
  departure_at: "2026-06-14T14:20:00+02:00",
  arrival_at: "2026-06-14T16:55:00+02:00",
  flight_time_confidence: "estimated",
};

const option: DoorToDoorOption = {
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

test("Puerta a puerta route, nav, watchlist suggestion, and API contract are wired", () => {
  assert.match(fs.readFileSync(PAGE, "utf8"), /DoorToDoorPanel/);
  assert.match(fs.readFileSync(NAV, "utf8"), /\/puerta-a-puerta/);
  assert.match(fs.readFileSync(WATCH_DETAIL, "utf8"), /DoorToDoorWatchlistSuggestion/);
  const apiSource = fs.readFileSync(API, "utf8");
  assert.match(apiSource, /\/door-to-door\/search/);
  assert.match(apiSource, /\/door-to-door\/suggestions/);
  assert.match(apiSource, /\/door-to-door\/saved-location/);
  assert.match(apiSource, /\/door-to-door\/history/);
});

test("DoorToDoorPanel includes core states, filters, consent, and no coverage guidance", () => {
  const source = fs.readFileSync(PANEL, "utf8");
  assert.match(source, /empty/);
  assert.match(source, /loading/);
  assert.match(source, /partial/);
  assert.match(source, /no_coverage/);
  assert.match(source, /save_origin_as_default/);
  assert.match(source, /passengers/);
  assert.match(source, /luggage/);
  assert.match(source, /subir el margen/);
});

test("Door-to-door option, radar, and timeline render decision evidence", () => {
  const html = renderToStaticMarkup(
    <>
      <DoorToDoorOptionCard option={option} selected={true} chosen={false} onSelect={() => undefined} onChoose={() => undefined} />
      <DoorToDoorRouteVisual option={option} flight={flight} />
      <DoorToDoorTimeline option={option} flight={flight} />
    </>,
  );
  assert.match(html, /Mejor equilibrio/);
  assert.match(html, /42-68 EUR estimado/);
  assert.match(html, /riesgo bajo/);
  assert.match(html, /Almería/);
  assert.match(html, /Treviso centro/);
  assert.match(html, /Horario estimado/);
});

test("Door-to-door styles include responsive radar and mobile decision layout hooks", () => {
  const source = fs.readFileSync(STYLES, "utf8");
  assert.match(source, /d2d-route-visual/);
  assert.match(source, /d2d-decision-grid/);
  assert.match(source, /max-width: 680px/);
  assert.match(source, /prefers-reduced-motion/);
});
