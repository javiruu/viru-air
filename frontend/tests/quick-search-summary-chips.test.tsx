import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { QuickSearchSummaryChips } from "../src/modules/quick-search/components/QuickSearchSummaryChips";

test("QuickSearchSummaryChips renders compact relevant chips", () => {
  const html = renderToStaticMarkup(
    <QuickSearchSummaryChips
      title="Plan de vuelo"
      headline="MAD -> TSF"
      caption="1 pasajero - Solo ida - 8 may 2026"
      chips={[
        { id: "route", label: "Ruta exacta: MAD -> TSF", tone: "route" },
        { id: "nearby-origin", label: "Origen cercano", tone: "search" },
        { id: "radius", label: "Hasta 500 km", tone: "search", emphasis: true },
        { id: "separate-flights", label: "Vuelos separados", tone: "advanced" },
        { id: "avoids", label: "Evita BCN", tone: "result" },
      ]}
      missingBadges={["Falta vuelta"]}
      onOpenAdvanced={() => undefined}
      moreOptionsLabel="Más opciones"
    />,
  );

  assert.match(html, /data-ui="qs-summary-chips"/);
  assert.match(html, /Plan de vuelo/);
  assert.match(html, /MAD -&gt; TSF/);
  assert.match(html, /1 pasajero - Solo ida - 8 may 2026/);
  assert.match(html, /Ruta exacta: MAD -&gt; TSF/);
  assert.match(html, /Origen cercano/);
  assert.match(html, /Hasta 500 km/);
  assert.match(html, /qs-summary-chip-compact-highlight/);
  assert.match(html, /Vuelos separados/);
  assert.match(html, /Evita BCN/);
  assert.match(html, /Falta vuelta/);
  assert.match(html, /aria-haspopup="dialog"/);
  assert.match(html, /aria-controls="qs-advanced-drawer"/);
  assert.match(html, /Más opciones/);
  assert.doesNotMatch(html, /0 ajustes/);
});

test("QuickSearchSummaryChips renders nothing when no chip is relevant", () => {
  const html = renderToStaticMarkup(
    <QuickSearchSummaryChips title="Plan de vuelo" headline="MAD -> TSF" caption="1 pasajero" chips={[]} />,
  );

  assert.equal(html, "");
});
