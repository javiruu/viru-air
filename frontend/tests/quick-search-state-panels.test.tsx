import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { QuickSearchLoadingProgress } from "../src/modules/quick-search/components/QuickSearchLoadingProgress";
import { QuickSearchStatePanels } from "../src/modules/quick-search/components/QuickSearchStatePanels";
import { getQuickSearchVisualState } from "../src/modules/quick-search/state/getQuickSearchVisualState";

function t(key: string) {
  const copy: Record<string, string> = {
    searchReadyTitle: "Listo para explorar",
    searchReadyText: "Introduce una ruta y pulsa Buscar",
    searchReadyHint: "Puedes ampliar con alternativos",
    rateLimitTitle: "Demasiadas peticiones",
    rateLimitText: "Espera un momento",
    stateRateHint: "Protegemos el servicio",
    rateLimitCountdown: "Reintento en",
    errorTitle: "Algo fallo",
    searchFailed: "No se pudo completar",
    stateErrorHint: "Revisa el formulario",
    errorRetry: "Reintentar",
    emptyText: "Prueba a relajar restricciones",
    stateEmptyHint: "Ajusta filtros o usa una accion rapida",
    emptyCta: "Relajar filtros",
    emptyLikelyCausesTitle: "Causas probables",
    emptyShowMore: "Ver mas",
    emptyShowLess: "Ver menos",
    emptyRelaxActionsTitle: "Acciones rapidas",
  };
  return copy[key] || key;
}

test("QuickSearchStatePanels renders empty state causes and relax actions", () => {
  const html = renderToStaticMarkup(
    <QuickSearchStatePanels
      searchState="empty"
      rateLimitSeconds={0}
      searchError={null}
      emptyStateMainTitle="0 resultados con estos filtros"
      locale="es"
      zeroResultCauses={["Strict activo", "Escalas desactivadas", "Radio corto", "Exclusiones activas"]}
      visibleZeroResultCauses={["Strict activo", "Escalas desactivadas", "Radio corto"]}
      canExpandZeroResultCauses={true}
      emptyCausesExpanded={false}
      zeroResultActions={[
        { id: "disable_strict", label: "Desactivar strict" },
        { id: "open_radius_150", label: "Abrir radio" },
      ]}
      onToggleEmptyCauses={() => undefined}
      onRelaxAction={() => undefined}
      onRunSearch={() => undefined}
      onEmptyCta={() => undefined}
      t={t}
    />,
  );

  assert.match(html, /0 resultados con estos filtros/);
  assert.match(html, /Causas probables/);
  assert.match(html, /Strict activo/);
  assert.match(html, /Desactivar strict/);
  assert.match(html, /Relajar filtros/);
  assert.match(html, /Ver mas/);
});

test("QuickSearchStatePanels renders retry affordance for error state", () => {
  const html = renderToStaticMarkup(
    <QuickSearchStatePanels
      searchState="error"
      rateLimitSeconds={0}
      searchError="backend exploded"
      emptyStateMainTitle=""
      locale="es"
      zeroResultCauses={[]}
      visibleZeroResultCauses={[]}
      canExpandZeroResultCauses={false}
      emptyCausesExpanded={false}
      zeroResultActions={[]}
      onToggleEmptyCauses={() => undefined}
      onRelaxAction={() => undefined}
      onRunSearch={() => undefined}
      onEmptyCta={() => undefined}
      t={t}
    />,
  );

  assert.match(html, /Algo fallo/);
  assert.match(html, /backend exploded/);
  assert.match(html, /Reintentar/);
});

test("visual loading keeps the empty panel hidden until the search is really finished", () => {
  const visualState = getQuickSearchVisualState({
    searchState: "empty",
    showLoader: false,
    loadingVisualHold: true,
    visibleResultsCount: 0,
  });
  const panelState =
    visualState === "success_empty"
      ? "empty"
      : visualState === "success_with_results"
        ? "success"
        : visualState;
  const html = renderToStaticMarkup(
    <>
      <QuickSearchLoadingProgress
        show={visualState === "loading"}
        loadingVisualHold={true}
        loadingAria="Cargando"
        loadingPhaseLabel="Preparando vista"
        progressPercent={95}
        loadingSubcheckTitle="Comprobaciones"
        loadingSubchecks={[{ id: "request", label: "Buscando vuelos", status: "active" }]}
        loadingSubcheckDone="completado"
        loadingSubcheckActive="en curso"
        prefersReducedMotion={true}
        boardedCount={0}
        showBoarding={false}
        boardingPassengers={4}
        loadingTitle="Buscando vuelos"
        loadingText="Espera mientras preparamos la vista"
        loadingTotalText="0 resultados"
        loadingProgressText="95% completado"
        loadingScopeText="Comprobando disponibilidad"
      />
      <QuickSearchStatePanels
        searchState={panelState}
        rateLimitSeconds={0}
        searchError={null}
        emptyStateMainTitle="0 resultados con estos filtros"
        locale="es"
        zeroResultCauses={["Strict activo"]}
        visibleZeroResultCauses={["Strict activo"]}
        canExpandZeroResultCauses={false}
        emptyCausesExpanded={false}
        zeroResultActions={[]}
        onToggleEmptyCauses={() => undefined}
        onRelaxAction={() => undefined}
        onRunSearch={() => undefined}
        onEmptyCta={() => undefined}
        t={t}
      />
    </>,
  );

  assert.match(html, /qs-state-loading/);
  assert.doesNotMatch(html, /qs-state-empty/);
  assert.doesNotMatch(html, /0 resultados con estos filtros/);
});

test("visual loading stays dominant when the loader is already active for a fast final-empty response", () => {
  const visualState = getQuickSearchVisualState({
    searchState: "empty",
    showLoader: true,
    loadingVisualHold: false,
    visibleResultsCount: 0,
  });
  const panelState =
    visualState === "success_empty"
      ? "empty"
      : visualState === "success_with_results"
        ? "success"
        : visualState;
  const html = renderToStaticMarkup(
    <QuickSearchStatePanels
      searchState={panelState}
      rateLimitSeconds={0}
      searchError={null}
      emptyStateMainTitle="0 resultados con estos filtros"
      locale="es"
      zeroResultCauses={["Strict activo"]}
      visibleZeroResultCauses={["Strict activo"]}
      canExpandZeroResultCauses={false}
      emptyCausesExpanded={false}
      zeroResultActions={[]}
      onToggleEmptyCauses={() => undefined}
      onRelaxAction={() => undefined}
      onRunSearch={() => undefined}
      onEmptyCta={() => undefined}
      t={t}
    />,
  );

  assert.equal(visualState, "loading");
  assert.doesNotMatch(html, /qs-state-empty/);
  assert.doesNotMatch(html, /0 resultados con estos filtros/);
});
