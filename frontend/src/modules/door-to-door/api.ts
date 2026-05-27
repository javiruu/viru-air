import { apiFetch, apiFetchWithStatus } from "@/modules/shared/api";
import type {
  DoorToDoorHistoryItem,
  DoorToDoorLocation,
  DoorToDoorPreferences,
  DoorToDoorProviderStatus,
  DoorToDoorResponse,
  DoorToDoorSavedLocation,
  DoorToDoorSuggestionsResponse,
} from "@/modules/door-to-door/types";

export function fetchDoorToDoorSuggestions(
  query: string,
  sessionToken?: string,
  field?: "origin" | "destination",
  watchId?: string,
) {
  const params = new URLSearchParams({ q: query });
  if (sessionToken) params.set("session_token", sessionToken);
  if (field) params.set("field", field);
  if (watchId) params.set("watch_id", watchId);
  return apiFetchWithStatus<DoorToDoorSuggestionsResponse>(
    `/door-to-door/suggestions?${params.toString()}`,
    undefined,
    { timeoutMs: 4500 },
  ).then((result) => {
    if (result.ok) return result.data;
    return {
      items: [],
      meta: {
        provider_status: "provider_error" as const,
        degraded_reason: result.error.code || "suggestions_fetch_failed",
        used_region_codes: [],
      },
    };
  });
}

export function fetchDoorToDoorProviderStatus(): Promise<DoorToDoorProviderStatus[]> {
  return apiFetch<DoorToDoorProviderStatus[]>("/door-to-door/providers/status");
}

export function fetchSavedDoorToDoorLocation(): Promise<DoorToDoorSavedLocation | null> {
  return apiFetch<DoorToDoorSavedLocation | null>("/door-to-door/saved-location");
}

export function saveDoorToDoorLocation(location: DoorToDoorLocation): Promise<DoorToDoorSavedLocation> {
  return apiFetch<DoorToDoorSavedLocation>("/door-to-door/saved-location", {
    method: "PUT",
    body: JSON.stringify({ location }),
  });
}

export function deleteDoorToDoorLocation(): Promise<{ status: string }> {
  return apiFetch<{ status: string }>("/door-to-door/saved-location", { method: "DELETE" });
}

export function searchDoorToDoor(input: {
  flight_watch_id: string;
  origin: DoorToDoorLocation;
  final_destination: DoorToDoorLocation;
  preferences: DoorToDoorPreferences;
  save_origin_as_default: boolean;
}): Promise<DoorToDoorResponse> {
  return apiFetch<DoorToDoorResponse>("/door-to-door/search", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function fetchDoorToDoorHistory(watchId?: string): Promise<DoorToDoorHistoryItem[]> {
  const suffix = watchId ? `?watch_id=${encodeURIComponent(watchId)}` : "";
  return apiFetch<DoorToDoorHistoryItem[]>(`/door-to-door/history${suffix}`);
}

export function chooseDoorToDoorOption(input: {
  historyId: string;
  optionId: string;
  optionLabel: string;
  optionSummary: Record<string, unknown>;
}): Promise<{ id: string; option_id: string; option_label: string; chosen_at: string }> {
  return apiFetch(`/door-to-door/history/${encodeURIComponent(input.historyId)}/chosen`, {
    method: "POST",
    body: JSON.stringify({
      option_id: input.optionId,
      option_label: input.optionLabel,
      option_summary: input.optionSummary,
    }),
  });
}
