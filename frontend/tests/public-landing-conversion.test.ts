import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const LANDING_PAGE = path.join(process.cwd(), "src", "app", "(public)", "page.tsx");

test("public landing uses the new four-block conversion structure", () => {
  const source = fs.readFileSync(LANDING_PAGE, "utf8");

  assert.match(source, /landing-conv-hero-grid/);
  assert.match(source, /landing-proof-cred/);
  assert.match(source, /landing-conv-decision/);
  assert.match(source, /landing-close-cta-v2/);
});

test("public landing keeps the demo calendar inside the hero demo and removes the old standalone preview section", () => {
  const source = fs.readFileSync(LANDING_PAGE, "utf8");

  assert.match(source, /demo-calendar-grid-v3/);
  assert.doesNotMatch(source, /landing-calendar-preview/);
});

test("public landing keeps conversion-focused actions in hero and close sections", () => {
  const source = fs.readFileSync(LANDING_PAGE, "utf8");

  assert.match(source, /public\.landing\.ctaEnter/);
  assert.match(source, /public\.landing\.ctaCreate/);
  assert.match(source, /public\.landing\.closeProofLabel/);
});
