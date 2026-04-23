import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { QuickSearchFilterConsole } from "../src/modules/quick-search/components/QuickSearchFilterConsole";

const copy: Record<string, string> = {
  filterConsoleEyebrow: "Control",
  filterConsoleTitle: "Consola",
  filterConsoleSubtitle: "Ajusta filtros",
  filterCountLabel: "activos",
  toolbarFilters: "Filtros",
  coverageTitle: "Cobertura",
  timeTitle: "Horario",
  visibleResultsTitle: "Resultados visibles",
  stopsTitle: "Escalas",
  filterAppliedOnSearch: "Se aplica al buscar",
  filterAppliedToResults: "Ajusta la vista",
  filterPartialSupport: "Soporte parcial",
  filterCoverageDirect: "Solo ruta base",
  filterVisibleOpen: "Vista abierta",
  filterVisibleCustom: "Vista afinada",
  filterExperimentalOn: "Self-connect activo",
  filterExperimentalOff: "Directos primero",
  summaryStrictOn: "Strict activo",
  summaryStrictOff: "Strict desactivado",
  pendingChangesTitle: "Cambios sin aplicar",
  pendingChangesBody: "Pulsa Buscar para actualizar.",
  applyAndSearch: "Aplicar y buscar",
  toolbarActiveFilters: "Filtros activos",
  resetAll: "Restablecer todo",
  ariaRemoveFilter: "Eliminar {value}",
  filterNoActive: "Sin filtros extra",
};

function t(key: string) {
  return copy[key] || key;
}

function noop() {
  return undefined;
}

test("QuickSearchFilterConsole renders grouped summaries and active chips", () => {
  const html = renderToStaticMarkup(
    <QuickSearchFilterConsole
      activeChips={[{ id: "price-max", label: "Precio maximo: 120", onClear: noop }]}
      activeFiltersCount={1}
      appliedFiltersCount={1}
      pendingSearchChanges={true}
      isFiltersOpen={false}
      radiusActive={true}
      radiusKm={150}
      priceMin=""
      priceMax="120"
      durationMax=""
      riskFilter="all"
      sortBy="ranking"
      includeStops={false}
      maxStops={1}
      bufferMin=""
      includeNearbyOrigins={true}
      includeNearbyDestinations={false}
      departAfter="07:00"
      departBefore="22:00"
      strictFilters={true}
      excludeOrigins={[]}
      excludeDestinations={[]}
      excludeOriginInput=""
      excludeDestinationInput=""
      prefAvailable={false}
      prefBadge={false}
      fieldErrors={{}}
      filtersCloseRef={{ current: null }}
      t={t as any}
      formatRiskLabel={(value) => value || ""}
      setRadiusKm={noop}
      setPriceMin={noop}
      setPriceMax={noop}
      setDurationMax={noop}
      setRiskFilter={noop}
      setSortBy={noop}
      setIncludeStops={noop}
      setMaxStops={noop}
      setBufferMin={noop}
      setIncludeNearbyOrigins={noop}
      setIncludeNearbyDestinations={noop}
      setDepartAfter={noop}
      setDepartBefore={noop}
      setStrictFilters={noop}
      setExcludeOrigins={noop}
      setExcludeDestinations={noop}
      setExcludeOriginInput={noop}
      setExcludeDestinationInput={noop}
      addExcludeOrigin={noop}
      addExcludeDestination={noop}
      removeExcludeOrigin={noop}
      removeExcludeDestination={noop}
      onOpenFilters={noop}
      onCloseFilters={noop}
      onApplyAndSearch={noop}
      onApplyPreferences={noop}
      onClearAllFilters={noop}
      onResetCoverage={noop}
      onResetTiming={noop}
      onResetVisible={noop}
      onResetExperimental={noop}
      onPresetDirect={noop}
      onPresetOriginNearby={noop}
      onPresetBothNearby={noop}
      onPresetRegional={noop}
    />,
  );

  assert.match(html, /Consola/);
  assert.match(html, /Cobertura/);
  assert.match(html, /Resultados visibles/);
  assert.match(html, /Precio maximo: 120/);
  assert.match(html, /Cambios sin aplicar/);
  assert.match(html, /data-ui="qs-filter-console"/);
});
