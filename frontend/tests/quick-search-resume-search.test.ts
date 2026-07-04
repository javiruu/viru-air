import assert from "node:assert/strict";
import test from "node:test";

import {
  buildResumeSearchSnapshot,
  clearDismissedResumeSearch,
  dismissResumeSearchSnapshot,
  loadResumeSearchSnapshot,
  saveResumeSearchSnapshot,
} from "@/modules/quick-search/resume-search";

type LocalStorageMock = {
  getItem: (key: string) => string | null;
  setItem: (key: string, value: string) => void;
  removeItem: (key: string) => void;
  clear: () => void;
};

function createLocalStorageMock(): LocalStorageMock {
  const store = new Map<string, string>();
  return {
    getItem: (key) => store.get(key) ?? null,
    setItem: (key, value) => store.set(key, value),
    removeItem: (key) => store.delete(key),
    clear: () => store.clear(),
  };
}

function installWindow() {
  const localStorage = createLocalStorageMock();
  Object.assign(globalThis, {
    window: {
      localStorage,
    },
  });
  localStorage.setItem("viru_token", "token-1234567890-abcdef");
  return localStorage;
}

function validArgs() {
  return {
    origin: "MAD",
    destination: "BGY",
    travelDate: "2026-08-20",
    returnDate: "",
    isReturn: false,
    adults: 1,
    daysBefore: 2,
    daysAfter: 2,
    radiusKm: 150,
    strictFilters: true,
    departAfter: "07:00",
    departBefore: "22:00",
    includeStops: false,
    maxStops: 1,
    bufferMin: "",
    includeNearbyOrigins: false,
    includeNearbyDestinations: true,
    excludeOrigins: [],
    excludeDestinations: [],
    priceMin: "",
    priceMax: "",
    durationMax: "",
    sortBy: "ranking" as const,
    resultsCount: 8,
    summary: "Te quedaste mirando MAD -> BGY.",
    detail: "Fechas flexibles y aeropuertos cercanos listos para retomar.",
  };
}

test("resume search stores and loads a useful snapshot", () => {
  const localStorage = installWindow();
  const snapshot = buildResumeSearchSnapshot({
    ...validArgs(),
    now: new Date("2026-07-04T12:00:00.000Z"),
  });

  assert.ok(snapshot);
  saveResumeSearchSnapshot(snapshot);

  const loaded = loadResumeSearchSnapshot(new Date("2026-07-04T14:00:00.000Z"));
  assert.ok(loaded);
  assert.equal(loaded.origin, "MAD");
  assert.match(loaded.href, /\/quick-search\?resume=1/);
  assert.equal(localStorage.getItem("viru_resume_search_snapshot") !== null, true);
});

test("resume search ignores empty or too-weak drafts", () => {
  installWindow();
  const snapshot = buildResumeSearchSnapshot({
    ...validArgs(),
    travelDate: "",
    daysBefore: 0,
    daysAfter: 0,
    includeNearbyDestinations: false,
    resultsCount: 0,
  });

  assert.equal(snapshot, null);
});

test("resume search hides dismissed or stale snapshots", () => {
  installWindow();
  const snapshot = buildResumeSearchSnapshot({
    ...validArgs(),
    now: new Date("2026-07-04T12:00:00.000Z"),
  });
  assert.ok(snapshot);
  saveResumeSearchSnapshot(snapshot);

  dismissResumeSearchSnapshot(snapshot.key);
  assert.equal(loadResumeSearchSnapshot(new Date("2026-07-04T14:00:00.000Z")), null);

  clearDismissedResumeSearch(snapshot.key);
  assert.ok(loadResumeSearchSnapshot(new Date("2026-07-04T14:00:00.000Z")));
  assert.equal(loadResumeSearchSnapshot(new Date("2026-07-07T12:30:00.000Z")), null);
});
