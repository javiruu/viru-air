import type { AirportIataEntry } from "@/modules/quick-search/types";
import { getTranslatedCityName, matchesCityTranslation } from "@/modules/shared/cityTranslations";

// ── Text normalization ───────────────────────────────────────────────

export function normalizeText(text: string): string {
  if (!text) return "";
  return text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

// ── Build suggestions from airport seed data ─────────────────────────

export function buildAirportSuggestions(
  airports: AirportIataEntry[],
  value: string,
  limit = 6,
  locale = "en",
) {
  const q = normalizeText(value.trim());
  if (!q) return [];
  const out: Array<{ iata: string; name: string }> = [];
  const seen = new Set<string>();

  // Pass 1: IATA prefix match
  for (const airport of airports) {
    if (out.length >= limit) break;
    const originalName = airport.municipality || airport.name;
    const nIata = normalizeText(airport.iata);
    if (nIata.startsWith(q) || matchesCityTranslation(originalName, value)) {
      out.push({
        iata: airport.iata,
        name: getTranslatedCityName(originalName, locale),
      });
      seen.add(airport.iata);
    }
  }

  // Pass 2: Full name match
  if (out.length < limit) {
    for (const airport of airports) {
      if (out.length >= limit) break;
      if (seen.has(airport.iata)) continue;
      const originalName = airport.municipality || airport.name;
      const hay = normalizeText(`${airport.name} ${airport.municipality}`);
      if (hay.includes(q) || matchesCityTranslation(originalName, value)) {
        out.push({
          iata: airport.iata,
          name: getTranslatedCityName(originalName, locale),
        });
        seen.add(airport.iata);
      }
    }
  }

  return out;
}

// ── Merge recent + API suggestions ───────────────────────────────────

export function mergeAirportSuggestions(
  recentSuggestions: Array<{ iata: string; name: string }>,
  apiSuggestions: Array<{ iata: string; name: string }>,
  limit = 6,
) {
  const out: Array<{ iata: string; name: string }> = [];
  const seen = new Set<string>();

  for (const suggestion of [...recentSuggestions, ...apiSuggestions]) {
    const key = suggestion.iata.trim().toUpperCase();
    if (!key || seen.has(key)) continue;
    seen.add(key);
    out.push({ iata: key, name: suggestion.name });
    if (out.length >= limit) break;
  }

  return out;
}
