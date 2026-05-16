export type Airport = {
  iata: string;
  name: string;
};

export type AirportMeta = {
  iata: string;
  name: string;
  city: string;
  country: string;
  latitude: number;
  longitude: number;
};

export type CountryAirports = {
  code: string;
  name: string;
  airports: Airport[];
};

export const COUNTRY_AIRPORTS: CountryAirports[] = [
  {
    code: "ES",
    name: "España",
    airports: [
      { iata: "ALC", name: "Alicante" },
      { iata: "LEI", name: "Almería" },
      { iata: "OVD", name: "Asturias" },
      { iata: "BCN", name: "Barcelona (Todos los aeropuertos)" },
      { iata: "BIO", name: "Bilbao" },
      { iata: "GRX", name: "Granada" },
      { iata: "IBZ", name: "Ibiza" },
      { iata: "MAD", name: "Madrid" },
      { iata: "AGP", name: "Málaga" },
      { iata: "PMI", name: "Palma de Mallorca" },
      { iata: "SVQ", name: "Sevilla" },
      { iata: "VLC", name: "Valencia" },
    ],
  },
  {
    code: "IE",
    name: "Irlanda",
    airports: [
      { iata: "DUB", name: "Dublín" },
      { iata: "ORK", name: "Cork" },
      { iata: "SNN", name: "Shannon" },
    ],
  },
  {
    code: "IT",
    name: "Italia",
    airports: [
      { iata: "BGY", name: "Bérgamo" },
      { iata: "BLQ", name: "Bolonia" },
      { iata: "CIA", name: "Roma Ciampino" },
      { iata: "FCO", name: "Roma Fiumicino" },
      { iata: "MXP", name: "Milán Malpensa" },
      { iata: "NAP", name: "Nápoles" },
      { iata: "PSA", name: "Pisa" },
      { iata: "VCE", name: "Venecia" },
    ],
  },
  {
    code: "FR",
    name: "Francia",
    airports: [
      { iata: "BVA", name: "París Beauvais" },
      { iata: "CDG", name: "París Charles de Gaulle" },
      { iata: "MRS", name: "Marsella" },
      { iata: "NCE", name: "Niza" },
      { iata: "TLS", name: "Toulouse" },
    ],
  },
  {
    code: "DE",
    name: "Alemania",
    airports: [
      { iata: "BER", name: "Berlín" },
      { iata: "CGN", name: "Colonia" },
      { iata: "FRA", name: "Fráncfort" },
      { iata: "HAM", name: "Hamburgo" },
      { iata: "MUC", name: "Múnich" },
    ],
  },
  {
    code: "PT",
    name: "Portugal",
    airports: [
      { iata: "FAO", name: "Faro" },
      { iata: "LIS", name: "Lisboa" },
      { iata: "OPO", name: "Oporto" },
    ],
  },
  {
    code: "GB",
    name: "Reino Unido",
    airports: [
      { iata: "EDI", name: "Edimburgo" },
      { iata: "GLA", name: "Glasgow" },
      { iata: "LON", name: "Londres (Todos los aeropuertos)" },
      { iata: "LCY", name: "Londres City" },
      { iata: "LGW", name: "Londres Gatwick" },
      { iata: "LHR", name: "Londres Heathrow" },
      { iata: "LTN", name: "Londres Luton" },
      { iata: "MAN", name: "Mánchester" },
      { iata: "STN", name: "Londres Stansted" },
    ],
  },
];

const AIRPORT_BY_IATA = new Map<string, Airport>();
const COUNTRY_BY_IATA = new Map<string, CountryAirports>();

for (const country of COUNTRY_AIRPORTS) {
  for (const airport of country.airports) {
    const code = airport.iata.toUpperCase();
    AIRPORT_BY_IATA.set(code, airport);
    COUNTRY_BY_IATA.set(code, country);
  }
}

export const AIRPORT_META: Record<string, AirportMeta> = {
  ALC: { iata: "ALC", name: "Alicante", city: "Alicante", country: "España", latitude: 38.2822, longitude: -0.5581 },
  LEI: { iata: "LEI", name: "Almería", city: "Almería", country: "España", latitude: 36.8439, longitude: -2.3701 },
  OVD: { iata: "OVD", name: "Asturias", city: "Oviedo", country: "España", latitude: 43.5636, longitude: -6.0346 },
  BCN: { iata: "BCN", name: "Barcelona (Todos los aeropuertos)", city: "Barcelona", country: "España", latitude: 41.2974, longitude: 2.0833 },
  BIO: { iata: "BIO", name: "Bilbao", city: "Bilbao", country: "España", latitude: 43.3011, longitude: -2.9106 },
  GRX: { iata: "GRX", name: "Granada", city: "Granada", country: "España", latitude: 37.1887, longitude: -3.7774 },
  IBZ: { iata: "IBZ", name: "Ibiza", city: "Ibiza", country: "España", latitude: 38.8729, longitude: 1.3731 },
  MAD: { iata: "MAD", name: "Madrid", city: "Madrid", country: "España", latitude: 40.4722, longitude: -3.5609 },
  AGP: { iata: "AGP", name: "Málaga", city: "Málaga", country: "España", latitude: 36.6749, longitude: -4.4991 },
  PMI: { iata: "PMI", name: "Palma de Mallorca", city: "Palma", country: "España", latitude: 39.5536, longitude: 2.7278 },
  SVQ: { iata: "SVQ", name: "Sevilla", city: "Sevilla", country: "España", latitude: 37.4179, longitude: -5.8931 },
  VLC: { iata: "VLC", name: "Valencia", city: "Valencia", country: "España", latitude: 39.4893, longitude: -0.4816 },
  DUB: { iata: "DUB", name: "Dublín", city: "Dublín", country: "Irlanda", latitude: 53.4213, longitude: -6.2701 },
  ORK: { iata: "ORK", name: "Cork", city: "Cork", country: "Irlanda", latitude: 51.8413, longitude: -8.4911 },
  SNN: { iata: "SNN", name: "Shannon", city: "Shannon", country: "Irlanda", latitude: 52.7019, longitude: -8.9248 },
  BGY: { iata: "BGY", name: "Bérgamo", city: "Bérgamo", country: "Italia", latitude: 45.6739, longitude: 9.7042 },
  BLQ: { iata: "BLQ", name: "Bolonia", city: "Bolonia", country: "Italia", latitude: 44.5354, longitude: 11.2887 },
  CIA: { iata: "CIA", name: "Roma Ciampino", city: "Roma", country: "Italia", latitude: 41.7999, longitude: 12.5949 },
  FCO: { iata: "FCO", name: "Roma Fiumicino", city: "Roma", country: "Italia", latitude: 41.8003, longitude: 12.2389 },
  MXP: { iata: "MXP", name: "Milán Malpensa", city: "Milán", country: "Italia", latitude: 45.6301, longitude: 8.7281 },
  NAP: { iata: "NAP", name: "Nápoles", city: "Nápoles", country: "Italia", latitude: 40.886, longitude: 14.2908 },
  PSA: { iata: "PSA", name: "Pisa", city: "Pisa", country: "Italia", latitude: 43.6839, longitude: 10.3927 },
  VCE: { iata: "VCE", name: "Venecia", city: "Venecia", country: "Italia", latitude: 45.5053, longitude: 12.3519 },
  BVA: { iata: "BVA", name: "París Beauvais", city: "París", country: "Francia", latitude: 49.4544, longitude: 2.1128 },
  CDG: { iata: "CDG", name: "París Charles de Gaulle", city: "París", country: "Francia", latitude: 49.0097, longitude: 2.5479 },
  MRS: { iata: "MRS", name: "Marsella", city: "Marsella", country: "Francia", latitude: 43.4393, longitude: 5.2214 },
  NCE: { iata: "NCE", name: "Niza", city: "Niza", country: "Francia", latitude: 43.6653, longitude: 7.215 },
  TLS: { iata: "TLS", name: "Toulouse", city: "Toulouse", country: "Francia", latitude: 43.6293, longitude: 1.3638 },
  BER: { iata: "BER", name: "Berlín", city: "Berlín", country: "Alemania", latitude: 52.3667, longitude: 13.5033 },
  CGN: { iata: "CGN", name: "Colonia", city: "Colonia", country: "Alemania", latitude: 50.8659, longitude: 7.1427 },
  FRA: { iata: "FRA", name: "Fráncfort", city: "Fráncfort", country: "Alemania", latitude: 50.0379, longitude: 8.5622 },
  HAM: { iata: "HAM", name: "Hamburgo", city: "Hamburgo", country: "Alemania", latitude: 53.6304, longitude: 9.9882 },
  MUC: { iata: "MUC", name: "Múnich", city: "Múnich", country: "Alemania", latitude: 48.3538, longitude: 11.7861 },
  FAO: { iata: "FAO", name: "Faro", city: "Faro", country: "Portugal", latitude: 37.0144, longitude: -7.9659 },
  LIS: { iata: "LIS", name: "Lisboa", city: "Lisboa", country: "Portugal", latitude: 38.7742, longitude: -9.1342 },
  OPO: { iata: "OPO", name: "Oporto", city: "Oporto", country: "Portugal", latitude: 41.2356, longitude: -8.6781 },
  EDI: { iata: "EDI", name: "Edimburgo", city: "Edimburgo", country: "Reino Unido", latitude: 55.95, longitude: -3.3725 },
  GLA: { iata: "GLA", name: "Glasgow", city: "Glasgow", country: "Reino Unido", latitude: 55.8719, longitude: -4.4331 },
  LON: { iata: "LON", name: "Londres (Todos los aeropuertos)", city: "Londres", country: "Reino Unido", latitude: 51.5074, longitude: -0.1278 },
  LCY: { iata: "LCY", name: "Londres City", city: "Londres", country: "Reino Unido", latitude: 51.5053, longitude: 0.0553 },
  LGW: { iata: "LGW", name: "Londres Gatwick", city: "Londres", country: "Reino Unido", latitude: 51.1537, longitude: -0.1821 },
  LHR: { iata: "LHR", name: "Londres Heathrow", city: "Londres", country: "Reino Unido", latitude: 51.47, longitude: -0.4543 },
  LTN: { iata: "LTN", name: "Londres Luton", city: "Londres", country: "Reino Unido", latitude: 51.8747, longitude: -0.3683 },
  MAN: { iata: "MAN", name: "Mánchester", city: "Mánchester", country: "Reino Unido", latitude: 53.3537, longitude: -2.2749 },
  STN: { iata: "STN", name: "Londres Stansted", city: "Londres", country: "Reino Unido", latitude: 51.885, longitude: 0.235 },
  KUN: { iata: "KUN", name: "Aeropuerto de Kaunas", city: "Kaunas", country: "Lituania", latitude: 54.9633, longitude: 24.0847 },
};

export function findCountryByIata(iata: string): CountryAirports | null {
  const code = iata.toUpperCase();
  return COUNTRY_BY_IATA.get(code) || null;
}

export function findAirportByIata(iata: string): Airport | null {
  const code = iata.toUpperCase();
  return AIRPORT_BY_IATA.get(code) || null;
}

export function getAirportMeta(iata: string): AirportMeta | null {
  const code = iata.toUpperCase();
  return AIRPORT_META[code] || null;
}

import { apiFetchWithStatus } from "@/modules/shared/api";

export async function searchAirportsAsync(query: string): Promise<AirportMeta[]> {
  if (!query || query.trim().length < 2) return [];
  const response = await apiFetchWithStatus<{ items: any[] }>(`/airports/seeds?q=${encodeURIComponent(query)}`);
  if (!response.ok) return [];
  return response.data.items.map(item => ({
    iata: item.iata,
    name: item.name,
    city: item.municipality,
    country: item.country_code,
    latitude: Number(item.latitude),
    longitude: Number(item.longitude),
  }));
}

export async function getAirportMetaAsync(iata: string): Promise<AirportMeta | null> {
  const code = iata.toUpperCase();
  if (AIRPORT_META[code]) {
    return AIRPORT_META[code];
  }
  const results = await searchAirportsAsync(code);
  const match = results.find(r => r.iata === code);
  if (match) {
    AIRPORT_META[code] = match; // cache it
    return match;
  }
  return null;
}



