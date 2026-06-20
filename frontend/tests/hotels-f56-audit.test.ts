import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

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
  assert.match(source, /<HotelProviderStatusPill rates=\{detail\.rates\} \/>/);

  assert.ok(source.indexOf("<HotelTrackedOffersPanel") > source.indexOf('className={`panel panel-soft hotel-results-panel'));
  assert.ok(source.indexOf("<HotelPriceTimeline") > source.indexOf("<HotelTrackedOffersPanel"));
  assert.ok(source.indexOf("<HotelWatchlistPanel") < source.indexOf("<HotelCompSetPanel"));
  assert.match(source, /onDeleteCompSet=\{compSets\.handleDeleteCompSet\}/);
});

test("H56: Hotel search keeps area mode and explicit live-provider toggle", () => {
  const source = fs.readFileSync(HOTELS_SEARCH, "utf8");

  assert.match(source, /searchMode: "name" \| "area"/);
  assert.match(source, /hotel-search-area-grid/);
  assert.match(source, /onAreaResolve/);
  assert.match(source, /onSelectArea/);
  assert.match(source, /radiusKm/);
  assert.match(source, /useProvider/);
  assert.match(source, /hotel-provider-toggle/);
  assert.match(source, /t\("hotels\.search\.useProviderLabel"\)/);
});

test("H56: provider and parity states remain signal-focused instead of booking-focused", () => {
  const source = fs.readFileSync(HOTELS_SIGNALS, "utf8");
  const i18n = fs.readFileSync(HOTELS_I18N, "utf8");

  assert.match(source, /t\("hotels\.provider\.active"\)/);
  assert.match(source, /t\("hotels\.provider\.noSignal"\)/);
  assert.match(source, /t\("hotels\.parity\.limited"\)/);
  assert.match(source, /t\("hotels\.parity\.limitedDetail"\)/);

  assert.match(i18n, /statusMock: "Proveedor mock"/);
  assert.match(i18n, /noSignal: "Sin señal todavía"/);
  assert.match(i18n, /limited: "Señal limitada"|limited: "SeÃ±al limitada"/);
  assert.doesNotMatch(i18n, /Book now|Reserva ahora|Comprar ahora/);
});

test("H57: hotel result cards keep both tracking and watchlist actions visible", () => {
  const source = fs.readFileSync(HOTELS_SEARCH, "utf8");

  assert.match(source, /t\("hotels\.actions\.trackPrice"\)/);
  assert.match(source, /t\("hotels\.actions\.trackingActive"\)/);
  assert.match(source, /t\("hotels\.actions\.addToWatchlist"\)/);
  assert.match(source, /t\("hotels\.actions\.inWatchlist"\)/);
  assert.ok(source.indexOf('t("hotels.actions.addToWatchlist")') > source.indexOf('t("hotels.actions.trackPrice")'));
});

test("H57: weather promo card styles stay scoped instead of overriding every .card", () => {
  const css = fs.readFileSync(SCREENS_CSS, "utf8");

  assert.match(css, /\.cardm > \.card \{/);
  assert.match(css, /:root\[data-theme="dark"\] \.cardm > \.card \{/);
  assert.doesNotMatch(css, /\n\.card \{\n  position: relative;\n  width: 240px;\n  height: 130px;/);
});
