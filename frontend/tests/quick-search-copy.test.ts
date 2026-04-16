import assert from "node:assert/strict";
import test from "node:test";

import { getQuickSearchCopy } from "../src/modules/shared/quickSearchCopy";

test("quick search copy defaults to es", () => {
  const { locale, t } = getQuickSearchCopy(undefined);
  assert.equal(locale, "es");
  assert.equal(t("title"), "Búsqueda rápida");
});

test("quick search copy resolves en locale", () => {
  const { locale, t } = getQuickSearchCopy("en");
  assert.equal(locale, "en");
  assert.equal(t("title"), "Quick Search");
  assert.equal(t("ariaFiltersToggle"), "Filters ({count})");
  assert.equal(t("ariaRemoveFilter"), "Remove {value}");
  assert.equal(t("loadingSubcheckFlight"), "Searching flight {route}");
});

test("quick search warning fallback returns code", () => {
  const { tWarn } = getQuickSearchCopy("en");
  assert.equal(tWarn("unknown_code"), "unknown_code");
});

test("quick search copy exposes state microcopy in es", () => {
  const { t } = getQuickSearchCopy("es");
  assert.equal(t("stateEmptyHint"), "Ajusta filtros o usa una accion rapida para recuperar resultados.");
  assert.equal(t("stateErrorHint"), "Revisa los datos del formulario y vuelve a intentarlo.");
  assert.equal(t("stateRateHint"), "Hemos limitado temporalmente la frecuencia para proteger el servicio.");
  assert.equal(t("loadingSubcheckTitle"), "Comprobaciones en curso");
});
