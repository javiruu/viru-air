import assert from "node:assert/strict";
import test from "node:test";

import { resolveBridgeRoute } from "../src/modules/shared/routeBridges";

test("route bridges keep legacy history route compatible", () => {
  assert.equal(resolveBridgeRoute("/history"), "/watchlist");
});

test("route bridges point legacy preferences to canonical hub", () => {
  assert.equal(resolveBridgeRoute("/preferences"), "/preferencias");
});

test("route bridges point suggestions to support feedback idea", () => {
  assert.equal(resolveBridgeRoute("/suggestions"), "/soporte/feedback?type=idea");
});

test("route bridges support canonical preference tabs mapping", () => {
  assert.equal(resolveBridgeRoute("/preferencias/busqueda"), "/preferencias?tab=busqueda");
  assert.equal(resolveBridgeRoute("/preferencias/apariencia"), "/preferencias?tab=apariencia");
  assert.equal(resolveBridgeRoute("/preferencias/region"), "/preferencias?tab=region");
});

test("unknown route stays untouched", () => {
  assert.equal(resolveBridgeRoute("/watchlist"), "/watchlist");
});
