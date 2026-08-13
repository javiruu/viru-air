import { apiFetchWithStatus } from "@/modules/shared/api";

import type {
  HotelAlertEventOut,
  HotelAlertRuleOut,
  HotelAreaResolveOut,
  HotelAreaSearchResultOut,
  HotelAreaSearchV2Out,
  HotelCompSetDetailOut,
  HotelCompSetOut,
  HotelDetailOut,
  HotelIngestOut,
  HotelNearbySuggestionOut,
  HotelParityOut,
  HotelRateOut,
  HotelSavedSearchOut,
  HotelSearchOut,
  HotelTrackedOfferOut,
  HotelTrackedOfferV2CreateOut,
  HotelTrackedOfferHistoryV2Out,
  HotelTrackedOfferV2LifecycleOut,
  HotelTrackedOfferV2Out,
  HotelTrackedOffersV2Out,
  HotelWatchlistItemOut,
  HotelsApiError,
} from "./types";

export class HotelsRequestError extends Error implements HotelsApiError {
  status: number;
  correlation_id?: string;
  client_event_id?: string;

  constructor(status: number, message: string, context?: { correlation_id?: string; client_event_id?: string }) {
    super(message);
    this.name = "HotelsRequestError";
    this.status = status;
    this.correlation_id = context?.correlation_id;
    this.client_event_id = context?.client_event_id;
  }
}

function queryString(params: Record<string, string | number | boolean | null | undefined>): string {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === null || value === undefined || value === "") return;
    sp.set(key, String(value));
  });
  const raw = sp.toString();
  return raw ? `?${raw}` : "";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const result = await apiFetchWithStatus<T>(path, init);
  if (!result.ok) {
    throw new HotelsRequestError(result.status, result.error.message, {
      correlation_id: result.error.correlation_id,
      client_event_id: result.error.client_event_id,
    });
  }
  return result.data;
}

export async function ingestHotelsMock(): Promise<HotelIngestOut> {
  return request<HotelIngestOut>("/hotels/ingest/mock", { method: "POST" });
}

export async function searchHotels(
  params: {
    q?: string;
    city?: string;
    country_code?: string;
    limit?: number;
    offset?: number;
  },
  signal?: AbortSignal,
  intentId?: string,
): Promise<HotelSearchOut[]> {
  return request<HotelSearchOut[]>(`/hotels/search${queryString(params)}`, {
    signal,
    headers: intentId ? { "x-client-event-id": intentId } : undefined,
  });
}

export async function getHotelDetail(
  hotelId: string,
  signal?: AbortSignal,
  intentId?: string,
): Promise<HotelDetailOut> {
  return request<HotelDetailOut>(`/hotels/${hotelId}`, {
    signal,
    headers: intentId ? { "x-client-event-id": intentId } : undefined,
  });
}

export async function getHotelRates(
  hotelId: string,
  params?: { check_in?: string; check_out?: string },
  signal?: AbortSignal,
  intentId?: string,
): Promise<HotelRateOut[]> {
  return request<HotelRateOut[]>(`/hotels/${hotelId}/rates${queryString(params || {})}`, {
    signal,
    headers: intentId ? { "x-client-event-id": intentId } : undefined,
  });
}

export async function getHotelParity(
  hotelId: string,
  signal?: AbortSignal,
  intentId?: string,
): Promise<HotelParityOut[]> {
  return request<HotelParityOut[]>(`/hotels/${hotelId}/parity`, {
    signal,
    headers: intentId ? { "x-client-event-id": intentId } : undefined,
  });
}

export async function listSavedHotelSearches(): Promise<HotelSavedSearchOut[]> {
  return request<HotelSavedSearchOut[]>("/hotels/saved-searches");
}

export async function createSavedHotelSearch(payload: {
  schema_version?: "hotel-search-v1";
  query: Record<string, unknown>;
  label?: string | null;
}): Promise<HotelSavedSearchOut> {
  return request<HotelSavedSearchOut>("/hotels/saved-searches", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateSavedHotelSearch(
  searchId: string,
  payload: { label?: string | null; status?: "active" | "paused" },
): Promise<HotelSavedSearchOut> {
  return request<HotelSavedSearchOut>(`/hotels/saved-searches/${searchId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteSavedHotelSearch(searchId: string): Promise<void> {
  await request<{ status: string }>(`/hotels/saved-searches/${searchId}`, { method: "DELETE" });
}

export async function listHotelWatchlist(): Promise<HotelWatchlistItemOut[]> {
  return request<HotelWatchlistItemOut[]>("/hotels/watchlist");
}

export async function createHotelWatchlistItem(payload: { hotel_id: string; label?: string | null }): Promise<HotelWatchlistItemOut> {
  return request<HotelWatchlistItemOut>("/hotels/watchlist", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteHotelWatchlistItem(itemId: string): Promise<void> {
  await request<{ status: string }>(`/hotels/watchlist/${itemId}`, { method: "DELETE" });
}

export async function listHotelAlertRules(): Promise<HotelAlertRuleOut[]> {
  return request<HotelAlertRuleOut[]>("/hotels/alert-rules");
}

export async function createHotelAlertRule(payload: {
  hotel_id: string;
  tracked_offer_id?: string | null;
  rule_type: string;
  threshold_amount?: number | null;
  threshold_percent?: number | null;
  compare_against?: string;
  cooldown_minutes?: number;
  is_active?: boolean;
}): Promise<HotelAlertRuleOut> {
  return request<HotelAlertRuleOut>("/hotels/alert-rules", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateHotelAlertRule(
  ruleId: string,
  payload: {
    rule_type?: string;
    threshold_amount?: number | null;
    threshold_percent?: number | null;
    compare_against?: string;
    is_active?: boolean;
  },
): Promise<HotelAlertRuleOut> {
  return request<HotelAlertRuleOut>(`/hotels/alert-rules/${ruleId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteHotelAlertRule(ruleId: string): Promise<void> {
  await request<{ status: string }>(`/hotels/alert-rules/${ruleId}`, { method: "DELETE" });
}

export async function listHotelAlertEvents(params?: { hotel_id?: string; limit?: number; offset?: number }): Promise<HotelAlertEventOut[]> {
  return request<HotelAlertEventOut[]>(`/hotels/alert-events${queryString(params || {})}`);
}

export async function listHotelCompSets(): Promise<HotelCompSetOut[]> {
  return request<HotelCompSetOut[]>("/hotels/comp-sets");
}

export async function createHotelCompSet(payload: { name: string; anchor_hotel_id: string }): Promise<HotelCompSetOut> {
  return request<HotelCompSetOut>("/hotels/comp-sets", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getHotelCompSetDetail(compSetId: string): Promise<HotelCompSetDetailOut> {
  return request<HotelCompSetDetailOut>(`/hotels/comp-sets/${compSetId}`);
}

export async function addHotelCompSetMember(compSetId: string, payload: { hotel_id: string }) {
  return request<{ id: string; comp_set_id: string; hotel_id: string }>(`/hotels/comp-sets/${compSetId}/members`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteHotelCompSetMember(compSetId: string, memberId: string): Promise<void> {
  await request<{ status: string }>(`/hotels/comp-sets/${compSetId}/members/${memberId}`, { method: "DELETE" });
}

export async function deleteHotelCompSet(compSetId: string): Promise<void> {
  await request<{ status: string }>(`/hotels/comp-sets/${compSetId}`, { method: "DELETE" });
}

export async function getHotelNearbySuggestions(
  compSetId: string,
  params?: { radius_km?: number; limit?: number },
): Promise<HotelNearbySuggestionOut[]> {
  return request<HotelNearbySuggestionOut[]>(`/hotels/comp-sets/${compSetId}/nearby-suggestions${queryString(params || {})}`);
}

export async function areaResolve(q: string, signal?: AbortSignal): Promise<HotelAreaResolveOut> {
  return request<HotelAreaResolveOut>(`/hotels/area-resolve${queryString({ q })}`, { signal });
}

export async function areaSearch(params: {
  latitude: number;
  longitude: number;
  radius_km?: number;
  check_in: string;
  check_out: string;
  guests?: number;
  currency?: string;
  min_stars?: number;
  max_price?: number;
  sort?: string;
  use_provider?: boolean;
},
  signal?: AbortSignal,
  intentId?: string,
): Promise<HotelAreaSearchResultOut[]> {
  return request<HotelAreaSearchResultOut[]>(`/hotels/area-search${queryString(params)}`, {
    signal,
    headers: intentId ? { "x-client-event-id": intentId } : undefined,
  });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isAreaSearchV2Result(value: unknown): boolean {
  if (!isRecord(value) || !isRecord(value.price) || !isRecord(value.stay_context)) return false;
  return typeof value.hotel_id === "string"
    && typeof value.canonical_name === "string"
    && typeof value.city === "string"
    && typeof value.country_code === "string"
    && typeof value.distance_km === "number"
    && (typeof value.price.amount === "number" || value.price.amount === null)
    && typeof value.price.currency === "string"
    && typeof value.stay_context.check_in === "string"
    && typeof value.stay_context.check_out === "string"
    && typeof value.stay_context.guests === "number";
}

function isCapabilityState(value: unknown): boolean {
  return value === "supported"
    || value === "supported_with_caveat"
    || value === "partial"
    || value === "planned"
    || value === "unavailable";
}

function isWarning(value: unknown): boolean {
  return isRecord(value)
    && typeof value.code === "string"
    && (value.severity === "info" || value.severity === "warning" || value.severity === "error")
    && typeof value.message_key === "string"
    && (typeof value.provider === "string" || value.provider === null)
    && (value.scope === "collection" || value.scope === "result" || value.scope === "field")
    && Array.isArray(value.result_ids)
    && value.result_ids.every((resultId) => typeof resultId === "string")
    && isRecord(value.meta);
}

function isTrackingPrice(value: unknown): boolean {
  return isRecord(value)
    && (typeof value.amount === "number" || value.amount === null)
    && typeof value.currency === "string"
    && (value.basis === "total_stay" || value.basis === "per_night" || value.basis === "unknown")
    && (value.status === "observed" || value.status === "unavailable" || value.status === "not_comparable" || value.status === "stale")
    && (typeof value.observed_at === "string" || value.observed_at === null);
}

function isTrackingFreshness(value: unknown): boolean {
  return isRecord(value)
    && (value.state === "fresh" || value.state === "recent" || value.state === "cached" || value.state === "historical" || value.state === "stale" || value.state === "expired" || value.state === "unknown")
    && (typeof value.observed_at === "string" || value.observed_at === null)
    && (typeof value.age_seconds === "number" || value.age_seconds === null)
    && (typeof value.expires_at === "string" || value.expires_at === null)
    && typeof value.mixed === "boolean"
    && typeof value.requires_revalidation === "boolean"
    && (typeof value.policy_version === "string" || value.policy_version === null)
    && (value.provenance_kind === "provider_observed" || value.provenance_kind === "provider_revalidated" || value.provenance_kind === "cache_current" || value.provenance_kind === "historical_snapshot" || value.provenance_kind === "fixture_demo" || value.provenance_kind === "derived" || value.provenance_kind === "unknown");
}

function isTrackingCapabilities(value: unknown): boolean {
  return isRecord(value) && Object.values(value).every(isCapabilityState);
}

function isTrackedOfferV2(value: unknown): value is HotelTrackedOfferV2Out {
  if (!isRecord(value) || !isRecord(value.stay_context) || !isTrackingCapabilities(value.capabilities) || !Array.isArray(value.warnings)) {
    return false;
  }
  const observationIsValid = value.latest_observation === null || (
    isRecord(value.latest_observation)
    && typeof value.latest_observation.snapshot_id === "string"
    && typeof value.latest_observation.legacy_collected_at === "string"
    && (typeof value.latest_observation.observed_at === "string" || value.latest_observation.observed_at === null)
    && typeof value.latest_observation.provider === "string"
    && (typeof value.latest_observation.room_label === "string" || value.latest_observation.room_label === null)
    && (typeof value.latest_observation.meal_plan === "string" || value.latest_observation.meal_plan === null)
    && (typeof value.latest_observation.cancellation_policy === "string" || value.latest_observation.cancellation_policy === null)
    && typeof value.latest_observation.availability_status === "string"
    && (typeof value.latest_observation.conditions_completeness === "string" || value.latest_observation.conditions_completeness === null)
    && (typeof value.latest_observation.canonical_stay_offer_id === "string" || value.latest_observation.canonical_stay_offer_id === null)
    && isTrackingPrice(value.latest_observation.price)
    && isTrackingFreshness(value.latest_observation.freshness)
  );
  const activeObservationIsValid = value.state !== "active" || (
    isRecord(value.latest_observation)
    && typeof value.stay_context.check_in === "string"
    && typeof value.stay_context.check_out === "string"
    && typeof value.latest_observation.canonical_stay_offer_id === "string"
    && isRecord(value.latest_observation.price)
    && typeof value.latest_observation.price.amount === "number"
    && value.latest_observation.price.basis === "total_stay"
    && value.latest_observation.price.status === "observed"
    && value.latest_observation.conditions_completeness === "complete"
    && (value.latest_observation.availability_status === "available" || value.latest_observation.availability_status === "limited")
  );
  const unavailableObservationIsValid = value.state !== "unavailable" || (
    isRecord(value.latest_observation)
    && value.latest_observation.availability_status !== "available"
    && value.latest_observation.availability_status !== "limited"
    && value.latest_observation.availability_status !== "stale"
    && isRecord(value.latest_observation.price)
    && value.latest_observation.price.status === "unavailable"
  );
  return typeof value.id === "string"
    && typeof value.hotel_id === "string"
    && typeof value.state_version === "number"
    && Number.isInteger(value.state_version)
    && value.state_version >= 1
    && (value.state === "active" || value.state === "pending_context" || value.state === "pending_first_observation" || value.state === "partial" || value.state === "paused" || value.state === "unavailable" || value.state === "expired" || value.state === "archived")
    && (typeof value.stay_context.check_in === "string" || value.stay_context.check_in === null)
    && (typeof value.stay_context.check_out === "string" || value.stay_context.check_out === null)
    && typeof value.stay_context.guests === "number"
    && value.stay_context.guests > 0
    && typeof value.stay_context.currency === "string"
    && value.stay_context.currency.length > 0
    && observationIsValid
    && activeObservationIsValid
    && unavailableObservationIsValid
    && value.warnings.every(isWarning);
}

function isTrackedOffersV2Response(value: unknown): value is HotelTrackedOffersV2Out {
  if (!isRecord(value) || !Array.isArray(value.data) || !isRecord(value.meta)) return false;
  const { meta } = value;
  return meta.contract_version === "hotels.tracking.v2"
    && typeof meta.request_id === "string"
    && typeof meta.generated_at === "string"
    && (meta.result_state === "success" || meta.result_state === "empty" || meta.result_state === "partial")
    && isRecord(meta.query)
    && isRecord(meta.pagination)
    && meta.pagination.mode === "none"
    && typeof meta.pagination.returned === "number"
    && meta.pagination.returned === value.data.length
    && typeof meta.pagination.total === "number"
    && meta.pagination.total >= meta.pagination.returned
    && typeof meta.pagination.has_next === "boolean"
    && (typeof meta.pagination.next_cursor === "string" || meta.pagination.next_cursor === null)
    && (typeof meta.pagination.previous_cursor === "string" || meta.pagination.previous_cursor === null)
    && typeof meta.pagination.sort === "string"
    && isTrackingFreshness(meta.freshness)
    && isTrackingCapabilities(meta.capabilities)
    && Array.isArray(meta.warnings)
    && meta.warnings.every(isWarning)
    && value.data.every(isTrackedOfferV2);
}

function isTrackedOfferV2CreateResponse(value: unknown): value is HotelTrackedOfferV2CreateOut {
  return isRecord(value)
    && isTrackedOfferV2(value.tracking)
    && isRecord(value.creation)
    && (value.creation.outcome === "created" || value.creation.outcome === "existing")
    && typeof value.creation.semantic_dedupe === "boolean"
    && ((value.creation.outcome === "created" && value.creation.semantic_dedupe === false)
      || (value.creation.outcome === "existing" && value.creation.semantic_dedupe === true));
}

function isTrackedOfferV2LifecycleResponse(value: unknown): value is HotelTrackedOfferV2LifecycleOut {
  return isRecord(value)
    && isTrackedOfferV2(value.tracking)
    && (value.outcome === "applied" || value.outcome === "existing" || value.outcome === "expired")
    && (value.outcome === "expired" ? value.tracking.state === "expired" : value.tracking.state !== "expired");
}

function isTrackedOfferHistoryV2Response(value: unknown): value is HotelTrackedOfferHistoryV2Out {
  if (!isRecord(value) || !isRecord(value.series) || !isRecord(value.series.identity) || !Array.isArray(value.series.points)
    || !Array.isArray(value.series.gaps) || !Array.isArray(value.series.segments) || !isRecord(value.aggregates)
    || !isRecord(value.comparisons) || !isTrackingFreshness(value.freshness) || !isTrackingCapabilities(value.capabilities)) {
    return false;
  }
  const { identity } = value.series;
  const aggregateValues = [
    value.aggregates.min_price,
    value.aggregates.max_price,
    value.aggregates.median_price,
    value.aggregates.average_price,
  ];
  return typeof value.tracked_offer_id === "string"
    && (identity.status === "comparable" || identity.status === "legacy_comparison" || identity.status === "not_comparable")
    && (typeof identity.comparability_key === "string" || identity.comparability_key === null)
    && (typeof identity.check_in === "string" || identity.check_in === null)
    && (typeof identity.check_out === "string" || identity.check_out === null)
    && typeof identity.guests === "number" && identity.guests > 0
    && typeof identity.currency === "string" && identity.currency.length > 0
    && (typeof identity.provider_scope === "string" || identity.provider_scope === null)
    && value.series.points.every((point) => isRecord(point)
      && typeof point.snapshot_id === "string"
      && typeof point.observed_at === "string"
      && (point.observation_time_source === "provider_observed" || point.observation_time_source === "legacy_collected")
      && typeof point.provider === "string"
      && typeof point.availability_status === "string"
      && (typeof point.conditions_completeness === "string" || point.conditions_completeness === null)
      && (typeof point.canonical_stay_offer_id === "string" || point.canonical_stay_offer_id === null)
      && (point.price_semantics === "total" || point.price_semantics === "unknown")
      && isTrackingPrice(point.price)
      && (point.eligibility === "eligible" || point.eligibility === "excluded")
      && (typeof point.excluded_reason === "string" || point.excluded_reason === null))
    && typeof value.aggregates.sample_size_total === "number"
    && value.aggregates.sample_size_total === value.series.points.length
    && typeof value.aggregates.sample_size_eligible === "number"
    && value.aggregates.sample_size_eligible >= 0
    && aggregateValues.every((item) => typeof item === "number" || item === null)
    && typeof value.aggregates.currency === "string"
    && (value.aggregates.price_semantics === "total" || value.aggregates.price_semantics === "unknown")
    && isRecord(value.aggregates.exclusions)
    && Object.values(value.aggregates.exclusions).every((count) => typeof count === "number" && count >= 0)
    && value.comparisons.vs_initial === null
    && value.comparisons.vs_previous === null
    && value.comparisons.vs_minimum === null;
}

export function parseAreaSearchV2Response(payload: unknown): HotelAreaSearchV2Out {
  if (!isRecord(payload) || !Array.isArray(payload.data) || !isRecord(payload.meta)) {
    throw new HotelsRequestError(502, "hotels_results_v2_invalid");
  }
  if (
    payload.meta.contract_version !== "hotels.results.v2"
    || typeof payload.meta.request_id !== "string"
    || !payload.data.every(isAreaSearchV2Result)
  ) {
    throw new HotelsRequestError(502, "hotels_results_v2_invalid");
  }
  return payload as HotelAreaSearchV2Out;
}

export function adaptAreaSearchV2ToV1(payload: HotelAreaSearchV2Out): HotelAreaSearchResultOut[] {
  return payload.data.map((result) => ({
    hotel_id: result.hotel_id,
    canonical_name: result.canonical_name,
    city: result.city,
    country_code: result.country_code,
    stars: result.stars,
    distance_km: result.distance_km,
    lowest_price: result.price.amount,
    price_basis: result.price.basis === "total_stay" ? "total_stay" : "unknown",
    currency: result.price.currency,
    provider: result.provider,
    check_in: result.stay_context.check_in,
    check_out: result.stay_context.check_out,
    guests: result.stay_context.guests,
    has_tracking: result.has_tracking,
  }));
}

export async function areaSearchV2(params: {
  latitude: number;
  longitude: number;
  radius_km?: number;
  check_in: string;
  check_out: string;
  guests?: number;
  currency?: string;
  min_stars?: number;
  max_price?: number;
  sort?: string;
  use_provider?: boolean;
},
  signal?: AbortSignal,
  intentId?: string,
): Promise<HotelAreaSearchV2Out> {
  const payload = await request<unknown>(`/hotels/v2/area-search${queryString(params)}`, {
    signal,
    headers: intentId ? { "x-client-event-id": intentId } : undefined,
  });
  return parseAreaSearchV2Response(payload);
}

export function parseTrackedOffersV2Response(payload: unknown): HotelTrackedOffersV2Out {
  if (!isTrackedOffersV2Response(payload)) {
    throw new HotelsRequestError(502, "hotels_tracking_v2_invalid");
  }
  return payload;
}

export function parseTrackedOfferV2CreateResponse(payload: unknown): HotelTrackedOfferV2CreateOut {
  if (!isTrackedOfferV2CreateResponse(payload)) {
    throw new HotelsRequestError(502, "hotels_tracking_v2_invalid");
  }
  return payload;
}

export function parseTrackedOfferV2LifecycleResponse(payload: unknown): HotelTrackedOfferV2LifecycleOut {
  if (!isTrackedOfferV2LifecycleResponse(payload)) {
    throw new HotelsRequestError(502, "hotels_tracking_v2_invalid");
  }
  return payload;
}

export function parseTrackedOfferHistoryV2Response(payload: unknown): HotelTrackedOfferHistoryV2Out {
  if (!isTrackedOfferHistoryV2Response(payload)) {
    throw new HotelsRequestError(502, "hotels_tracking_history_v2_invalid");
  }
  return payload;
}

export async function listTrackedOffersV2(): Promise<HotelTrackedOffersV2Out> {
  const payload = await request<unknown>("/hotels/v2/tracked-offers");
  return parseTrackedOffersV2Response(payload);
}

export async function createTrackedOfferV2(sourceRateId: string): Promise<HotelTrackedOfferV2CreateOut> {
  const payload = await request<unknown>("/hotels/v2/tracked-offers", {
    method: "POST",
    body: JSON.stringify({ source_rate_id: sourceRateId }),
  });
  return parseTrackedOfferV2CreateResponse(payload);
}

export async function transitionTrackedOfferV2Lifecycle(
  offerId: string,
  action: "pause" | "resume" | "archive",
  expectedStateVersion: number,
): Promise<HotelTrackedOfferV2LifecycleOut> {
  const payload = await request<unknown>(`/hotels/v2/tracked-offers/${offerId}/lifecycle`, {
    method: "PATCH",
    body: JSON.stringify({ action, expected_state_version: expectedStateVersion }),
  });
  return parseTrackedOfferV2LifecycleResponse(payload);
}

export async function listTrackedOffers(params?: { is_active?: boolean }): Promise<HotelTrackedOfferOut[]> {
  return request<HotelTrackedOfferOut[]>(`/hotels/tracked-offers${queryString(params || {})}`);
}

export async function createTrackedOffer(payload: {
  hotel_id: string;
  area_label?: string | null;
  origin_query?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  radius_km?: number | null;
  check_in?: string | null;
  check_out?: string | null;
  guests?: number;
  room_label?: string | null;
  meal_plan?: string | null;
  cancellation_policy?: string | null;
  provider?: string;
  initial_price?: number | null;
  current_price?: number | null;
  target_price?: number | null;
  currency?: string;
}): Promise<HotelTrackedOfferOut> {
  return request<HotelTrackedOfferOut>("/hotels/tracked-offers", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteTrackedOffer(offerId: string): Promise<void> {
  await request<{ status: string }>(`/hotels/tracked-offers/${offerId}`, { method: "DELETE" });
}

export async function getTrackedOffer(offerId: string): Promise<HotelTrackedOfferOut> {
  return request<HotelTrackedOfferOut>(`/hotels/tracked-offers/${offerId}`);
}

export async function updateTrackedOffer(
  offerId: string,
  payload: {
    area_label?: string | null;
    origin_query?: string | null;
    latitude?: number | null;
    longitude?: number | null;
    radius_km?: number | null;
    check_in?: string | null;
    check_out?: string | null;
    guests?: number;
    room_label?: string | null;
    meal_plan?: string | null;
    cancellation_policy?: string | null;
    provider?: string;
    initial_price?: number | null;
    current_price?: number | null;
    target_price?: number | null;
    currency?: string;
    is_active?: boolean;
  },
): Promise<HotelTrackedOfferOut> {
  return request<HotelTrackedOfferOut>(`/hotels/tracked-offers/${offerId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function getTrackedOfferSnapshots(offerId: string, signal?: AbortSignal): Promise<HotelRateOut[]> {
  return request<HotelRateOut[]>(`/hotels/tracked-offers/${offerId}/snapshots`, { signal });
}

export async function getTrackedOfferHistoryV2(
  offerId: string,
  signal?: AbortSignal,
): Promise<HotelTrackedOfferHistoryV2Out> {
  const payload = await request<unknown>(`/hotels/v2/tracked-offers/${offerId}/history`, { signal });
  return parseTrackedOfferHistoryV2Response(payload);
}
