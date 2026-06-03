import { apiFetchWithStatus } from "@/modules/shared/api";

import type {
  HotelAlertEventOut,
  HotelAlertRuleOut,
  HotelCompSetDetailOut,
  HotelCompSetOut,
  HotelDetailOut,
  HotelIngestOut,
  HotelNearbySuggestionOut,
  HotelParityOut,
  HotelRateOut,
  HotelSearchOut,
  HotelWatchlistItemOut,
  HotelsApiError,
} from "./types";

export class HotelsRequestError extends Error implements HotelsApiError {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "HotelsRequestError";
    this.status = status;
  }
}

function queryString(params: Record<string, string | number | null | undefined>): string {
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
    throw new HotelsRequestError(result.status, result.error.message);
  }
  return result.data;
}

export async function ingestHotelsMock(): Promise<HotelIngestOut> {
  return request<HotelIngestOut>("/hotels/ingest/mock", { method: "POST" });
}

export async function searchHotels(params: {
  q?: string;
  city?: string;
  country_code?: string;
  limit?: number;
  offset?: number;
}): Promise<HotelSearchOut[]> {
  return request<HotelSearchOut[]>(`/hotels/search${queryString(params)}`);
}

export async function getHotelDetail(hotelId: string): Promise<HotelDetailOut> {
  return request<HotelDetailOut>(`/hotels/${hotelId}`);
}

export async function getHotelRates(hotelId: string, params?: { check_in?: string; check_out?: string }): Promise<HotelRateOut[]> {
  return request<HotelRateOut[]>(`/hotels/${hotelId}/rates${queryString(params || {})}`);
}

export async function getHotelParity(hotelId: string): Promise<HotelParityOut[]> {
  return request<HotelParityOut[]>(`/hotels/${hotelId}/parity`);
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
  rule_type: "price_below" | "price_above" | "parity_break";
  threshold_amount?: number | null;
  threshold_percent?: number | null;
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
    rule_type?: "price_below" | "price_above" | "parity_break";
    threshold_amount?: number | null;
    threshold_percent?: number | null;
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

export async function getHotelNearbySuggestions(
  compSetId: string,
  params?: { radius_km?: number; limit?: number },
): Promise<HotelNearbySuggestionOut[]> {
  return request<HotelNearbySuggestionOut[]>(`/hotels/comp-sets/${compSetId}/nearby-suggestions${queryString(params || {})}`);
}

