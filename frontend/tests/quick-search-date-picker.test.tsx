import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { QuickSearchDatePicker } from "../src/modules/quick-search/components/QuickSearchDatePicker";

test("QuickSearchDatePicker renders placeholder state with viru trigger markup", () => {
  const html = renderToStaticMarkup(
    <QuickSearchDatePicker
      name="travel_date"
      label="Fecha"
      value=""
      onChange={() => undefined}
      placeholder="Selecciona fechas"
      localeTag="es-ES"
      variant="outbound"
    />,
  );

  assert.match(html, /data-ui="qs-date-picker-v2"/);
  assert.match(html, /Selecciona salida/);
  assert.match(html, /qs-date-trigger/);
  assert.doesNotMatch(html, /type="date"/);
  assert.doesNotMatch(html, /qs-date-popover/);
});

test("QuickSearchDatePicker renders open calendar grid with selected day", () => {
  const html = renderToStaticMarkup(
    <QuickSearchDatePicker
      name="return_date"
      label="Vuelta"
      value="2026-06-14"
      min="2026-06-10"
      onChange={() => undefined}
      placeholder="Selecciona fechas"
      localeTag="es-ES"
      variant="return"
      defaultOpen={true}
      dayHintsByIso={{
        "2026-06-14": {
          date: "2026-06-14",
          min_price: 89.12,
          bucket: "low",
        },
      }}
    />,
  );

  assert.match(html, /Vuelta/);
  assert.match(html, /junio de 2026/i);
  assert.match(html, /qs-date-popover__grid/);
  assert.match(html, /qs-date-day is-selected/);
  assert.match(html, /data-date="2026-06-14"/);
  assert.match(html, /Fecha seleccionada/);
  assert.match(html, /Vuelta elegida/);
});

test("QuickSearchDatePicker renders no-data marker with compact tooltip", () => {
  const html = renderToStaticMarkup(
    <QuickSearchDatePicker
      name="travel_date"
      label="Fecha"
      value="2026-06-10"
      onChange={() => undefined}
      placeholder="Selecciona fechas"
      localeTag="es-ES"
      variant="outbound"
      defaultOpen={true}
      dayHintsByIso={{
        "2026-06-11": {
          date: "2026-06-11",
          min_price: null,
          bucket: "none",
          no_data_reason: "no_fare_data",
        },
      }}
    />,
  );

  assert.match(html, /qs-date-day__no-price-icon/);
  assert.match(html, /qs-date-day__no-price-tooltip/);
  assert.match(html, /Sin datos de precio para este d(?:í|i)a/);
});
