import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

import { buildHotelSearchQuery, readHotelSearchUrlState } from "../src/modules/hotels/hotelSearchUrlState";

const HOTEL_PAGE = path.join(process.cwd(), "src", "modules", "hotels", "HotelRadarPage.tsx");
const MY_HOTELS_PANEL = path.join(process.cwd(), "src", "modules", "hotels", "components", "HotelMyHotelsPanel.tsx");
const ALERTS_HOOK = path.join(process.cwd(), "src", "modules", "hotels", "hooks", "useHotelAlerts.ts");
const SEARCH_HOOK = path.join(process.cwd(), "src", "modules", "hotels", "hooks", "useHotelSearch.ts");
const TRACKING_HOOK = path.join(process.cwd(), "src", "modules", "hotels", "hooks", "useTrackedOffers.ts");
const TRACKING_PANEL = path.join(process.cwd(), "src", "modules", "hotels", "components", "HotelTrackedOffersPanel.tsx");

test("H47: the return panel survives canonical hotel search URL state", () => {
  const state = readHotelSearchUrlState(new URLSearchParams("panel=mis-hoteles&q=Madrid&searched=1"));

  assert.equal(state.panel, "mis-hoteles");
  assert.equal(
    buildHotelSearchQuery({
      ...state,
      selectedHotelId: null,
    }),
    "panel=mis-hoteles&q=Madrid&searched=1",
  );
});

test("H47: Mis hoteles is an in-place return surface with tracking, alerts, and saved hotels", () => {
  const page = fs.readFileSync(HOTEL_PAGE, "utf8");
  const alertsHook = fs.readFileSync(ALERTS_HOOK, "utf8");
  const searchHook = fs.readFileSync(SEARCH_HOOK, "utf8");
  const trackingHook = fs.readFileSync(TRACKING_HOOK, "utf8");
  const trackingPanel = fs.readFileSync(TRACKING_PANEL, "utf8");

  assert.ok(fs.existsSync(MY_HOTELS_PANEL));
  assert.match(page, /HotelMyHotelsPanel/);
  assert.match(page, /search\.navigatePanel\(isMyHotelsPanel \? "search" : "mis-hoteles"\)/);
  assert.match(alertsHook, /: \{ limit: 50 \}\)/);
  assert.match(searchHook, /selectedHotelId,\s*searchIntentId,/);
  assert.match(searchHook, /nextPanel === "search" \? null : selectedHotelId/);
  assert.match(trackingHook, /trackedOffersError/);
  assert.match(trackingHook, /handleSetTrackingActive/);
  assert.match(page, /trackedOffersError=\{tracked\.trackedOffersError\}/);
  assert.match(page, /onSetTrackingActive/);
  assert.match(trackingPanel, /confirmingDeletionOfferId/);
});
