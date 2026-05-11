import assert from "node:assert/strict";
import test from "node:test";

import { PRODUCT_VOCAB, UNSPECIFIED_MODEL_NAMES } from "../src/modules/shared/productVocabulary";

test("product vocabulary maps canonical route/api/entity pairs", () => {
  assert.equal(PRODUCT_VOCAB.watchlist.entity, "FlightWatch");
  assert.equal(PRODUCT_VOCAB.history.entity, "PriceSnapshot");
  assert.equal(PRODUCT_VOCAB.alerts.entity, "AlertRule");
  assert.equal(PRODUCT_VOCAB.opportunities.route, "/recomendaciones");
  assert.equal(PRODUCT_VOCAB.feedback.route, "/soporte/feedback?type=idea");
});

test("legacy aliases stay explicit in vocabulary map", () => {
  assert.equal(PRODUCT_VOCAB.history.legacy, "/history");
  assert.equal(PRODUCT_VOCAB.preferences.legacy, "/preferences");
  assert.equal(PRODUCT_VOCAB.feedback.legacy, "/suggestions");
});

test("unspecified legacy model names are documented", () => {
  assert.deepEqual(UNSPECIFIED_MODEL_NAMES, ["watchlist_item", "activity_event", "system_status"]);
});
