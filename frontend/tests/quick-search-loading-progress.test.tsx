import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { QuickSearchLoadingProgress } from "../src/modules/quick-search/components/QuickSearchLoadingProgress";

test("QuickSearchLoadingProgress stays hidden when loader is inactive and not held", () => {
  const html = renderToStaticMarkup(
    <QuickSearchLoadingProgress
      show={false}
      loadingVisualHold={false}
      loadingAria="Cargando"
      loadingPhaseLabel="Consultando tarifas"
      progressPercent={0}
      loadingSubcheckTitle="Comprobaciones"
      loadingSubchecks={[]}
      loadingSubcheckDone="ok"
      loadingSubcheckActive="activo"
      prefersReducedMotion={false}
      boardedCount={0}
      showBoarding={false}
      boardingPassengers={4}
      loadingTitle="Buscando vuelos"
      loadingText="Espera mientras preparamos la vista"
      loadingTotalText="Vuelos a buscar: 120"
      loadingProgressText="Progreso: 0/120 vuelos"
      loadingScopeText="Cobertura activa: 24 rutas x 5 dias"
    />,
  );

  assert.equal(html, "");
});

test("QuickSearchLoadingProgress renders progress, subchecks and skeleton cards", () => {
  const html = renderToStaticMarkup(
    <QuickSearchLoadingProgress
      show={true}
      loadingVisualHold={false}
      loadingAria="Cargando"
      loadingPhaseLabel="Ordenando resultados"
      progressPercent={42}
      loadingSubcheckTitle="Comprobaciones"
      loadingSubchecks={[
        { id: "flight", label: "Buscando vuelo MAD-DUB", status: "done" },
        { id: "ranking", label: "Calculando ranking", status: "active" },
      ]}
      loadingSubcheckDone="completado"
      loadingSubcheckActive="en curso"
      prefersReducedMotion={true}
      boardedCount={1}
      showBoarding={true}
      boardingPassengers={4}
      loadingTitle="Buscando vuelos"
      loadingText="Espera mientras preparamos la vista"
      loadingTotalText="Vuelos a buscar: 120"
      loadingProgressText="Progreso: 50/120 vuelos"
      loadingScopeText="Cobertura activa: 24 rutas x 5 dias"
    />,
  );

  assert.match(html, /42%/);
  assert.match(html, /Buscando vuelo MAD-DUB/);
  assert.match(html, /Calculando ranking/);
  assert.match(html, /Buscando vuelos/);
  assert.match(html, /Vuelos a buscar: 120/);
  assert.match(html, /Progreso: 50\/120 vuelos/);
  assert.match(html, /Cobertura activa: 24 rutas x 5 dias/);
  assert.match(html, /qs-skeleton-card/);
});
