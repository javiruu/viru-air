import { useEffect } from "react";

import { apiFetch } from "@/modules/shared/api";
import type { CompatibleResponse } from "@/modules/watchlist/types";

type UseWatchlistCompatibilityInput = {
  origin: string;
  destination: string;
  travelDate: string;
  setOrigin: (value: string) => void;
  setDestination: (value: string) => void;
  setCompatibleOrigins: (value: string[]) => void;
  setCompatibleDestinations: (value: string[]) => void;
};

export function useWatchlistCompatibility({
  origin,
  destination,
  travelDate,
  setOrigin,
  setDestination,
  setCompatibleOrigins,
  setCompatibleDestinations,
}: UseWatchlistCompatibilityInput): void {
  useEffect(() => {
    if (!travelDate) {
      setCompatibleOrigins([]);
      setCompatibleDestinations([]);
      setOrigin("");
      setDestination("");
      return;
    }

    if (!origin) {
      setCompatibleDestinations([]);
      return;
    }

    apiFetch<CompatibleResponse>(`/airports/compatible?origin_iata=${origin}&travel_date=${travelDate}`)
      .then((data) => {
        setCompatibleDestinations(data.compatible_iata);
        if (destination && data.compatible_iata.length > 0 && !data.compatible_iata.includes(destination)) {
          setDestination("");
        }
      })
      .catch(() => setCompatibleDestinations([]));
  }, [origin, travelDate, destination, setCompatibleDestinations, setCompatibleOrigins, setDestination, setOrigin]);

  useEffect(() => {
    if (!travelDate) {
      setCompatibleOrigins([]);
      return;
    }

    if (!destination) {
      setCompatibleOrigins([]);
      return;
    }

    apiFetch<CompatibleResponse>(`/airports/compatible?destination_iata=${destination}&travel_date=${travelDate}`)
      .then((data) => {
        setCompatibleOrigins(data.compatible_iata);
        if (origin && data.compatible_iata.length > 0 && !data.compatible_iata.includes(origin)) {
          setOrigin("");
        }
      })
      .catch(() => setCompatibleOrigins([]));
  }, [destination, travelDate, origin, setCompatibleOrigins, setOrigin]);
}
