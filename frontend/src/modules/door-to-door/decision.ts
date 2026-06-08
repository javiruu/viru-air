import type { DecisionBadge, DecisionReason, DoorToDoorOption, OptionDeltaSummary } from "@/modules/door-to-door/types";

export function getDecisionBadges(options: DoorToDoorOption[]): Record<string, DecisionBadge[]> {
  if (options.length === 0) return {};
  const byDuration = [...options].sort((a, b) => compareNumber(a.total_duration_minutes, b.total_duration_minutes, a.id, b.id));
  const byBuffer = [...options].sort((a, b) => compareNumber(a.airport_buffer_minutes, b.airport_buffer_minutes, a.id, b.id, true));
  const byTransfers = [...options].sort((a, b) => compareNumber(a.transfer_count, b.transfer_count, a.id, b.id));
  const byPrice = [...options]
    .filter((option) => option.total_price_min != null)
    .sort((a, b) => compareNumber(a.total_price_min, b.total_price_min, a.id, b.id));

  const badges: Record<string, DecisionBadge[]> = {};
  for (const option of options) badges[option.id] = [];

  addBadge(badges, byDuration[0], { kind: "fastest", label: "fastest" });
  addBadge(badges, byBuffer[0], { kind: "longest_buffer", label: "longest_buffer" });
  addBadge(badges, byTransfers[0], { kind: "fewest_changes", label: "fewest_changes" });
  if (byPrice[0]) addBadge(badges, byPrice[0], { kind: "best_estimated_price", label: "best_estimated_price" });

  return badges;
}

export function getDecisionReasons(recommended: DoorToDoorOption, options: DoorToDoorOption[]): DecisionReason[] {
  const peers = options.filter((item) => item.id !== recommended.id);
  const reasons: DecisionReason[] = [];

  if (recommended.total_price_min != null && peers.some((item) => item.total_price_min != null)) {
    const bestOther = minNumber(peers.map((item) => item.total_price_min));
    if (bestOther != null && recommended.total_price_min <= bestOther) {
      reasons.push({ kind: "price", label: "price" });
    }
  }

  if (recommended.airport_buffer_minutes != null && peers.some((item) => item.airport_buffer_minutes != null)) {
    const bestBuffer = maxNumber(peers.map((item) => item.airport_buffer_minutes));
    if (bestBuffer != null && recommended.airport_buffer_minutes >= bestBuffer) {
      reasons.push({ kind: "buffer", label: "buffer" });
    }
  }

  const bestTransfers = minNumber(peers.map((item) => item.transfer_count));
  if (bestTransfers != null && recommended.transfer_count <= bestTransfers) {
    reasons.push({ kind: "transfers", label: "transfers" });
  }

  if (recommended.total_duration_minutes != null && peers.some((item) => item.total_duration_minutes != null)) {
    const bestDuration = minNumber(peers.map((item) => item.total_duration_minutes));
    if (bestDuration != null && recommended.total_duration_minutes <= bestDuration) {
      reasons.push({ kind: "duration", label: "duration" });
    }
  }

  if (hasUncertainSources(recommended)) {
    reasons.push({ kind: "confidence", label: "confidence" });
  }

  return reasons.slice(0, 3);
}

export function getAlternativeDeltas(recommended: DoorToDoorOption, options: DoorToDoorOption[]): OptionDeltaSummary[] {
  return options
    .filter((item) => item.id !== recommended.id)
    .sort((a, b) => compareNumber(a.score, b.score, a.id, b.id, true))
    .slice(0, 2)
    .map((option) => ({
      option_id: option.id,
      option_label: option.label,
      delta_price: diff(option.total_price_min, recommended.total_price_min),
      delta_duration_minutes: diff(option.total_duration_minutes, recommended.total_duration_minutes),
      delta_buffer_minutes: diff(option.airport_buffer_minutes, recommended.airport_buffer_minutes),
      delta_transfer_count: diff(option.transfer_count, recommended.transfer_count),
    }));
}

export function hasUncertainSources(option: DoorToDoorOption): boolean {
  return option.sources.some(
    (source) =>
      source.source_type === "deeplink" ||
      source.source_type === "estimate" ||
      source.source_type === "mock" ||
      source.confidence === "estimated" ||
      source.confidence === "deeplink" ||
      source.confidence === "unavailable",
  );
}

function addBadge(store: Record<string, DecisionBadge[]>, option: DoorToDoorOption | undefined, badge: DecisionBadge) {
  if (!option) return;
  if (!store[option.id]) store[option.id] = [];
  if (!store[option.id].some((item) => item.kind === badge.kind)) store[option.id].push(badge);
}

function diff(value: number | null | undefined, baseline: number | null | undefined): number | null {
  if (value == null || baseline == null) return null;
  return value - baseline;
}

function compareNumber(
  a: number | null | undefined,
  b: number | null | undefined,
  aId: string,
  bId: string,
  desc = false,
): number {
  if (a == null && b == null) return aId.localeCompare(bId);
  if (a == null) return 1;
  if (b == null) return -1;
  if (a === b) return aId.localeCompare(bId);
  return desc ? b - a : a - b;
}

function minNumber(values: Array<number | null | undefined>): number | null {
  const filtered = values.filter((value): value is number => value != null);
  if (filtered.length === 0) return null;
  return Math.min(...filtered);
}

function maxNumber(values: Array<number | null | undefined>): number | null {
  const filtered = values.filter((value): value is number => value != null);
  if (filtered.length === 0) return null;
  return Math.max(...filtered);
}
