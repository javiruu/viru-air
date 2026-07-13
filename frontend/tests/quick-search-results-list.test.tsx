import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { QuickSearchResultsList } from "../src/modules/quick-search/components/QuickSearchResultsList";
import type { SearchResult } from "../src/modules/quick-search/types";

function buildResult(): SearchResult {
  return {
    result_id: "res-1",
    origin: "NDR",
    destination: "BVA",
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
    legs: [
      {
        origin_iata: "NDR",
        destination_iata: "BVA",
        dep_ts: "2026-06-01T09:15:00",
        arr_ts: "2026-06-01T10:50:00",
      },
    ],
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
    deepLink: "Abrir vuelo",
    detailsAlt: "Alternativos",
    detailsWindow: "Ventana",
    detailsScore: "Score",
    detailsBuffer: "Buffer",
    detailsLegs: "Tramos",
    source: "Fuente",
    weatherDepart: "Salida",
    weatherArrive: "Llegada",
    flightTime: "Vuelo",
    scoreHint: "Heuristica",
    summaryRadius: "Radio",
    sourceUnknown: "Fuente desconocida",
    aiPreferredPrice: "Precio recomendado",
    aiPreferredAria: "Resultado preferido por IA",
    aiPreferredReasonLabel: "Motivo recomendado",
    refreshPrice: "Actualizar precio",
    refreshPriceLoading: "Actualizando precio...",
    viewWatchlist: "Ver Watchlist",
  };
  return copy[key] || key;
}

test("QuickSearchResultsList renders the simplified result-row hierarchy without badges", () => {
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
      canRefreshPrice={() => true}
      refreshingResultId={null}
      refreshPrice={() => undefined}
      isInWatchlist={() => false}
      addToWatchlist={() => undefined}
      viewInWatchlist={() => undefined}
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

  assert.match(html, /Nador/);
  assert.match(html, /\(NDR\)/);
  assert.match(html, /Beauvais/);
  assert.match(html, /\(BVA\)/);
  assert.doesNotMatch(html, /Alternativa/);
  assert.match(html, /EUR 39/);
  assert.match(html, /Salida/);
  assert.match(html, /09:15/);
  assert.match(html, /Llegada/);
  assert.match(html, /10:50/);
  assert.match(html, /Guardar/);
  assert.doesNotMatch(html, /Actualizar precio/);
  assert.doesNotMatch(html, /Ver detalle/);
  assert.match(html, /Abrir vuelo/);
  assert.match(html, /Ryanair/);
  assert.match(html, /qs-provider-logo--ryanair/);
  assert.doesNotMatch(html, /qs-provider-badge/);
  assert.doesNotMatch(html, /Verificado 4 min/);
  assert.doesNotMatch(html, /qs-tag/);
  assert.match(html, /qs-result-flight-time[\s\S]*Vuelo:[\s\S]*95 min[\s\S]*Abrir vuelo/);
  assert.doesNotMatch(html, /Frescura:/);
  assert.doesNotMatch(html, /Duracion:/);
  assert.match(html, /trip\/flights\/select/);
});

test("QuickSearchResultsList derives arrival and flight time when legs are missing", () => {
  const html = renderToStaticMarkup(
    <QuickSearchResultsList
      visibleResults={[{ ...buildResult(), legs: [] }]}
      compactView={false}
      expandedRows={{}}
      openRowMenuId={null}
      deeplinkUrl=""
      origin="NDR"
      destination="BVA"
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
      canRefreshPrice={() => false}
      refreshingResultId={null}
      refreshPrice={() => undefined}
      isInWatchlist={() => false}
      addToWatchlist={() => undefined}
      viewInWatchlist={() => undefined}
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

  assert.match(html, /Salida/);
  assert.match(html, /09:15/);
  assert.match(html, /Llegada/);
  assert.match(html, /10:50/);
  assert.match(html, /Vuelo/);
  assert.match(html, /95 min/);
});

test("QuickSearchResultsList canonicalizes Ryanair deeplinks and rejects landing pages", () => {
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
      canRefreshPrice={() => false}
      refreshingResultId={null}
      refreshPrice={() => undefined}
      isInWatchlist={() => false}
      addToWatchlist={() => undefined}
      viewInWatchlist={() => undefined}
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

  assert.match(htmlWithRelativeLink, /Abrir vuelo/);
  assert.match(htmlWithRelativeLink, /href="https:\/\/www\.ryanair\.com\/es\/es\/trip\/flights\/select\?/);
  assert.match(htmlWithRelativeLink, /originIata=MAD/);
  assert.match(htmlWithRelativeLink, /destinationIata=LIS/);
  assert.match(htmlWithRelativeLink, /dateOut=2026-06-01/);
  assert.match(htmlWithRelativeLink, /tpOriginIata=MAD/);
  assert.match(htmlWithRelativeLink, /role="menuitem"[\s\S]*Ver detalle/);
  assert.doesNotMatch(htmlWithRelativeLink, /href="\/es\/es\/trip\/flights\/select/);
  assert.doesNotMatch(htmlWithRelativeLink, /origin_iata=/);
  assert.doesNotMatch(htmlWithRelativeLink, /date_out=/);

  const htmlWithAbsoluteInternalParams = renderToStaticMarkup(
    <QuickSearchResultsList
      visibleResults={[{ ...buildResult(), deeplink_url: "https://www.ryanair.com/es/es/trip/flights/select?origin_iata=AGP&destination_iata=DUB&date_out=2026-06-02&adults=2" }]}
      compactView={false}
      expandedRows={{}}
      openRowMenuId={null}
      deeplinkUrl=""
      origin="AGP"
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
      canRefreshPrice={() => false}
      refreshingResultId={null}
      refreshPrice={() => undefined}
      isInWatchlist={() => false}
      addToWatchlist={() => undefined}
      viewInWatchlist={() => undefined}
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

  assert.match(htmlWithAbsoluteInternalParams, /href="https:\/\/www\.ryanair\.com\/es\/es\/trip\/flights\/select\?/);
  assert.match(htmlWithAbsoluteInternalParams, /originIata=AGP/);
  assert.match(htmlWithAbsoluteInternalParams, /destinationIata=DUB/);
  assert.match(htmlWithAbsoluteInternalParams, /dateOut=2026-06-02/);
  assert.match(htmlWithAbsoluteInternalParams, /adults=2/);
  assert.doesNotMatch(htmlWithAbsoluteInternalParams, /origin_iata=/);
  assert.doesNotMatch(htmlWithAbsoluteInternalParams, /date_out=/);

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
      canRefreshPrice={() => false}
      refreshingResultId={null}
      refreshPrice={() => undefined}
      isInWatchlist={() => false}
      addToWatchlist={() => undefined}
      viewInWatchlist={() => undefined}
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

  assert.doesNotMatch(htmlWithLandingOnly, /Abrir vuelo/);
});

test("QuickSearchResultsList turns saved rows into a watchlist link action", () => {
  const html = renderToStaticMarkup(
    <QuickSearchResultsList
      visibleResults={[buildResult()]}
      compactView={false}
      expandedRows={{}}
      openRowMenuId={null}
      deeplinkUrl=""
      origin="NDR"
      destination="BVA"
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
      canRefreshPrice={() => false}
      refreshingResultId={null}
      refreshPrice={() => undefined}
      isInWatchlist={() => true}
      getWatchlistHref={() => "/watchlist?watchId=watch_123&origin=NDR&destination=BVA&travelDate=2026-06-01"}
      addToWatchlist={() => undefined}
      viewInWatchlist={() => undefined}
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

  assert.match(html, /Ver Watchlist/);
  assert.match(html, /href="\/watchlist\?watchId=watch_123&amp;origin=NDR&amp;destination=BVA&amp;travelDate=2026-06-01"/);
  assert.doesNotMatch(html, /Guardar/);
});

test("QuickSearchResultsList renders Wizz Air branding and avoids Ryanair fallback links", () => {
  const html = renderToStaticMarkup(
    <QuickSearchResultsList
      visibleResults={[{ ...buildResult(), source: "wizzair-farechart", deeplink_url: null }]}
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
      canRefreshPrice={() => false}
      refreshingResultId={null}
      refreshPrice={() => undefined}
      isInWatchlist={() => false}
      addToWatchlist={() => undefined}
      viewInWatchlist={() => undefined}
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

  assert.match(html, /Wizz Air/);
  assert.match(html, /wizzair-farechart/);
  assert.match(html, /Tramos/);
  assert.match(html, /Salida/);
  assert.match(html, /09:15/);
  assert.match(html, /Llegada/);
  assert.match(html, /10:50/);
  assert.match(html, /Vuelo/);
  assert.match(html, /95 min/);
  assert.doesNotMatch(html, /Abrir vuelo/);
});

test("QuickSearchResultsList renders the preferred result as an accessible star tooltip", () => {
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
      canRefreshPrice={() => true}
      refreshingResultId={null}
      refreshPrice={() => undefined}
      isInWatchlist={() => false}
      addToWatchlist={() => undefined}
      viewInWatchlist={() => undefined}
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

  assert.match(html, /Motivo recomendado/);
  assert.match(html, /Precio recomendado por equilibrio/);
  assert.match(html, /qs-result-recommendation-star/);
  assert.match(html, /role="tooltip"/);
  assert.doesNotMatch(html, /qs-tag/);
  assert.match(html, /qs-result-row-ai/);
});

test("QuickSearchResultsList keeps the star and provider logo but removes compact badges", () => {
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
      canRefreshPrice={() => true}
      refreshingResultId={null}
      refreshPrice={() => undefined}
      isInWatchlist={() => false}
      addToWatchlist={() => undefined}
      viewInWatchlist={() => undefined}
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

  assert.doesNotMatch(html, /Precio recomendado/);
  assert.doesNotMatch(html, /Directo/);
  assert.doesNotMatch(html, /Visto 38 min/);
  assert.doesNotMatch(html, /qs-tag/);
  assert.match(html, /qs-result-recommendation-star/);
  assert.match(html, /qs-provider-logo--ryanair/);
  assert.match(html, /Resultado preferido por IA/);
  assert.match(html, /Vuelo.*95 min/s);
});

test("QuickSearchResultsList keeps the AI reason on the star and omits detail badges", () => {
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
      canRefreshPrice={() => true}
      refreshingResultId={"res-1"}
      refreshPrice={() => undefined}
      isInWatchlist={() => false}
      addToWatchlist={() => undefined}
      viewInWatchlist={() => undefined}
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
  assert.match(html, /qs-result-recommendation-tooltip/);
  assert.doesNotMatch(html, /Precio historico/);
  assert.doesNotMatch(html, /qs-result-detail-tags/);
  assert.doesNotMatch(html, /Actualizando precio/);
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
      canRefreshPrice={() => false}
      refreshingResultId={null}
      refreshPrice={() => undefined}
      isInWatchlist={() => false}
      addToWatchlist={() => undefined}
      viewInWatchlist={() => undefined}
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
