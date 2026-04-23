export const QUICK_SEARCH_RADIUS_MIN = 10;
export const QUICK_SEARCH_RADIUS_MAX = 500;
export const QUICK_SEARCH_RADIUS_DEFAULT = 150;

export function clampQuickSearchRadius(value: number, fallback = QUICK_SEARCH_RADIUS_DEFAULT): number {
  if (!Number.isFinite(value)) return fallback;
  return Math.min(QUICK_SEARCH_RADIUS_MAX, Math.max(QUICK_SEARCH_RADIUS_MIN, Math.trunc(value)));
}

export function parseQuickSearchIataTokens(raw: string): string[] {
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

export function mergeQuickSearchIataTokens(current: string[], raw: string): string[] {
  const next = [...current];
  for (const iata of parseQuickSearchIataTokens(raw)) {
    if (!next.includes(iata)) next.push(iata);
  }
  return next;
}
