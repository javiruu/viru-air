import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

import {
  getCommunityHubIndicator,
  getCommunityHubParticipation,
} from "@/modules/watchlist/communityHubPresentation";
import { createEmptyCommunityPricing } from "@/modules/watchlist/watchlistApiCompatibility";

const COMMUNITY_DRAWER = path.join(
  process.cwd(),
  "src",
  "modules",
  "watchlist",
  "components",
  "CommunityPricingDrawer.tsx",
);
const COMMUNITY_HOOK = path.join(
  process.cwd(),
  "src",
  "modules",
  "watchlist",
  "useCommunityPricing.ts",
);
const ACCOUNT_MENU = path.join(
  process.cwd(),
  "src",
  "modules",
  "shared",
  "AccountMenu.tsx",
);

test("community hub indicator prioritizes the traveler's pending contribution", () => {
  const communityPricing = createEmptyCommunityPricing();
  communityPricing.eligible = true;

  assert.equal(getCommunityHubIndicator(communityPricing), "pending");
});

test("community hub indicator shows public evidence when the route range is available", () => {
  const communityPricing = createEmptyCommunityPricing();
  communityPricing.aggregate.is_public = true;
  communityPricing.aggregate.sample_size = 4;
  communityPricing.aggregate.min_price = 67;
  communityPricing.aggregate.max_price = 89;

  assert.equal(getCommunityHubIndicator(communityPricing), "public");
});

test("community hub indicator acknowledges a contribution above aggregate state", () => {
  const communityPricing = createEmptyCommunityPricing();
  communityPricing.aggregate.is_public = true;
  communityPricing.response = {
    flew: true,
    price_per_traveler: 74,
    currency: "EUR",
  };

  assert.equal(getCommunityHubIndicator(communityPricing), "contributed");
});

test("community hub participation keeps opening read-only until an explicit action", () => {
  const communityPricing = createEmptyCommunityPricing();
  assert.equal(getCommunityHubParticipation(communityPricing), "purchase");

  communityPricing.eligible = true;
  assert.equal(getCommunityHubParticipation(communityPricing), "contribute");

  communityPricing.response = {
    flew: false,
    price_per_traveler: null,
    currency: "EUR",
  };
  assert.equal(getCommunityHubParticipation(communityPricing), "review");
});

test("community hub drawer preserves modal keyboard and focus behavior", () => {
  const source = fs.readFileSync(COMMUNITY_DRAWER, "utf8");
  const hookSource = fs.readFileSync(COMMUNITY_HOOK, "utf8");
  const accountMenuSource = fs.readFileSync(ACCOUNT_MENU, "utf8");

  assert.match(source, /role="dialog"/);
  assert.match(source, /aria-modal="true"/);
  assert.match(source, /closeButtonRef\.current\?\.focus\(\)/);
  assert.match(source, /event\.key === "Escape" && !isSaving/);
  assert.match(source, /aria-hidden="true"[\s\S]*disabled=\{isSaving\}/);
  assert.match(source, /aria-label=\{t\("watchlist\.communityPricing\.close"\)\}[\s\S]*disabled=\{isSaving\}/);
  assert.match(source, /event\.key !== "Tab"/);
  assert.match(source, /\}, \[activeWatchId\]\);/);
  assert.match(hookSource, /returnFocusRef\.current =/);
  assert.match(hookSource, /flushSync\(\(\) => \{/);
  assert.match(hookSource, /returnFocusTarget\?\.focus\(\)/);
  assert.match(hookSource, /await load\(\)\.catch\(\(\) => undefined\);[\s\S]*close\(\);/);
  assert.match(accountMenuSource, /event\.key === "Escape" && open/);
});
