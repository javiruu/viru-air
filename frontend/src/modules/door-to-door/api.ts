import {
  suggestionsApiV1DoorToDoorSuggestionsGet,
  providersStatusApiV1DoorToDoorProvidersStatusGet,
  corridorsApiV1DoorToDoorCorridorsGet,
  getSavedLocationApiV1DoorToDoorSavedLocationGet,
  putSavedLocationApiV1DoorToDoorSavedLocationPut,
  deleteSavedLocationApiV1DoorToDoorSavedLocationDelete,
  searchDoorToDoorApiV1DoorToDoorSearchPost,
  listHistoryApiV1DoorToDoorHistoryGet,
  chooseOptionApiV1DoorToDoorHistoryHistoryIdChosenPost,
  listSavedPlacesApiV1DoorToDoorSavedPlacesGet,
  createSavedPlaceApiV1DoorToDoorSavedPlacesPost,
  deleteSavedPlaceApiV1DoorToDoorSavedPlacesPlaceIdDelete,
} from "@/api/generated/door-to-door/door-to-door";
import type {
  DoorToDoorCorridorsResponse,
  DoorToDoorHistoryItem,
  DoorToDoorLocation,
  DoorToDoorPreferences,
  DoorToDoorResponse,
  DoorToDoorSavedLocation,
  DoorToDoorSavedPlace,
  DoorToDoorSuggestionsResponse,
  DoorToDoorProviderStatus,
} from "@/modules/door-to-door/types";

export function fetchDoorToDoorSuggestions(
  query: string,
  sessionToken?: string,
  field?: "origin" | "destination",
  watchId?: string,
  signal?: AbortSignal,
): Promise<DoorToDoorSuggestionsResponse> {
  const params = new URLSearchParams({ q: query });
  if (sessionToken) params.set("session_token", sessionToken);
  if (field) params.set("field", field);
  if (watchId) params.set("watch_id", watchId);
  return suggestionsApiV1DoorToDoorSuggestionsGet({ q: query, session_token: sessionToken, field, watch_id: watchId }, { signal }) as unknown as Promise<DoorToDoorSuggestionsResponse>;
}

export function fetchDoorToDoorProviderStatus(): Promise<DoorToDoorProviderStatus[]> {
  return providersStatusApiV1DoorToDoorProvidersStatusGet() as unknown as Promise<DoorToDoorProviderStatus[]>;
}

export function fetchDoorToDoorCorridors(): Promise<DoorToDoorCorridorsResponse> {
  return corridorsApiV1DoorToDoorCorridorsGet() as unknown as Promise<DoorToDoorCorridorsResponse>;
}

export function fetchSavedDoorToDoorLocation(): Promise<DoorToDoorSavedLocation | null> {
  return getSavedLocationApiV1DoorToDoorSavedLocationGet() as unknown as Promise<DoorToDoorSavedLocation | null>;
}

export function saveDoorToDoorLocation(
  location: DoorToDoorLocation,
): Promise<DoorToDoorSavedLocation> {
  return putSavedLocationApiV1DoorToDoorSavedLocationPut({ location: location as any }) as unknown as Promise<DoorToDoorSavedLocation>;
}

export function deleteDoorToDoorLocation(): Promise<{ status: string }> {
  return deleteSavedLocationApiV1DoorToDoorSavedLocationDelete() as unknown as Promise<{ status: string }>;
}

export function searchDoorToDoor(input: {
  flight_watch_id: string;
  origin: DoorToDoorLocation;
  final_destination: DoorToDoorLocation;
  preferences: DoorToDoorPreferences;
  save_origin_as_default: boolean;
}): Promise<DoorToDoorResponse> {
  return searchDoorToDoorApiV1DoorToDoorSearchPost(input as any) as unknown as Promise<DoorToDoorResponse>;
}

export function fetchDoorToDoorHistory(watchId?: string): Promise<DoorToDoorHistoryItem[]> {
  return listHistoryApiV1DoorToDoorHistoryGet({ watch_id: watchId }) as unknown as Promise<DoorToDoorHistoryItem[]>;
}

export function chooseDoorToDoorOption(input: {
  historyId: string;
  optionId: string;
  optionLabel: string;
  optionSummary: Record<string, unknown>;
}): Promise<{ id: string; option_id: string; option_label: string; chosen_at: string }> {
  return chooseOptionApiV1DoorToDoorHistoryHistoryIdChosenPost(input.historyId, {
    option_id: input.optionId,
    option_label: input.optionLabel,
    option_summary: input.optionSummary as any,
  }) as unknown as Promise<{ id: string; option_id: string; option_label: string; chosen_at: string }>;
}

export function fetchDoorToDoorSavedPlaces(watchId?: string): Promise<DoorToDoorSavedPlace[]> {
  return listSavedPlacesApiV1DoorToDoorSavedPlacesGet({ watch_id: watchId }) as unknown as Promise<DoorToDoorSavedPlace[]>;
}

export function createDoorToDoorSavedPlace(input: {
  label: string;
  note: string;
  watch_id: string | null;
}): Promise<DoorToDoorSavedPlace> {
  return createSavedPlaceApiV1DoorToDoorSavedPlacesPost(input) as unknown as Promise<DoorToDoorSavedPlace>;
}

export function deleteDoorToDoorSavedPlace(placeId: string): Promise<{ status: string }> {
  return deleteSavedPlaceApiV1DoorToDoorSavedPlacesPlaceIdDelete(placeId) as unknown as Promise<{ status: string }>;
}
