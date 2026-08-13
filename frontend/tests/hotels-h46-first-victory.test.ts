import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const HOTELS_I18N = path.join(process.cwd(), "src", "i18n", "domains", "hotels.ts");
const HOTELS_PAGE = path.join(process.cwd(), "src", "modules", "hotels", "HotelRadarPage.tsx");
const HOTELS_EMPTY = path.join(process.cwd(), "src", "modules", "hotels", "components", "HotelCompSetPanel.tsx");
const HOTELS_SEARCH_HOOK = path.join(process.cwd(), "src", "modules", "hotels", "hooks", "useHotelSearch.ts");
const HOTELS_TRACKED = path.join(process.cwd(), "src", "modules", "hotels", "hooks", "useTrackedOffers.ts");
const HOTELS_TIMELINE = path.join(process.cwd(), "src", "modules", "hotels", "components", "HotelTimelineAndSignals.tsx");
const HOTELS_TRACKING_CONFIRMATION = path.join(process.cwd(), "src", "modules", "hotels", "components", "HotelTrackingConfirmationDialog.tsx");

test("H46: watchlist copy is save semantics, not tracking semantics (ES/EN)", () => {
  const i18n = fs.readFileSync(HOTELS_I18N, "utf8");

  assert.match(i18n, /addToWatchlist: "Guardar hotel"/);
  assert.match(i18n, /inWatchlist: "Guardado"/);
  assert.match(i18n, /trackPrice: "Seguir precio"/);
  assert.match(i18n, /trackingActive: "Siguiendo precio"/);

  assert.match(i18n, /addToWatchlist: "Save hotel"/);
  assert.match(i18n, /inWatchlist: "Saved"/);
  assert.match(i18n, /trackPrice: "Follow price"/);
  assert.match(i18n, /trackingActive: "Following price"/);
});

test("H46: save confirmation never promises price tracking", () => {
  const i18n = fs.readFileSync(HOTELS_I18N, "utf8");

  assert.match(i18n, /watchAdded: "Hotel guardado\. No se ha activado ningún seguimiento de precio\."/);
  assert.match(i18n, /watchAdded: "Hotel saved\. No price tracking was activated\."/);
  assert.match(i18n, /watchAlreadyAdded: "Este hotel ya está guardado\."/);
  // The daily-review promise is only valid once H09/H23/H45 demonstrate the
  // policy; with the sweep CronJob suspended it must not be claimed.
  assert.ok(!/revisará la señal disponible cada día/.test(i18n));
  assert.ok(!/review the available signal daily/.test(i18n));
  assert.match(i18n, /trackedOfferCreated: "Seguimiento creado con el precio observado/);
});

test("H46: idle and empty states are distinct and recoverable", () => {
  const i18n = fs.readFileSync(HOTELS_I18N, "utf8");
  const page = fs.readFileSync(HOTELS_PAGE, "utf8");
  const empty = fs.readFileSync(HOTELS_EMPTY, "utf8");
  const hook = fs.readFileSync(HOTELS_SEARCH_HOOK, "utf8");

  assert.match(i18n, /idle: \{/);
  assert.match(i18n, /empty: \{/);
  assert.match(i18n, /title: "Empieza tu búsqueda"/);
  assert.match(i18n, /title: "Start searching"/);

  assert.match(hook, /hasSearched/);
  assert.match(hook, /setHasSearched\(true\)/);
  assert.match(page, /variant=\{search\.hasSearched \? "empty" : "idle"\}/);
  assert.match(empty, /variant\?: "idle" \| "empty"/);
  assert.match(empty, /"hotels\.idle\.title"/);
  assert.match(empty, /"hotels\.empty\.title"/);
});

test("H46: tracking is blocked without an eligible stay context", () => {
  const tracked = fs.readFileSync(HOTELS_TRACKED, "utf8");
  const i18n = fs.readFileSync(HOTELS_I18N, "utf8");

  assert.match(tracked, /trackingNeedsContext/);
  assert.match(tracked, /cheapest === null/);
  assert.match(i18n, /trackingNeedsContext:/);
  assert.match(i18n, /trackingNeedsContext: "Para seguir el precio hace falta una estancia/);
});

test("H23: tracking confirms a concrete observed offer through the V2 source rate", () => {
  const tracked = fs.readFileSync(HOTELS_TRACKED, "utf8");
  const page = fs.readFileSync(HOTELS_PAGE, "utf8");
  const timeline = fs.readFileSync(HOTELS_TIMELINE, "utf8");
  const confirmation = fs.readFileSync(HOTELS_TRACKING_CONFIRMATION, "utf8");

  assert.match(tracked, /createTrackedOfferV2/);
  assert.ok(!/await createTrackedOffer\(/.test(tracked));
  assert.match(tracked, /trackingCandidate/);
  assert.match(page, /HotelTrackingConfirmationDialog/);
  assert.match(timeline, /onTrackRate/);
  assert.match(confirmation, /room_label/);
  assert.match(confirmation, /cancellation_policy/);
  assert.match(confirmation, /onConfirm/);
});
