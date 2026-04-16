import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { QuickSearchResultsList } from "../src/modules/quick-search/components/QuickSearchResultsList";
import type { SearchResult } from "../src/modules/quick-search/types";

function buildResult(): SearchResult {
  return {
    result_id: "res-1",
    origin: "MAD",
    destination: "LIS",
    travel_date: "2026-06-01",
    departure_time_local: "09:15",
    price: 39,
    price_total: 39,
    currency: "EUR",
    source: "ryanair",
    duration_total: 95,
    duration_total_min: 95,
    risk_label: "low",
    ranking_score: 0.84,
    freshness_ts: "2026-06-01T08:00:00Z",
    stale_data: false,
    itinerary_type: "direct",
    legs: [],
  };
}

function t(key: string) {
  const copy: Record<string, string> = {
    alternative: "Alternativa",
    resultsColRoute: "Ruta",
    resultsColPrice: "Precio",
    resultsColDuration: "Duracion",
    resultsColRisk: "Riesgo",
    resultsColFreshness: "Frescura",
    save: "Guardar",
    detailsToggle: "Ver detalle",
    detailsHide: "Ocultar detalle",
    rowActionsMoreAria: "Abrir mas acciones",
    rowActionsMenuAria: "Acciones adicionales",
    freshnessStale: "Desactualizado",
    score: "Score",
    deepLinkAlt: "Copiar parametros",
    deepLink: "Abrir en Ryanair",
    detailsAlt: "Alternativos",
    detailsWindow: "Ventana",
    detailsRisk: "Riesgo",
    detailsScore: "Score",
    detailsBuffer: "Buffer",
    scoreHint: "Heuristica",
    summaryRadius: "Radio",
    sourceUnknown: "Fuente desconocida",
  };
  return copy[key] || key;
}

test("QuickSearchResultsList renders result rows with primary actions and alternative badge", () => {
  const html = renderToStaticMarkup(
    <QuickSearchResultsList
      visibleResults={[buildResult()]}
      compactView={false}
      expandedRows={{}}
      openRowMenuId={null}
      deeplinkUrl=""
      hiddenHighRiskResults={[]}
      showHighRisk={false}
      origin="MAD"
      destination="DUB"
      radiusKm={150}
      departAfter="07:00"
      departBefore="22:00"
      localeTag="es"
      getCopyPayload={() => "payload"}
      rowMenuTriggerRefs={{ current: {} }}
      t={t}
      formatMoney={(value, currency) => `${currency || "EUR"} ${value}`}
      formatScore={(value) => value.toFixed(2)}
      formatRiskLabel={(label) => label || "--"}
      formatFreshness={(value) => value || "--"}
      formatMinutes={(value) => `${value ?? 0} min`}
      resultKey={(result) => result.result_id || "fallback"}
      getResultTags={() => [{ key: "risk", label: "bajo riesgo", tone: "low" }]}
      addToWatchlist={() => undefined}
      setExpandedRows={() => undefined}
      setSelectedResultId={() => undefined}
      setOpenRowMenuId={() => undefined}
      setCopyModalPayload={() => undefined}
      setCopyModalOpen={() => undefined}
      closeRowMenu={() => undefined}
      onTrackOpenRyanair={() => undefined}
      onToggleHighRisk={() => undefined}
      onTrackRowOverflow={() => undefined}
      onTrackCopyParams={() => undefined}
    />,
  );

  assert.match(html, /MAD/);
  assert.match(html, /LIS/);
  assert.match(html, /Alternativa/);
  assert.match(html, /EUR 39/);
  assert.match(html, /Guardar/);
  assert.match(html, /Ver detalle/);
});
