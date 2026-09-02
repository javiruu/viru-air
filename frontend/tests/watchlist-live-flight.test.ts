import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { readStylesheetTree } from "./helpers/read-stylesheet-tree";

import {
  formatLiveTime,
  liveCoverageTone,
  milestoneTimeSource,
  milestoneTimestamp,
  selectPrimaryFlightLabel,
  selectPrimaryLivePosition,
} from "../src/modules/watchlist/liveFlightPresentation";
import type { LiveFlightTracking } from "../src/modules/watchlist/liveFlightTypes";

function trackingFixture(): LiveFlightTracking {
  return {
    watch_id: "watch-1",
    coverage: "live",
    provider_status: "ok",
    generated_at: "2026-07-22T08:46:00Z",
    refresh_after_seconds: 60,
    legs: [
      {
        sequence: 0,
        identity: {
          flight_instance_fingerprint: "flight-instance",
          flight_number: "FR9602",
          carrier_code: "FR",
          origin_iata: "MAD",
          destination_iata: "FCO",
          scheduled_departure_at: "2026-07-22T08:30:00Z",
          scheduled_arrival_at: "2026-07-22T10:55:00Z",
        },
        operational: {
          status: "active",
          status_raw: "active",
          observed_at: "2026-07-22T08:45:00Z",
          expires_at: "2026-07-22T08:46:00Z",
          freshness: "fresh",
          provider: "aviationstack",
          callsign: "RYR9602",
          departure: {
            scheduled_at: "2026-07-22T08:30:00Z",
            estimated_at: "2026-07-22T08:35:00Z",
            actual_at: "2026-07-22T08:37:00Z",
            terminal: "1",
            gate: "B12",
            delay_minutes: 7,
          },
          arrival: {
            scheduled_at: "2026-07-22T10:55:00Z",
            estimated_at: "2026-07-22T11:02:00Z",
            actual_at: null,
            terminal: "3",
            gate: "E8",
            delay_minutes: 7,
          },
          position: {
            latitude: 41.1,
            longitude: 2.1,
            altitude_m: 9100,
            speed_mps: 220,
            heading_deg: 94,
            on_ground: false,
          },
          registration: "EI-TEST",
          aircraft_iata: "B738",
          aircraft_icao: "B738",
          data_quality: "observed",
        },
      },
    ],
  };
}

test("live flight presentation exposes only a provider-observed position", () => {
  const tracking = trackingFixture();

  assert.deepEqual(selectPrimaryLivePosition(tracking), {
    latitude: 41.1,
    longitude: 2.1,
    altitude_m: 9100,
    speed_mps: 220,
    heading_deg: 94,
    on_ground: false,
  });
  assert.equal(selectPrimaryFlightLabel(tracking), "FR9602");

  tracking.legs[0]!.operational!.position = null;
  assert.equal(selectPrimaryLivePosition(tracking), null);
});

test("live flight map follows the active leg instead of a landed leg with position", () => {
  const tracking = trackingFixture();
  const landedLeg = tracking.legs[0]!;
  landedLeg.operational!.status = "landed";
  landedLeg.identity.flight_number = "IB100";
  landedLeg.operational!.position = {
    latitude: 40.4,
    longitude: -3.7,
    altitude_m: 0,
    speed_mps: 0,
    heading_deg: 0,
    on_ground: true,
  };
  tracking.legs.push({
    ...landedLeg,
    sequence: 1,
    identity: {
      ...landedLeg.identity,
      flight_number: "IB200",
      origin_iata: "BCN",
      destination_iata: "FCO",
    },
    operational: {
      ...landedLeg.operational!,
      status: "active",
      freshness: "fresh",
      position: {
        latitude: 42.3,
        longitude: 4.8,
        altitude_m: 9600,
        speed_mps: 218,
        heading_deg: 82,
        on_ground: false,
      },
    },
  });

  assert.equal(selectPrimaryFlightLabel(tracking), "IB200");
  assert.deepEqual(selectPrimaryLivePosition(tracking), {
    latitude: 42.3,
    longitude: 4.8,
    altitude_m: 9600,
    speed_mps: 218,
    heading_deg: 82,
    on_ground: false,
  });
});

test("live flight milestones prefer actual, then estimated, then scheduled time", () => {
  const departure = trackingFixture().legs[0]!.operational!.departure;
  const arrival = trackingFixture().legs[0]!.operational!.arrival;

  assert.equal(milestoneTimestamp(departure), "2026-07-22T08:37:00Z");
  assert.equal(milestoneTimeSource(departure), "actual");
  assert.equal(milestoneTimestamp(arrival), "2026-07-22T11:02:00Z");
  assert.equal(milestoneTimeSource(arrival), "estimated");
  assert.equal(formatLiveTime("not-a-date", "es-ES"), "--");
});

test("live flight coverage tone distinguishes observed, stale, and unavailable data", () => {
  const tracking = trackingFixture();
  assert.equal(liveCoverageTone(tracking), "success");

  tracking.coverage = "cached";
  assert.equal(liveCoverageTone(tracking), "warning");

  tracking.coverage = "identity_missing";
  assert.equal(liveCoverageTone(tracking), "info");
});

test("watchlist live UI keeps map positions observed and multi-leg detail progressive", () => {
  const mapPanel = fs.readFileSync(
    path.join(process.cwd(), "src", "modules", "watchlist", "components", "WatchlistMapDecisionPanel.tsx"),
    "utf8",
  );
  const livePanel = fs.readFileSync(
    path.join(process.cwd(), "src", "modules", "watchlist", "components", "WatchLiveFlightPanel.tsx"),
    "utf8",
  );
  const screensCss = readStylesheetTree(path.join(process.cwd(), "src", "styles", "screens.css"));

  assert.doesNotMatch(mapPanel, /AnimatedRouteDot|watch-map-route-dot|✈/);
  assert.match(mapPanel, /watchlist\.map\.noObservedPosition/);
  assert.match(mapPanel, /<Plane aria-hidden=/);
  assert.match(mapPanel, /--watch-map-heading.*heading_deg/);
  assert.match(screensCss, /rotate\(var\(--watch-map-heading, 0deg\)\)/);
  assert.doesNotMatch(screensCss, /watch-map-live-marker[^}]*rotate\(16deg\)/s);
  assert.doesNotMatch(mapPanel, /return livePosition \? null : primary/);
  assert.doesNotMatch(mapPanel, /setActivePopupWatchId\(primary\.watchId\)/);
  assert.match(mapPanel, /<MapPopup[\s\S]*anchor="top"/);
  assert.match(mapPanel, /<MapPopup[\s\S]*offset=\{20\}/);
  assert.match(livePanel, /watch-live-flight-leg--secondary/);
  assert.match(livePanel, /<details/);
  assert.match(livePanel, /watchlist\.live\.legUnavailable/);
  assert.match(livePanel, /watchlist\.live\.providerSource/);
  assert.match(livePanel, /watchlist\.live\.altitude/);
  assert.doesNotMatch(livePanel, /filter\(\(leg\) => leg\.operational\)/);
});
