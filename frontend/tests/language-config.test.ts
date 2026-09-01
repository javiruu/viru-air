import assert from "node:assert/strict";
import test from "node:test";

import { DEFAULT_LOCALE, LANGUAGES, localeTag, normalizeLocale } from "../src/i18n";

test("language selector uses one centralized ES/EN configuration", () => {
  assert.deepEqual(LANGUAGES.map(({ locale, shortLabel, countryCode }) => ({ locale, shortLabel, countryCode })), [
    { locale: "es", shortLabel: "ES", countryCode: "es" },
    { locale: "en", shortLabel: "EN", countryCode: "gb" },
  ]);
  assert.equal(DEFAULT_LOCALE, "es");
});

test("locale normalization and format tags keep the existing fallback contract", () => {
  assert.equal(normalizeLocale("en-GB"), "en");
  assert.equal(normalizeLocale("es-MX"), "es");
  assert.equal(normalizeLocale("fr-FR"), "es");
  assert.equal(localeTag("es"), "es-ES");
  assert.equal(localeTag("en"), "en-US");
});
