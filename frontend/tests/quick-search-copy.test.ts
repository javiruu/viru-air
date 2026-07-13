import assert from "node:assert/strict";
import test from "node:test";

import { getQuickSearchCopy } from "../src/modules/shared/quickSearchCopy";

test("quick search copy defaults to es", () => {
  const { locale, t } = getQuickSearchCopy(undefined);
  assert.equal(locale, "es");
  assert.equal(t("swapRoute"), "Intercambiar ruta");
});

test("quick search copy resolves en locale", () => {
  const { locale, t } = getQuickSearchCopy("en");
  assert.equal(locale, "en");
  assert.equal(t("title"), "Quick Search");
  assert.equal(t("ariaFiltersToggle"), "Active settings ({count})");
  assert.equal(t("ariaRemoveFilter"), "Remove filter {value}");
  assert.equal(t("loadingSubcheckFlight"), "Searching flight {route}");
  assert.equal(t("deepLink"), "Open flight");
});

test("quick search warning fallback returns code", () => {
  const { tWarn } = getQuickSearchCopy("en");
  assert.equal(tWarn("unknown_code"), "unknown_code");
});

test("quick search copy includes precise partial-provider warnings", () => {
  const es = getQuickSearchCopy("es");
  const en = getQuickSearchCopy("en");

  assert.equal(
    es.tWarn("ryanair_availability_failed_partial"),
    "No pudimos confirmar toda la disponibilidad de Ryanair; te mostramos solo lo que si respondio.",
  );
  assert.equal(
    en.tWarn("ryanair_fares_failed_partial"),
    "Some Ryanair fare checks failed; showing results confirmed by availability.",
  );
  assert.equal(es.tWarn("ryanair_unavailable_partial"), "Algunas combinaciones no pudieron consultarse.");
  assert.equal(
    es.tWarn("easyjet_provider_unavailable_total"),
    "easyJet no respondio y no pudimos confirmar vuelos en este momento.",
  );
  assert.equal(
    en.tWarn("easyjet_provider_unavailable_total"),
    "easyJet did not respond and we could not confirm flights right now.",
  );
});

test("quick search copy exposes state microcopy in es", () => {
  const { t } = getQuickSearchCopy("es");
  assert.equal(t("stateEmptyHint"), "Ajusta filtros o usa una accion rapida para recuperar resultados.");
  assert.equal(t("stateErrorHint"), "Revisa los datos del formulario y vuelve a intentarlo.");
  assert.equal(t("stateRateHint"), "Hemos limitado temporalmente la frecuencia para proteger el servicio.");
  assert.equal(t("loadingSubcheckTitle"), "Comprobaciones en curso");
  assert.equal(t("flexTitle"), "Que margen tienes con la fecha?");
  assert.equal(t("flexPresetCustom"), "Personalizar");
  assert.equal(t("flexCustomSummary"), "Fecha flexible: {before} dias antes y {after} dias despues");
  assert.equal(t("aiPreferredPrice"), "Mejor opcion encontrada");
  assert.equal(t("aiPreferredAria"), "Resultado preferido por IA");
  assert.equal(t("aiPreferredReasonLabel"), "Por qué lo recomendamos");
  assert.equal(t("swapRoute"), "Intercambiar ruta");
  assert.equal(t("recentAutocompleteLabel"), "Recientes guardados");
  assert.equal(t("sideViewControlsSubtitle"), "Estos filtros solo cambian este panel.");
  assert.equal(t("roundTripToggleHint"), "Activalo cuando quieras ver ida y vuelta en dos paneles coordinados.");
  assert.equal(t("passengersBaseFareHint"), "Precio base orientativo.");
  assert.equal(t("returnResetAfterOutboundChange"), "Hemos limpiado la vuelta para que puedas elegir una nueva fecha coherente.");
  assert.equal(t("deepLink"), "Abrir vuelo");
});
