import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { HelpSections, type HelpSection } from "../src/modules/shared/HelpBase";

test("HelpSections renders CTA when section includes label and href", () => {
  const sections: HelpSection[] = [
    {
      title: "Watchlist",
      body: "Gestiona rutas.",
      cta_label: "Abrir Watchlist",
      cta_href: "/watchlist",
    },
  ];

  const html = renderToStaticMarkup(<HelpSections sections={sections} />);

  assert.match(html, /Abrir Watchlist/);
  assert.match(html, /href="\/watchlist"/);
});

test("HelpSections keeps compatibility when CTA fields are missing", () => {
  const sections: HelpSection[] = [{ title: "FAQ", body: "Contenido base." }];

  const html = renderToStaticMarkup(<HelpSections sections={sections} />);

  assert.match(html, /Contenido base\./);
  assert.doesNotMatch(html, /btn-ghost/);
});
