import { COUNTRY_AIRPORTS } from "@/modules/shared/airports";

export type AirportSuggestion = {
  iata: string;
  name: string;
  countryCode: string;
  countryName: string;
};

const AIRPORT_SUGGESTIONS: AirportSuggestion[] = COUNTRY_AIRPORTS.flatMap((country) =>
  country.airports.map((airport) => ({
    iata: airport.iata,
    name: airport.name,
    countryCode: country.code,
    countryName: country.name,
  })),
);

export function getAirportSuggestions(query: string, limit = 8): AirportSuggestion[] {
  const q = query.trim().toLowerCase();
  if (!q) return AIRPORT_SUGGESTIONS.slice(0, limit);
  const startsWithCode = AIRPORT_SUGGESTIONS.filter((airport) =>
    airport.iata.toLowerCase().startsWith(q),
  );
  const startsWithName = AIRPORT_SUGGESTIONS.filter((airport) =>
    airport.name.toLowerCase().startsWith(q),
  );
  const contains = AIRPORT_SUGGESTIONS.filter((airport) => {
    const haystack = `${airport.iata} ${airport.name} ${airport.countryName}`.toLowerCase();
    return haystack.includes(q);
  });
  const seen = new Set<string>();
  const merged = [...startsWithCode, ...startsWithName, ...contains].filter((airport) => {
    if (seen.has(airport.iata)) return false;
    seen.add(airport.iata);
    return true;
  });
  return merged.slice(0, limit);
}

export function buildDateRange(start: string, end: string): string[] {
  if (!start) return [];
  const parseIsoDay = (value: string): Date | null => {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
    if (!match) return null;
    const year = Number(match[1]);
    const month = Number(match[2]) - 1;
    const day = Number(match[3]);
    const parsed = new Date(Date.UTC(year, month, day));
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  };
  const formatIsoDay = (value: Date): string => {
    const y = value.getUTCFullYear();
    const m = String(value.getUTCMonth() + 1).padStart(2, "0");
    const d = String(value.getUTCDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
  };

  const startDate = parseIsoDay(start);
  const endDate = parseIsoDay(end || start);
  if (!startDate) return [];
  if (!endDate) return [start];

  const from = startDate <= endDate ? startDate : endDate;
  const to = startDate <= endDate ? endDate : startDate;
  const out: string[] = [];
  const cursor = new Date(from);
  while (cursor <= to) {
    out.push(formatIsoDay(cursor));
    cursor.setUTCDate(cursor.getUTCDate() + 1);
  }
  return out;
}
