import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const API = path.join(process.cwd(), "src", "modules", "hotels", "api.ts");
const HOOK = path.join(process.cwd(), "src", "modules", "hotels", "hooks", "useSavedHotelSearches.ts");
const PANEL = path.join(process.cwd(), "src", "modules", "hotels", "components", "HotelSavedSearchesPanel.tsx");
const PAGE = path.join(process.cwd(), "src", "modules", "hotels", "HotelRadarPage.tsx");
const I18N = path.join(process.cwd(), "src", "i18n", "domains", "hotels.ts");

test("H48: saved-search CRUD is wired separately from tracking", () => {
  const api = fs.readFileSync(API, "utf8");
  const hook = fs.readFileSync(HOOK, "utf8");
  const panel = fs.readFileSync(PANEL, "utf8");
  const page = fs.readFileSync(PAGE, "utf8");
  const i18n = fs.readFileSync(I18N, "utf8");

  assert.match(api, /listSavedHotelSearches/);
  assert.match(api, /createSavedHotelSearch/);
  assert.match(api, /updateSavedHotelSearch/);
  assert.match(api, /deleteSavedHotelSearch/);
  assert.match(hook, /useSavedHotelSearches/);
  assert.match(panel, /hotels\.savedSearches\.save/);
  assert.match(i18n, /save: "Guardar búsqueda"/);
  assert.match(page, /HotelSavedSearchesPanel/);
  assert.doesNotMatch(hook, /createTrackedOffer|createHotelAlertRule/);
});

test("H48: restoring a saved search strips private/navigation execution fields", () => {
  const page = fs.readFileSync(PAGE, "utf8");
  assert.match(page, /buildRestoredHotelSearchQuery/);
  assert.match(page, /hasSearched: false/);
  assert.match(page, /selectedHotelId: null/);
  assert.match(page, /router\.push\(`\/hoteles/);
});

test("H48: saved-search copy distinguishes active, paused, restore and delete", () => {
  const i18n = fs.readFileSync(I18N, "utf8");
  assert.match(i18n, /savedSearches:/);
  assert.match(i18n, /save: "Guardar búsqueda"/);
  assert.match(i18n, /restore: "Restaurar"/);
  assert.match(i18n, /pause: "Pausar"/);
  assert.match(i18n, /resume: "Reanudar"/);
  assert.match(i18n, /delete: "Eliminar"/);
  assert.match(i18n, /save: "Save search"/);
});
