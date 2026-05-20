import assert from "node:assert/strict";
import test from "node:test";

import { NAV_V1_PRIVATE } from "../src/modules/shared/navigationV1";

test("private nav follows canonical Phase 0 IA", () => {
  assert.deepEqual(
    NAV_V1_PRIVATE.map((item) => item.href),
    ["/dashboard", "/watchlist", "/puerta-a-puerta", "/quick-search", "/alerts", "/recomendaciones", "/preferencias", "/soporte/ayuda"],
  );
});

test("private nav does not expose suggestions as workspace module", () => {
  assert.equal(NAV_V1_PRIVATE.map((item) => item.href as string).includes("/suggestions"), false);
});
