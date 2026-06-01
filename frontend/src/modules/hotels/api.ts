import { apiFetchWithStatus } from "@/modules/shared/api";

import type {
  HotelCompSetDetailOut,
  HotelCompSetOut,
  HotelDetailOut,
  HotelIngestOut,
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

