export type QuickSearchAdditionalAirport = {
  readonly id: string;
  readonly value: string;
};

export function getAdditionalAirportFocusTarget(
  entries: readonly QuickSearchAdditionalAirport[],
  removedIndex: number,
): string | null {
  return entries[removedIndex + 1]?.id ?? entries[removedIndex - 1]?.id ?? null;
}

export function buildRouteSeedList(
  primary: string | readonly string[],
  additional: readonly string[],
  knownAirports: ReadonlySet<string>,
): string[] {
  const primaryValues = Array.isArray(primary) ? primary : [primary];
  const normalizedPrimary = primaryValues
    .map((value) => value.trim().toUpperCase())
    .filter(Boolean);
  const normalizedAdditional = additional
    .map((value) => value.trim().toUpperCase())
    .filter((value) => value.length === 3 && knownAirports.has(value));

  return Array.from(new Set([...normalizedPrimary, ...normalizedAdditional]));
}
