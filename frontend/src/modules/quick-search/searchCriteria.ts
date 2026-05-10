type NumericParseOptions = {
  allowFloat?: boolean;
  min?: number;
  max?: number;
};

export function parseNumericInput(raw: string, options: NumericParseOptions = {}): number | null {
  const value = raw.trim();
  if (!value) return null;

  const normalized = value.replace(",", ".");
  const pattern = options.allowFloat ? /^\d+(\.\d+)?$/ : /^\d+$/;
  if (!pattern.test(normalized)) return null;

  const parsed = Number(normalized);
  if (!Number.isFinite(parsed)) return null;
  if (!options.allowFloat && !Number.isInteger(parsed)) return null;
  if (options.min !== undefined && parsed < options.min) return null;
  if (options.max !== undefined && parsed > options.max) return null;
  return parsed;
}

export type CriteriaSignatureInput = {
  origin: string;
  destination: string;
  originCountryCode: string | null;
  destinationCountryCode: string | null;
  travelDate: string;
  returnDate: string;
  isReturn: boolean;
  adults: number;
  daysBefore: number;
  daysAfter: number;
  applyFlexReturn: boolean;
  includeStops: boolean;
  maxStops: number;
  durationMax: string;
  riskFilter: string;
  radiusKm: number;
  includeNearbyOrigins: boolean;
  includeNearbyDestinations: boolean;
  excludeOrigins: string[];
  excludeDestinations: string[];
  excludeOriginInput: string;
  excludeDestinationInput: string;
  strictFilters: boolean;
  priceMin: string;
  priceMax: string;
  departAfter: string;
  departBefore: string;
  bufferMin: string;
};

function parseIataTokens(raw: string): string[] {
  const seen = new Set<string>();
  return raw
    .toUpperCase()
    .split(/[,\s]+/)
    .map((item) => item.trim())
    .filter((item) => /^[A-Z]{3}$/.test(item))
    .filter((item) => {
      if (seen.has(item)) return false;
      seen.add(item);
      return true;
    });
}

function mergeIataTokens(current: string[], raw: string): string[] {
  const next = [...current];
  for (const iata of parseIataTokens(raw)) {
    if (!next.includes(iata)) next.push(iata);
  }
  return next;
}

// NOTE: This signature defines "applied vs edited" search criteria comparisons.
// Keep fields in sync with submit payload-relevant UI inputs.
export function buildCriteriaSignature(input: CriteriaSignatureInput): string {
  const normalizedExcludeOrigins = mergeIataTokens(input.excludeOrigins, input.excludeOriginInput);
  const normalizedExcludeDestinations = mergeIataTokens(input.excludeDestinations, input.excludeDestinationInput);
  return JSON.stringify({
    ...input,
    excludeOrigins: normalizedExcludeOrigins,
    excludeDestinations: normalizedExcludeDestinations,
    // The exclusion textboxes are transient draft UI; compare the applied semantic state.
    excludeOriginInput: "",
    excludeDestinationInput: "",
  });
}
