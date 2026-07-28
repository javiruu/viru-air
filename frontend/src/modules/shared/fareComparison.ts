export const FARE_EXTRA_KINDS = [
  "cabin_bag_10kg",
  "checked_bag_20kg",
  "insurance",
  "fast_track",
  "priority_boarding",
  "seat_selection",
  "flexible_ticket",
] as const;

export type FareExtraKind = (typeof FARE_EXTRA_KINDS)[number];

export type FareComparisonExtra = {
  readonly kind: FareExtraKind;
  readonly selected: boolean;
  readonly amount_per_person: number | null;
};

export type FareComparisonProfile = {
  readonly travelers: number;
  readonly extras: readonly FareComparisonExtra[];
};

export type ComparableFare = {
  readonly base_total: number;
  readonly extras_total: number;
  readonly comparable_total: number | null;
  readonly is_complete: boolean;
  readonly missing_kinds: readonly FareExtraKind[];
};

export function createEmptyFareComparisonProfile(travelers: number): FareComparisonProfile {
  return {
    travelers: Math.max(1, Math.min(9, Math.trunc(travelers))),
    extras: FARE_EXTRA_KINDS.map((kind) => ({
      kind,
      selected: false,
      amount_per_person: null,
    })),
  };
}

export function calculateComparableFare(
  baseTotal: number,
  profile: FareComparisonProfile,
): ComparableFare {
  const selected = profile.extras.filter((extra) => extra.selected);
  const missingKinds = selected
    .filter((extra) => extra.amount_per_person === null)
    .map((extra) => extra.kind);
  const extrasTotal = selected.reduce(
    (total, extra) => total + (extra.amount_per_person ?? 0) * profile.travelers,
    0,
  );

  return {
    base_total: baseTotal,
    extras_total: extrasTotal,
    comparable_total: missingKinds.length === 0 ? baseTotal + extrasTotal : null,
    is_complete: missingKinds.length === 0,
    missing_kinds: missingKinds,
  };
}
