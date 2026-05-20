import { apiFetch } from "@/modules/shared/api";
import type {
  DoorToDoorHistoryItem,
  DoorToDoorLocation,
  DoorToDoorPreferences,
  DoorToDoorResponse,
  DoorToDoorSavedLocation,
  DoorToDoorSuggestion,
} from "@/modules/door-to-door/types";

export function fetchDoorToDoorSuggestions(query: string): Promise<DoorToDoorSuggestion[]> {
  return apiFetch<DoorToDoorSuggestion[]>(`/door-to-door/suggestions?q=${encodeURIComponent(query)}`);
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
