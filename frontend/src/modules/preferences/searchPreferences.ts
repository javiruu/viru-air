import { Pref } from "@/modules/quick-search/types";

export type SearchPreferenceErrors = Partial<
  Record<
    "default_radius_km"
    | "avoid_departure_before"
    | "depart_before_default"
    | "calendar_hint_guideline_low_max_default"
    | "calendar_hint_guideline_mid_max_default",
    string
  >
>;

export const SEARCH_PREF_MIN_RADIUS_KM = 0;
export const SEARCH_PREF_MAX_RADIUS_KM = 500;
export const SEARCH_PREF_QUICK_TIME_CHIPS = ["06:00", "07:00", "08:30", "10:00"] as const;
export const SEARCH_PREF_LATE_TIME_CHIPS = ["18:00", "20:00", "22:00"] as const;
export const SEARCH_PREF_DEFAULT_TIME_PLACEHOLDER = "08:30";
export const SEARCH_PREF_LATE_TIME_PLACEHOLDER = "22:00";

export function isValidHour(value: string) {
  return /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(value);
}

export function validateSearchPreferences(
  nextPref: Pref,
  t: (key: string, params?: Record<string, string | number>) => string,
): SearchPreferenceErrors {
  const nextErrors: SearchPreferenceErrors = {};

  if (
    Number.isNaN(nextPref.default_radius_km) ||
    nextPref.default_radius_km < SEARCH_PREF_MIN_RADIUS_KM ||
    nextPref.default_radius_km > SEARCH_PREF_MAX_RADIUS_KM
  ) {
    nextErrors.default_radius_km = t("preferences.search.rangeError", {
      min: SEARCH_PREF_MIN_RADIUS_KM,
      max: SEARCH_PREF_MAX_RADIUS_KM,
    });
  }

  if (
    nextPref.avoid_departure_before &&
    nextPref.avoid_departure_before.trim() &&
    !isValidHour(nextPref.avoid_departure_before)
  ) {
    nextErrors.avoid_departure_before = t("preferences.search.timeError");
  }

  if (
    nextPref.depart_before_default &&
    nextPref.depart_before_default.trim() &&
    !isValidHour(nextPref.depart_before_default)
  ) {
    nextErrors.depart_before_default = t("preferences.search.timeError");
  }

  if (Number.isNaN(nextPref.calendar_hint_guideline_low_max_default) || nextPref.calendar_hint_guideline_low_max_default < 0) {
    nextErrors.calendar_hint_guideline_low_max_default = t("preferences.search.guidelineLowError");
  }

  if (
    Number.isNaN(nextPref.calendar_hint_guideline_mid_max_default)
    || nextPref.calendar_hint_guideline_mid_max_default <= nextPref.calendar_hint_guideline_low_max_default
  ) {
    nextErrors.calendar_hint_guideline_mid_max_default = t("preferences.search.guidelineMidError");
  }

  return nextErrors;
}

export function buildSearchPreferenceSummary(pref: Pref, t: (key: string) => string) {
  const nearbyEnabled = pref.include_nearby_origins_default || pref.include_nearby_destinations_default;
  const coverage = nearbyEnabled ? t("preferences.search.summaryCoverageRegional") : t("preferences.search.summaryCoverageDirect");
  const timing = pref.avoid_departure_before || pref.depart_before_default
    ? t("preferences.search.summaryTimingWindow")
    : t("preferences.search.summaryTimingOpen");
  const strict = pref.strict_filters_default
    ? t("preferences.search.summaryStrictTight")
    : t("preferences.search.summaryStrictFlexible");

  return {
    title: nearbyEnabled
      ? t("preferences.search.summaryTitleRegional")
      : t("preferences.search.summaryTitleDirect"),
    body: [coverage, strict, timing].join(" | "),
    chips: [
      pref.include_stops_default ? t("preferences.search.summaryStopsOn") : t("preferences.search.summaryStopsOff"),
      pref.strict_filters_default ? t("preferences.search.summaryStrictTight") : t("preferences.search.summaryStrictFlexible"),
      `${pref.default_radius_km} km`,
    ],
  };
}
