import { getAirportMeta } from "@/modules/shared/airports";
import type { WeatherDay, WeatherReport } from "@/modules/quick-search/types";
import type { QuickSearchCopyKey } from "@/modules/shared/quickSearchCopy";

// ── Weather code → human label ───────────────────────────────────────

export function weatherLabel(code: number): string {
  if (code === 0) return "Clear";
  if (code === 1 || code === 2) return "Mostly clear";
  if (code === 3) return "Cloudy";
  if (code >= 45 && code <= 48) return "Fog";
  if (code >= 51 && code <= 57) return "Drizzle";
  if (code >= 61 && code <= 67) return "Rain";
  if (code >= 71 && code <= 77) return "Snow";
  if (code >= 80 && code <= 82) return "Showers";
  if (code >= 95) return "Storm";
  return "Variable";
}

/**
 * Localized weather label — resolves the label using a provided `t` function
 * from quickSearchCopy. Used inside `fetchWeather` so the component's locale
 * is respected.
 */
export function weatherLabelLocalized(code: number, t: (key: QuickSearchCopyKey) => string): string {
  if (code === 0) return t("weatherClear");
  if (code === 1 || code === 2) return t("weatherMostlyClear");
  if (code === 3) return t("weatherCloudy");
  if (code >= 45 && code <= 48) return t("weatherFog");
  if (code >= 51 && code <= 57) return t("weatherDrizzle");
  if (code >= 61 && code <= 67) return t("weatherRain");
  if (code >= 71 && code <= 77) return t("weatherSnow");
  if (code >= 80 && code <= 82) return t("weatherShowers");
  if (code >= 95) return t("weatherStorm");
  return t("weatherVariable");
}

// ── Fetch error ──────────────────────────────────────────────────────

export type WeatherFetchErrorCode = "out_of_range" | "provider_error";

export class WeatherFetchError extends Error {
  code: WeatherFetchErrorCode;

  constructor(code: WeatherFetchErrorCode, message: string) {
    super(message);
    this.code = code;
  }
}

// ── Range validation ─────────────────────────────────────────────────

export function isWeatherRangeSupported(start: string, end: string): boolean {
  const startDate = new Date(`${start}T00:00:00Z`);
  const endDate = new Date(`${end}T00:00:00Z`);
  if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) return false;

  const today = new Date();
  const todayUtc = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate()));
  const maxDate = new Date(todayUtc);
  maxDate.setUTCDate(maxDate.getUTCDate() + 14);

  return startDate >= todayUtc && endDate <= maxDate;
}

// ── Fetch weather from Open-Meteo ────────────────────────────────────

export async function fetchWeather(
  iata: string,
  start: string,
  end: string,
  t: (key: QuickSearchCopyKey) => string,
): Promise<WeatherReport | null> {
  const meta = getAirportMeta(iata);
  if (!meta) return null;

  if (!isWeatherRangeSupported(start, end)) {
    throw new WeatherFetchError("out_of_range", "weather_out_of_range");
  }

  const params = new URLSearchParams({
    latitude: String(meta.latitude),
    longitude: String(meta.longitude),
    daily: "weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
    timezone: "auto",
    start_date: start,
    end_date: end,
  });
  const res = await fetch(`https://api.open-meteo.com/v1/forecast?${params.toString()}`);
  if (!res.ok) {
    const reasonRaw = await res.text().catch(() => "");
    const isRange400 = res.status === 400 && reasonRaw.toLowerCase().includes("out of allowed range");
    if (isRange400) {
      throw new WeatherFetchError("out_of_range", "weather_out_of_range");
    }
    throw new WeatherFetchError("provider_error", `weather_provider_${res.status}`);
  }
  const data = await res.json();
  const times: string[] = data?.daily?.time || [];
  const maxTemps: number[] = data?.daily?.temperature_2m_max || [];
  const minTemps: number[] = data?.daily?.temperature_2m_min || [];
  const precip: number[] = data?.daily?.precipitation_probability_max || [];
  const codes: number[] = data?.daily?.weathercode || [];
  const days: WeatherDay[] = times.map((time: string, idx: number) => ({
    date: time,
    tempMax: Number(maxTemps[idx] ?? 0),
    tempMin: Number(minTemps[idx] ?? 0),
    precipProb: Number.isFinite(precip[idx]) ? precip[idx] : null,
    description: weatherLabelLocalized(Number(codes[idx] ?? 0), t),
  }));
  return {
    iata: meta.iata,
    name: meta.name,
    city: meta.city,
    country: meta.country,
    days,
  };
}
