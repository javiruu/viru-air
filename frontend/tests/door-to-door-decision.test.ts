import assert from "node:assert/strict";
import test from "node:test";

import { getAlternativeDeltas, getDecisionBadges, getDecisionReasons } from "../src/modules/door-to-door/decision";
import type { DoorToDoorOption } from "../src/modules/door-to-door/types";

function buildOption(partial: Partial<DoorToDoorOption> & Pick<DoorToDoorOption, "id" | "label">): DoorToDoorOption {
  return {
    id: partial.id,
    label: partial.label,
    description: partial.description ?? "",
    status: partial.status ?? "real_result",
    currency: partial.currency ?? "EUR",
    transfer_count: partial.transfer_count ?? 1,
    confidence: partial.confidence ?? "live",
    source_types: partial.source_types ?? ["api"],
    sources: partial.sources ?? [{ provider: "google_routes", source_provider: "google_routes", source_type: "api", confidence: "live", checked_at: "2026-05-20T10:00:00+02:00" }],
    legs: partial.legs ?? [],
    is_recommended: partial.is_recommended ?? false,
    is_extended: partial.is_extended ?? false,
    total_price_min: partial.total_price_min ?? null,
    total_price_max: partial.total_price_max ?? null,
    total_duration_minutes: partial.total_duration_minutes ?? null,
    airport_buffer_minutes: partial.airport_buffer_minutes ?? null,
    score: partial.score ?? null,
  };
}

test("decision badges are deterministic and mark the right winners", () => {
  const a = buildOption({ id: "a", label: "A", total_duration_minutes: 300, total_price_min: 80, transfer_count: 2, airport_buffer_minutes: 110 });
  const b = buildOption({ id: "b", label: "B", total_duration_minutes: 270, total_price_min: 90, transfer_count: 1, airport_buffer_minutes: 165 });
  const c = buildOption({ id: "c", label: "C", total_duration_minutes: 310, total_price_min: 70, transfer_count: 3, airport_buffer_minutes: 90 });

  const badges = getDecisionBadges([a, b, c]);

  assert.ok((badges.b ?? []).some((item) => item.kind === "fastest"));
  assert.ok((badges.b ?? []).some((item) => item.kind === "longest_buffer"));
  assert.ok((badges.b ?? []).some((item) => item.kind === "fewest_changes"));
  assert.ok((badges.c ?? []).some((item) => item.kind === "best_estimated_price"));
});

test("decision reasons prioritize price, buffer, and transfers when recommendation leads", () => {
  const recommended = buildOption({ id: "r", label: "R", total_price_min: 70, total_duration_minutes: 280, airport_buffer_minutes: 150, transfer_count: 1, is_recommended: true });
  const alt = buildOption({ id: "x", label: "X", total_price_min: 85, total_duration_minutes: 300, airport_buffer_minutes: 110, transfer_count: 2 });

  const reasons = getDecisionReasons(recommended, [recommended, alt]);
  assert.deepEqual(reasons.map((item) => item.kind), ["price", "buffer", "transfers"]);
});

test("decision reasons include confidence cue for deeplink/estimate data", () => {
  const recommended = buildOption({
    id: "r",
    label: "R",
    total_price_min: null,
    sources: [{ provider: "blablacar_deeplink", source_provider: "blablacar", source_type: "deeplink", confidence: "deeplink", checked_at: "2026-05-20T10:00:00+02:00" }],
    source_types: ["deeplink"],
    confidence: "deeplink",
  });
  const alt = buildOption({ id: "x", label: "X", total_price_min: null });

  const reasons = getDecisionReasons(recommended, [recommended, alt]);
  assert.ok(reasons.some((item) => item.kind === "confidence"));
});

test("alternative deltas compare against recommendation with null-safe fields", () => {
  const recommended = buildOption({ id: "r", label: "R", total_price_min: 80, total_duration_minutes: 300, airport_buffer_minutes: 120, transfer_count: 1, score: 90 });
  const alt = buildOption({ id: "x", label: "X", total_price_min: 95, total_duration_minutes: 280, airport_buffer_minutes: 100, transfer_count: 3, score: 70 });

  const deltas = getAlternativeDeltas(recommended, [recommended, alt]);
  assert.equal(deltas.length, 1);
  assert.equal(deltas[0].delta_price, 15);
  assert.equal(deltas[0].delta_duration_minutes, -20);
  assert.equal(deltas[0].delta_buffer_minutes, -20);
  assert.equal(deltas[0].delta_transfer_count, 2);
});
