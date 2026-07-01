import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { QuickSearchSummaryChips } from "../src/modules/quick-search/components/QuickSearchSummaryChips";

test("QuickSearchSummaryChips renders compact relevant chips", () => {
  const html = renderToStaticMarkup(
    <QuickSearchSummaryChips
      title="Tu busqueda"
      chips={[
        { id: "route", label: "Ruta exacta: MAD -> TSF", tone: "route" },
        { id: "nearby-origin", label: "Origen cercano", tone: "search" },
        { id: "radius", label: "Hasta 500 km", tone: "search" },
        { id: "separate-flights", label: "Vuelos separados", tone: "advanced" },
        { id: "avoids", label: "Evita BCN", tone: "result" },
      ]}
    />,
  );

  assert.match(html, /data-ui="qs-summary-chips"/);
  assert.match(html, /Ruta exacta: MAD -&gt; TSF/);
  assert.match(html, /Origen cercano/);
  assert.match(html, /Hasta 500 km/);
  assert.match(html, /Vuelos separados/);
  assert.match(html, /Evita BCN/);
  assert.doesNotMatch(html, /0 ajustes/);
});

test("QuickSearchSummaryChips renders nothing when no chip is relevant", () => {
  const html = renderToStaticMarkup(<QuickSearchSummaryChips title="Tu busqueda" chips={[]} />);

  assert.equal(html, "");
});
