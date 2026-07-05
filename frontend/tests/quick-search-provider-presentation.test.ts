import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { QuickSearchProviderBadge } from "../src/modules/quick-search/components/QuickSearchProviderBadge";
import {
  INITIAL_PROVIDER_SEARCH_STATUSES,
  resolveQuickSearchProviderPresentation,
} from "../src/modules/quick-search/providerPresentation";

test("resolveQuickSearchProviderPresentation recognizes easyJet sources", () => {
  for (const source of ["easyjet-public-availability", "easy-jet-public", "easy_jet", "ezj-feed", "EZY availability", "U2 fares"]) {
    const provider = resolveQuickSearchProviderPresentation(source);

    assert.equal(provider.id, "easyjet");
    assert.equal(provider.label, "easyJet");
    assert.equal(provider.rawSource, source);
  }
});

test("resolveQuickSearchProviderPresentation recognizes Iberia sources", () => {
  for (const source of ["iberia-ndc-airshopping", "Iberia NDC", "IB fares"]) {
    const provider = resolveQuickSearchProviderPresentation(source);

    assert.equal(provider.id, "iberia");
    assert.equal(provider.label, "Iberia");
    assert.equal(provider.rawSource, source);
  }
});

test("INITIAL_PROVIDER_SEARCH_STATUSES includes easyJet in provider lane", () => {
  assert.deepEqual(
    INITIAL_PROVIDER_SEARCH_STATUSES.map((provider) => provider.id),
    ["ryanair", "vueling", "wizzair", "easyjet", "iberia", "duffel"],
  );
});

test("QuickSearchProviderBadge renders easyJet as a branded provider", () => {
  const html = renderToStaticMarkup(
    React.createElement(QuickSearchProviderBadge, { source: "easyjet-public-availability" }),
  );

  assert.match(html, /qs-provider-badge--easyjet/);
  assert.match(html, /easyJet/);
  assert.match(html, /#FF6600/);
});

test("QuickSearchProviderBadge renders Iberia as a branded provider", () => {
  const html = renderToStaticMarkup(
    React.createElement(QuickSearchProviderBadge, { source: "iberia-ndc-airshopping" }),
  );

  assert.match(html, /qs-provider-badge--iberia/);
  assert.match(html, /Iberia/);
  assert.match(html, /#D71920/);
});
