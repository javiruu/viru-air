import assert from "node:assert/strict";
import test from "node:test";

import { t } from "../src/i18n/shell";

test("the shared shell resolves public and shared copy without loading product domains", () => {
  assert.equal(t("es", "public.landing.heroTitle"), "Deja de abrir diez pestañas para decidir un vuelo.");
  assert.equal(t("es", "public.auth.loginTitle"), "Entrar");
  assert.equal(t("en", "public.help.publicTitle"), "Help");
  assert.equal(t("en", "shared.theme.dark"), "Dark mode");
  assert.equal(t("es", "watchlist.heading"), "watchlist.heading");
});
