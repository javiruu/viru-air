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
  const provider = resolveQuickSearchProviderPresentation("easyjet-public-availability");

  assert.equal(provider.id, "easyjet");
  assert.equal(provider.label, "easyJet");
  assert.equal(provider.rawSource, "easyjet-public-availability");
});

test("INITIAL_PROVIDER_SEARCH_STATUSES includes easyJet in provider lane", () => {
  assert.deepEqual(
    INITIAL_PROVIDER_SEARCH_STATUSES.map((provider) => provider.id),
    ["ryanair", "vueling", "wizzair", "easyjet", "duffel"],
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
