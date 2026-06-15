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
    ranking_score: 0.84,
    freshness_ts: "2026-06-01T08:00:00Z",
    stale_data: false,
    itinerary_type: "direct",
    legs: [],
    deeplink_url: "https://www.ryanair.com/es/es",
  };
}

function t(key: string) {
  const copy: Record<string, string> = {
    alternative: "Alternativa",
    resultsColRoute: "Ruta",
    resultsColPrice: "Precio",
    resultsColDuration: "Duracion",
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
    detailsScore: "Score",
    detailsBuffer: "Buffer",
    scoreHint: "Heuristica",
    summaryRadius: "Radio",
    sourceUnknown: "Fuente desconocida",
    aiPreferredPrice: "Precio recomendado",
    aiPreferredAria: "Resultado preferido por IA",
    aiPreferredReasonLabel: "Motivo recomendado",
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
      deeplinkUrl="https://www.ryanair.com/es/es/trip/flights/select?originIata=MAD&destinationIata=LIS&dateOut=2026-06-01&adults=1"
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
      formatMinutes={(value) => `${value ?? 0} min`}
      resultKey={(result) => result.result_id || "fallback"}
      getResultTags={() => [
        { key: "buffer", label: "margen amplio", tone: "low" },
        { key: "freshness-fresh", label: "Verificado 4 min", tone: "fresh" },
      ]}
      addToWatchlist={() => undefined}
      setExpandedRows={() => undefined}
      setSelectedResultId={() => undefined}
      setOpenRowMenuId={() => undefined}
      setCopyModalPayload={() => undefined}
      setCopyModalOpen={() => undefined}
      closeRowMenu={() => undefined}
      onTrackOpenRyanair={() => undefined}
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
  assert.match(html, /Abrir en Ryanair/);
  assert.match(html, /Verificado 4 min/);
  assert.doesNotMatch(html, /Frescura:/);
  assert.match(html, /trip\/flights\/select/);
});

test("QuickSearchResultsList accepts official relative deeplink variants and rejects landing pages", () => {
  const htmlWithRelativeLink = renderToStaticMarkup(
    <QuickSearchResultsList
      visibleResults={[{ ...buildResult(), deeplink_url: "/es/es/trip/flights/select?origin_iata=MAD&destination_iata=LIS&date_out=2026-06-01&adults=1" }]}
      compactView={false}
      expandedRows={{}}
      openRowMenuId={"res-1"}
      deeplinkUrl=""
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
      formatMinutes={(value) => `${value ?? 0} min`}
      resultKey={(result) => result.result_id || "fallback"}
      getResultTags={() => [{ key: "buffer", label: "margen amplio", tone: "low" }]}
      addToWatchlist={() => undefined}
      setExpandedRows={() => undefined}
      setSelectedResultId={() => undefined}
      setOpenRowMenuId={() => undefined}
      setCopyModalPayload={() => undefined}
      setCopyModalOpen={() => undefined}
      closeRowMenu={() => undefined}
      onTrackOpenRyanair={() => undefined}
      onTrackRowOverflow={() => undefined}
      onTrackCopyParams={() => undefined}
    />,
  );

  assert.match(htmlWithRelativeLink, /Abrir en Ryanair/);

  const htmlWithLandingOnly = renderToStaticMarkup(
    <QuickSearchResultsList
      visibleResults={[{ ...buildResult(), deeplink_url: "https://www.ryanair.com/es/es" }]}
      compactView={false}
      expandedRows={{}}
      openRowMenuId={"res-1"}
      deeplinkUrl=""
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
      formatMinutes={(value) => `${value ?? 0} min`}
      resultKey={(result) => result.result_id || "fallback"}
      getResultTags={() => [{ key: "buffer", label: "margen amplio", tone: "low" }]}
      addToWatchlist={() => undefined}
      setExpandedRows={() => undefined}
      setSelectedResultId={() => undefined}
      setOpenRowMenuId={() => undefined}
      setCopyModalPayload={() => undefined}
      setCopyModalOpen={() => undefined}
      closeRowMenu={() => undefined}
      onTrackOpenRyanair={() => undefined}
      onTrackRowOverflow={() => undefined}
      onTrackCopyParams={() => undefined}
    />,
  );

  assert.doesNotMatch(htmlWithLandingOnly, /Abrir en Ryanair/);
});

test("QuickSearchResultsList renders ai preferred tag and reason", () => {
  const html = renderToStaticMarkup(
    <QuickSearchResultsList
      visibleResults={[{ ...buildResult(), ai_preferred: true, ai_preferred_reason: "Precio recomendado por equilibrio." }]}
      compactView={false}
      expandedRows={{}}
      openRowMenuId={null}
      deeplinkUrl="https://www.ryanair.com/es/es/trip/flights/select?originIata=MAD&destinationIata=LIS&dateOut=2026-06-01&adults=1"
      origin="MAD"
      destination="LIS"
      radiusKm={150}
      departAfter="07:00"
      departBefore="22:00"
      localeTag="es"
      getCopyPayload={() => "payload"}
      rowMenuTriggerRefs={{ current: {} }}
      t={t}
      formatMoney={(value, currency) => `${currency || "EUR"} ${value}`}
      formatScore={(value) => value.toFixed(2)}
      formatMinutes={(value) => `${value ?? 0} min`}
      resultKey={(result) => result.result_id || "fallback"}
      getResultTags={() => [
        { key: "ai-preferred", label: "Precio recomendado", tone: "ai" },
        { key: "freshness-fresh", label: "Verificado 4 min", tone: "fresh" },
      ]}
      addToWatchlist={() => undefined}
      setExpandedRows={() => undefined}
      setSelectedResultId={() => undefined}
      setOpenRowMenuId={() => undefined}
      setCopyModalPayload={() => undefined}
      setCopyModalOpen={() => undefined}
      closeRowMenu={() => undefined}
      onTrackOpenRyanair={() => undefined}
      onTrackRowOverflow={() => undefined}
      onTrackCopyParams={() => undefined}
    />,
  );

  assert.match(html, /Precio recomendado/);
  assert.match(html, /Motivo recomendado/);
  assert.match(html, /Precio recomendado por equilibrio/);
  assert.match(html, /Resultado preferido por IA/);
  assert.match(html, /qs-result-row-ai/);
});

test("QuickSearchResultsList keeps ai and itinerary tags in compact view", () => {
  const html = renderToStaticMarkup(
    <QuickSearchResultsList
      visibleResults={[{ ...buildResult(), ai_preferred: true }]}
      compactView={true}
      expandedRows={{}}
      openRowMenuId={null}
      deeplinkUrl="https://www.ryanair.com/es/es/trip/flights/select?originIata=MAD&destinationIata=LIS&dateOut=2026-06-01&adults=1"
      origin="MAD"
      destination="LIS"
      radiusKm={150}
      departAfter="07:00"
      departBefore="22:00"
      localeTag="es"
      getCopyPayload={() => "payload"}
      rowMenuTriggerRefs={{ current: {} }}
      t={t}
      formatMoney={(value, currency) => `${currency || "EUR"} ${value}`}
      formatScore={(value) => value.toFixed(2)}
      formatMinutes={(value) => `${value ?? 0} min`}
      resultKey={(result) => result.result_id || "fallback"}
      getResultTags={() => [
        { key: "ai-preferred", label: "Precio recomendado", tone: "ai" },
        { key: "itinerary-direct", label: "Directo", tone: "fresh" },
        { key: "freshness-warm", label: "Visto 38 min", tone: "med" },
      ]}
      addToWatchlist={() => undefined}
      setExpandedRows={() => undefined}
      setSelectedResultId={() => undefined}
      setOpenRowMenuId={() => undefined}
      setCopyModalPayload={() => undefined}
      setCopyModalOpen={() => undefined}
      closeRowMenu={() => undefined}
      onTrackOpenRyanair={() => undefined}
      onTrackRowOverflow={() => undefined}
      onTrackCopyParams={() => undefined}
    />,
  );

  assert.match(html, /Precio recomendado/);
  assert.match(html, /Directo/);
  assert.match(html, /Visto 38 min/);
  assert.match(html, /Resultado preferido por IA/);
});

test("QuickSearchResultsList shows ai reason in expanded details", () => {
  const html = renderToStaticMarkup(
    <QuickSearchResultsList
      visibleResults={[{ ...buildResult(), ai_preferred: true, ai_preferred_reason: "Mas barato sin sacrificar frescura." }]}
      compactView={false}
      expandedRows={{ "res-1": true }}
      openRowMenuId={null}
      deeplinkUrl="https://www.ryanair.com/es/es/trip/flights/select?originIata=MAD&destinationIata=LIS&dateOut=2026-06-01&adults=1"
      origin="MAD"
      destination="LIS"
      radiusKm={150}
      departAfter="07:00"
      departBefore="22:00"
      localeTag="es"
      getCopyPayload={() => "payload"}
      rowMenuTriggerRefs={{ current: {} }}
      t={t}
      formatMoney={(value, currency) => `${currency || "EUR"} ${value}`}
      formatScore={(value) => value.toFixed(2)}
      formatMinutes={(value) => `${value ?? 0} min`}
      resultKey={(result) => result.result_id || "fallback"}
      getResultTags={() => [
        { key: "ai-preferred", label: "Precio recomendado", tone: "ai" },
        { key: "freshness-stale", label: "Precio historico", tone: "stale" },
      ]}
      addToWatchlist={() => undefined}
      setExpandedRows={() => undefined}
      setSelectedResultId={() => undefined}
      setOpenRowMenuId={() => undefined}
      setCopyModalPayload={() => undefined}
      setCopyModalOpen={() => undefined}
      closeRowMenu={() => undefined}
      onTrackOpenRyanair={() => undefined}
      onTrackRowOverflow={() => undefined}
      onTrackCopyParams={() => undefined}
    />,
  );

  assert.match(html, /details-res-1/);
  assert.match(html, /Mas barato sin sacrificar frescura/);
  assert.match(html, /Precio historico/);
});

test("QuickSearchResultsList omits empty ai reason copy", () => {
  const html = renderToStaticMarkup(
    <QuickSearchResultsList
      visibleResults={[{ ...buildResult(), ai_preferred: true, ai_preferred_reason: "   " }]}
      compactView={false}
      expandedRows={{}}
      openRowMenuId={null}
      deeplinkUrl="https://www.ryanair.com/es/es/trip/flights/select?originIata=MAD&destinationIata=LIS&dateOut=2026-06-01&adults=1"
      origin="MAD"
      destination="LIS"
      radiusKm={150}
      departAfter="07:00"
      departBefore="22:00"
      localeTag="es"
      getCopyPayload={() => "payload"}
      rowMenuTriggerRefs={{ current: {} }}
      t={t}
      formatMoney={(value, currency) => `${currency || "EUR"} ${value}`}
      formatScore={(value) => value.toFixed(2)}
      formatMinutes={(value) => `${value ?? 0} min`}
      resultKey={(result) => result.result_id || "fallback"}
      getResultTags={() => [{ key: "ai-preferred", label: "Precio recomendado", tone: "ai" }]}
      addToWatchlist={() => undefined}
      setExpandedRows={() => undefined}
      setSelectedResultId={() => undefined}
      setOpenRowMenuId={() => undefined}
      setCopyModalPayload={() => undefined}
      setCopyModalOpen={() => undefined}
      closeRowMenu={() => undefined}
      onTrackOpenRyanair={() => undefined}
      onTrackRowOverflow={() => undefined}
      onTrackCopyParams={() => undefined}
    />,
  );

  assert.doesNotMatch(html, /Motivo recomendado/);
});
