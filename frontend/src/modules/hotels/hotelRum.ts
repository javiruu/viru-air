export const HOTEL_RUM_CONSENT_KEY = "viru_hotels_rum_consent";
export const HOTEL_RUM_CONSENT_GRANTED = "granted";
export const HOTEL_RUM_EVENT = "hotel_rum_vitals";
export const HOTEL_RUM_SCHEMA_VERSION = 1 as const;

export type HotelRumMetric = "lcp" | "inp" | "cls" | "ttfb";
export type HotelRumRating = "good" | "needs_improvement" | "poor";
export type HotelRumDeviceClass = "mobile" | "tablet" | "desktop";

export type HotelRumMetadata = {
  schema_version: typeof HOTEL_RUM_SCHEMA_VERSION;
  surface: "hoteles";
  metric: HotelRumMetric;
  value_bucket: string;
  rating: HotelRumRating;
  navigation_type: string;
  device_class: HotelRumDeviceClass;
};

const TIMING_BUCKETS = [0, 250, 500, 1000, 2000, 4000, 8000];
const CLS_BUCKETS = [0, 0.1, 0.25, 0.5];

function bucket(value: number, boundaries: readonly number[], suffix: string): string {
  if (!Number.isFinite(value) || value < 0) return "unknown";
  const index = boundaries.findIndex((boundary) => value < boundary);
  if (index === 0) return `<${boundaries[0]}${suffix}`;
  if (index === -1) return `${boundaries[boundaries.length - 1]}+${suffix}`;
  return `${boundaries[index - 1]}-${boundaries[index]}${suffix}`;
}

export function bucketHotelRumValue(metric: HotelRumMetric, value: number): string {
  if (metric === "cls") return bucket(value, CLS_BUCKETS, "");
  return bucket(value, TIMING_BUCKETS, "ms");
}

export function rateHotelRumMetric(metric: HotelRumMetric, value: number): HotelRumRating {
  if (!Number.isFinite(value) || value < 0) return "poor";
  if (metric === "cls") {
    if (value <= 0.1) return "good";
    if (value <= 0.25) return "needs_improvement";
    return "poor";
  }
  if (metric === "lcp") {
    if (value <= 2500) return "good";
    if (value <= 4000) return "needs_improvement";
    return "poor";
  }
  if (metric === "inp") {
    if (value <= 200) return "good";
    if (value <= 500) return "needs_improvement";
    return "poor";
  }
  if (value <= 800) return "good";
  if (value <= 1800) return "needs_improvement";
  return "poor";
}

export function classifyHotelRumDevice(width: number): HotelRumDeviceClass {
  if (width < 768) return "mobile";
  if (width < 1024) return "tablet";
  return "desktop";
}

export function buildHotelRumMetadata(
  metric: HotelRumMetric,
  value: number,
  options: { navigationType?: string; viewportWidth?: number } = {},
): HotelRumMetadata | null {
  if (!Number.isFinite(value) || value < 0) return null;
  return {
    schema_version: HOTEL_RUM_SCHEMA_VERSION,
    surface: "hoteles",
    metric,
    value_bucket: bucketHotelRumValue(metric, value),
    rating: rateHotelRumMetric(metric, value),
    navigation_type: ["navigate", "reload", "back_forward", "prerender"].includes(options.navigationType || "")
      ? options.navigationType || "navigate"
      : "navigate",
    device_class: classifyHotelRumDevice(options.viewportWidth || 0),
  };
}

export function hasHotelRumConsent(storage: Pick<Storage, "getItem"> | null | undefined): boolean {
  return storage?.getItem(HOTEL_RUM_CONSENT_KEY) === HOTEL_RUM_CONSENT_GRANTED;
}

export function shouldFlushHotelRumVisibility(visibilityState: string): boolean {
  return visibilityState === "hidden";
}
