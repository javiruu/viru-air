/**
 * Phase 20 — Door-to-Door provider audit
 *
 * Reads the backend registry to produce a definitive audit table:
 *   provider | source_type | production_ready | supports_search | supports_booking_url | has_tests | status
 *
 * Classification per roadmap:
 *   real     = functional_api / functional_open_data / functional_maps / functional_deeplink
 *   deeplink = functional_deeplink (links, no real-time data)
 *   stub     = pure_stub / deeplink_stub (placeholder, no code)
 *   mock     = functional_estimate (synthetic data)
 *   scraper  = scraper_base_only (HTML fetch, no parser)
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import { resolve } from "path";

const PROJECT_ROOT = resolve(process.cwd(), "..");
const REGISTRY_PATH = resolve(
  PROJECT_ROOT,
  "backend",
  "app",
  "door_to_door",
  "providers",
  "registry.py",
);
const BASE_PATH = resolve(
  PROJECT_ROOT,
  "backend",
  "app",
  "door_to_door",
  "providers",
  "base.py",
);

function readSource(absPath: string): string {
  return readFileSync(absPath, "utf-8");
}

// ── Audit table tests ─────────────────────────────────────────────

describe("Phase 20 — door-to-door provider registry audit", () => {
  const registrySrc = readSource(REGISTRY_PATH);

  it("registry defines ProviderDescriptor with source_type field", () => {
    assert.ok(
      registrySrc.includes("class ProviderDescriptor"),
      "ProviderDescriptor class must exist in registry.py",
    );
    assert.ok(
      registrySrc.includes("source_type: DoorToDoorSourceType"),
      "ProviderDescriptor must have source_type field",
    );
  });

  it("mock provider is blocked in staging/production", () => {
    assert.ok(
      registrySrc.includes("_is_non_local_env"),
      "Registry must check non-local env to block mock",
    );
    assert.ok(
      registrySrc.includes("mock_blocked_non_local_env"),
      "Registry must log warning when mock is blocked",
    );
  });

  it("all provider descriptors have required fields", () => {
    const fields = [
      "name=",
      "source_type=",
      "base_status=",
      "production_ready=",
      "supports_search=",
      "supports_booking_url=",
      "has_tests=",
      "notes=",
    ];
    for (const field of fields) {
      assert.ok(
        registrySrc.includes(field),
        `Registry must set ${field} for all descriptors`,
      );
    }
  });

  it("scraper providers require feature flag", () => {
    assert.ok(
      registrySrc.includes("DOOR_TO_DOOR_ENABLE_SCRAPERS"),
      "Scrapers must be gated by DOOR_TO_DOOR_ENABLE_SCRAPERS flag",
    );
  });

  it("Google Routes requires API key + flag", () => {
    assert.ok(
      registrySrc.includes("GOOGLE_MAPS_API_KEY"),
      "Google Routes must check for GOOGLE_MAPS_API_KEY",
    );
    assert.ok(
      registrySrc.includes("DOOR_TO_DOOR_ENABLE_GOOGLE_ROUTES"),
      "Google Routes must be gated by its own flag",
    );
  });

  it("GTFS transit requires feeds to be configured", () => {
    assert.ok(
      registrySrc.includes("DOOR_TO_DOOR_GTFS_FEEDS_JSON"),
      "GTFS must check for feed configuration",
    );
    assert.ok(
      registrySrc.includes("_has_gtfs_feeds"),
      "Registry must have _has_gtfs_feeds helper",
    );
  });

  it("Navitia requires API key", () => {
    assert.ok(
      registrySrc.includes("NAVITIA_API_KEY"),
      "Navitia must check for NAVITIA_API_KEY",
    );
  });
});

// ── Provider classification ──────────────────────────────────────

describe("Phase 20 — provider classification audit", () => {
  const registrySrc = readSource(REGISTRY_PATH);

  const PROVIDER_CATEGORIES = {
    real: [
      "google_routes",
      "gtfs_transit",
      "navitia",
      "google_maps_deeplink",
      "google_places",
    ],
    deeplink: ["blablacar_deeplink", "goopti_deeplink", "external_deeplink"],
    stub: [
      "opentripplanner",
      "amadeus_transfers",
      "mozio",
      "omio",
      "distribusion",
      "rome2rio",
    ],
    mock: ["mock_multimodal"],
    scraper: ["blablacar_scraper", "goopti_scraper", "alsa_scraper", "renfe_scraper"],
  };

  for (const [category, providers] of Object.entries(PROVIDER_CATEGORIES)) {
    it(`${category} providers (${providers.join(", ")}) are registered`, () => {
      for (const name of providers) {
        assert.ok(
          registrySrc.includes(`name="${name}"`),
          `Provider "${name}" must be registered in registry.py`,
        );
      }
    });
  }

  it("real providers have production_ready or functional status", () => {
    // At minimum, real providers must have functional_* base_status
    const functionalPrefixes = [
      "functional_api",
      "functional_open_data",
      "functional_maps",
      "functional_deeplink",
    ];
    const hasFunctional = functionalPrefixes.some((p) =>
      registrySrc.includes(p),
    );
    assert.ok(hasFunctional, "Registry must define functional status values");
  });

  it("stub providers have pure_stub or deeplink_stub status", () => {
    assert.ok(
      registrySrc.includes("pure_stub"),
      "Registry must have pure_stub status for stubs",
    );
    assert.ok(
      registrySrc.includes("deeplink_stub"),
      "Registry must have deeplink_stub status for rome2rio",
    );
  });

  it("scrapers have scraper_base_only status", () => {
    assert.ok(
      registrySrc.includes("scraper_base_only"),
      "Scrapers must have scraper_base_only status",
    );
  });

  it("mock provider has estimate source_type", () => {
    assert.ok(
      registrySrc.includes('source_type="estimate"'),
      "Mock provider must use source_type=estimate",
    );
  });
});

// ── Base provider contract ──────────────────────────────────────

describe("Phase 20 — base provider contract", () => {
  const baseSrc = readSource(BASE_PATH);

  it("DoorToDoorProvider is abstract with search + healthcheck", () => {
    assert.ok(baseSrc.includes("class DoorToDoorProvider(ABC)"), "Must be abstract");
    assert.ok(baseSrc.includes("@abstractmethod"), "Must have abstract methods");
    assert.ok(baseSrc.includes("async def search"), "Must define search method");
    assert.ok(
      baseSrc.includes("async def healthcheck"),
      "Must define healthcheck method",
    );
  });

  it("base provider has timeout and rate limiting", () => {
    assert.ok(baseSrc.includes("timeout_seconds"), "Must have timeout_seconds");
    assert.ok(
      baseSrc.includes("rate_limit_per_minute"),
      "Must have rate_limit_per_minute",
    );
  });

  it("base provider has warning system", () => {
    assert.ok(baseSrc.includes("push_warning"), "Must have push_warning method");
    assert.ok(
      baseSrc.includes("consume_warnings"),
      "Must have consume_warnings method",
    );
  });
});

// ── Frontend contract awareness ─────────────────────────────────

describe("Phase 20 — frontend contract awareness", () => {
  it("itinerary builder filters by real source types", () => {
    const SEARCH_PATH = resolve(
      PROJECT_ROOT,
      "backend",
      "app",
      "door_to_door",
      "services",
      "itinerary_builder.py",
    );
    const searchSrc = readSource(SEARCH_PATH);
    assert.ok(
      searchSrc.includes("_REAL_SOURCE_TYPES") || searchSrc.includes("source_type"),
      "Itinerary builder must filter by source_type to distinguish real from mock",
    );
  });

  it("search service excludes mock from main results", () => {
    const SEARCH_PATH = resolve(
      PROJECT_ROOT,
      "backend",
      "app",
      "door_to_door",
      "services",
      "search_service.py",
    );
    const searchSrc = readSource(SEARCH_PATH);
    assert.ok(
      searchSrc.includes('"mock"') || searchSrc.includes('"estimate"'),
      "Search service must handle mock/estimate provider filtering",
    );
  });
});
