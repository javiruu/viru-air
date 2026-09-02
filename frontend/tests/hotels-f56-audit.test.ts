import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { readStylesheetTree } from "./helpers/read-stylesheet-tree";

const HOTELS_ROUTE = path.join(process.cwd(), "src", "app", "(private)", "hoteles", "page.tsx");
const HOTELS_PAGE = path.join(process.cwd(), "src", "modules", "hotels", "HotelRadarPage.tsx");
const HOTELS_SEARCH = path.join(process.cwd(), "src", "modules", "hotels", "components", "HotelSearchPanel.tsx");
const HOTELS_SIGNALS = path.join(process.cwd(), "src", "modules", "hotels", "components", "HotelTimelineAndSignals.tsx");
const HOTELS_I18N = path.join(process.cwd(), "src", "i18n", "domains", "hotels.ts");
const SCREENS_CSS = path.join(process.cwd(), "src", "styles", "screens.css");

test("H56: /hoteles route stays wired to HotelRadarPage", () => {
  const source = fs.readFileSync(HOTELS_ROUTE, "utf8");
  assert.match(source, /import \{ HotelRadarPage \} from "@\/modules\/hotels\/HotelRadarPage";/);
  assert.match(source, /return <HotelRadarPage \/>;/);
});

test("H56: HotelRadarPage keeps the post-close composition and section order", () => {
  const source = fs.readFileSync(HOTELS_PAGE, "utf8");

  assert.match(source, /<HotelSearchPanel/);
  assert.match(source, /<HotelTrackedOffersPanel/);
  assert.match(source, /<HotelPriceTimeline/);
  assert.match(source, /<HotelWatchlistPanel/);
  assert.match(source, /<HotelParitySignal/);
  assert.match(source, /<HotelAlertsPanel/);
  assert.match(source, /<HotelCompSetPanel/);
  assert.match(source, /<HotelProviderStatusPill rates=\{detail\.rates\} signal=\{latestParitySignal\} \/>/);

  assert.ok(source.indexOf("<HotelTrackedOffersPanel") > source.indexOf('className={`panel panel-soft hotel-results-panel'));
  assert.ok(source.indexOf("<HotelPriceTimeline") > source.indexOf("<HotelTrackedOffersPanel"));
  assert.ok(source.indexOf("<HotelWatchlistPanel") < source.indexOf("<HotelCompSetPanel"));
  assert.match(source, /onDeleteCompSet=\{compSets\.handleDeleteCompSet\}/);
});

test("H56: Hotel search keeps area mode and explicit provider-signal toggle", () => {
  const source = fs.readFileSync(HOTELS_SEARCH, "utf8");

  assert.match(source, /searchMode: "name" \| "area"/);
  assert.match(source, /hotel-search-area-grid/);
  assert.match(source, /onAreaResolve/);
  assert.match(source, /onSelectArea/);
  assert.match(source, /radiusKm/);
  assert.match(source, /useProvider/);
  assert.match(source, /hotel-provider-toggle/);
  assert.match(source, /t\("hotels\.search\.useProviderLabel"\)/);
  assert.match(source, /providerHintOn/);
  assert.match(source, /providerHintOff/);
});

test("H32: hotel errors and collapsible panels expose accessible semantics", () => {
  const page = fs.readFileSync(HOTELS_PAGE, "utf8");

  assert.match(page, /role=\{search\.featureDisabled \? "status" : "alert"\}/);
  assert.match(page, /aria-live=\{search\.featureDisabled \? "polite" : "assertive"\}/);
  for (const panel of ["detail", "parity", "alerts", "compSet"]) {
    assert.match(page, new RegExp(`aria-controls="hotel-${panel === "compSet" ? "compset" : panel}-panel"`));
  }
});

test("H32: hotel mobile controls preserve 48px targets and long-content wrapping", () => {
  const css = readStylesheetTree(SCREENS_CSS);

  assert.match(css, /\.hotel-search-mode-tab \{[^}]*min-height:\s*48px/);
  assert.match(css, /\.hotel-area-suggestion-item \{[^}]*min-height:\s*48px/);
  assert.match(css, /\.hotel-overview-strip \{[^}]*grid-template-columns:\s*repeat\(3/s);
  assert.match(css, /@media \(max-width:\s*768px\)[\s\S]*\.hotel-overview-strip \{[^}]*overflow-x:\s*auto/s);
  assert.match(css, /\.hotel-provider-toggle-row \{[^}]*min-height:\s*48px/);
  assert.match(css, /\.hotel-result-main \{[^}]*display:\s*flex[^}]*width:\s*100%[^}]*min-height:\s*48px[^}]*overflow-wrap:\s*anywhere/);
  assert.match(css, /\.hoteles-layout,\s*\.hoteles-main-column,\s*\.hoteles-side-column,\s*\.hotel-search-panel,\s*\.hotel-results-panel,\s*\.hotel-results-list \{\s*min-width:\s*0;/);
  assert.match(css, /\.hotel-result-actions > button \{\s*min-height:\s*48px/);
  assert.match(css, /\.hoteles-page \.hotel-alerts-panel \.field \{\s*min-width:\s*0;/);
  assert.match(css, /\.hoteles-page \.hotel-alerts-panel \.qs-input-neutral \{[\s\S]*width:\s*100%;[\s\S]*max-width:\s*100%;[\s\S]*min-width:\s*0;/);
  assert.match(css, /\.hotel-area-spinner,[\s\S]*\.hotel-provider-toggle-row \{[\s\S]*animation:\s*none\s*!important/);
});

test("H56-H61: provider and parity states remain signal-focused instead of booking-focused", () => {
  const source = fs.readFileSync(HOTELS_SIGNALS, "utf8");
  const i18n = fs.readFileSync(HOTELS_I18N, "utf8");

  assert.match(source, /assessHotelSignal/);
  assert.match(i18n, /statusMock: "Modo demo"/);
  assert.match(i18n, /noObservations:/);
  assert.match(i18n, /insufficientData:/);
  assert.match(i18n, /limited: "Señal limitada"/);
  assert.doesNotMatch(i18n, /Book now|Reserva ahora|Comprar ahora/);
});

test("H57: hotel result cards keep both tracking and watchlist actions visible", () => {
  const source = fs.readFileSync(HOTELS_SEARCH, "utf8");

  assert.match(source, /t\("hotels\.actions\.trackPrice"\)/);
  assert.match(source, /t\("hotels\.actions\.trackAnotherOffer"\)/);
  assert.match(source, /t\("hotels\.actions\.addToWatchlist"\)/);
  assert.match(source, /t\("hotels\.actions\.inWatchlist"\)/);
  assert.ok(source.indexOf('t("hotels.actions.addToWatchlist")') > source.indexOf('t("hotels.actions.trackPrice")'));
});

test("H57: weather promo card styles stay scoped instead of overriding every .card", () => {
  const css = readStylesheetTree(SCREENS_CSS);

  assert.match(css, /\.cardm > \.card \{/);
  assert.match(css, /:root\[data-theme="dark"\] \.cardm > \.card \{/);
  assert.doesNotMatch(css, /\n\.card \{\n  position: relative;\n  width: 240px;\n  height: 130px;/);
});

test("H59-H60: hotel radar includes honest provider context and responsive hotel blocks", () => {
  const page = fs.readFileSync(HOTELS_PAGE, "utf8");
  const css = readStylesheetTree(SCREENS_CSS);

  assert.match(page, /hotel-provider-context/);
  assert.match(page, /providerHintOn/);
  assert.match(css, /\.hotel-tracked-offer-item \{/);
  assert.match(css, /\.hotel-comp-set-item \{/);
  assert.match(css, /\.hotel-nearby-item \{/);
  assert.match(css, /\.hotel-provider-context \{/);
});
