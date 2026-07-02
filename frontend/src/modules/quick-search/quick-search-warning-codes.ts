export const QUICK_SEARCH_PROVIDER_TOTAL_OUTAGE_WARNING_CODES = [
  "provider_total_outage",
  "ryanair_provider_unavailable_total",
  "vueling_provider_unavailable_total",
  "wizzair_provider_unavailable_total",
  "easyjet_provider_unavailable_total",
  "duffel_provider_unavailable_total",
] as const;

export const QUICK_SEARCH_PROVIDER_ERROR_WARNING_CODES = [
  "ryanair_availability_failed",
  "ryanair_fares_failed",
] as const;

export const QUICK_SEARCH_PROVIDER_PARTIAL_WARNING_CODES = [
  "ryanair_unavailable_partial",
  "ryanair_availability_failed_partial",
  "ryanair_fares_failed_partial",
  "provider_timeout_partial",
  "provider_error_partial",
  "provider_partial_results_served",
] as const;

export const QUICK_SEARCH_PROVIDER_PARTIAL_INLINE_WARNING_CODES = [
  "ryanair_unavailable_partial",
  "ryanair_unavailable_parcial",
  "ryanair_availability_failed_partial",
  "ryanair_fares_failed_partial",
] as const;
