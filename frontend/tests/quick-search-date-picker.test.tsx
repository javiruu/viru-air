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
    />,
  );

  assert.match(html, /Selecciona fechas/);
  assert.match(html, /qs-date-trigger/);
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
      defaultOpen={true}
    />,
  );

  assert.match(html, /Vuelta/);
  assert.match(html, /junio de 2026/i);
  assert.match(html, /qs-date-popover__grid/);
  assert.match(html, /qs-date-day is-selected/);
  assert.match(html, /Fecha seleccionada/);
});
