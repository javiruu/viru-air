import type { FormEvent } from "react";

import { apiFetch } from "@/modules/shared/api";
import { COUNTRY_AIRPORTS, findCountryByIata } from "@/modules/shared/airports";
import type { CountryAirports } from "@/modules/shared/airports";
import type { Watch } from "@/modules/watchlist/types";

type MessageType = "error" | "success";
type PickerField = "origin" | "destination";
type TranslateFn = (key: string, params?: Record<string, string | number>) => string;

type UseWatchlistFormInput = {
  t: TranslateFn;
  origin: string;
  destination: string;
  travelDate: string;
  targetPrice: string;
  activePicker: PickerField | null;
  compatibleOrigins: string[];
  compatibleDestinations: string[];
  setOrigin: (value: string) => void;
  setDestination: (value: string) => void;
  setTravelDate: (value: string) => void;
  setTargetPrice: (value: string) => void;
  setMessage: (value: string) => void;
  setMessageType: (value: MessageType) => void;
  setShowAdd: (value: boolean) => void;
  setActivePicker: (value: PickerField | null) => void;
  setSelectedCountry: (value: CountryAirports | null) => void;
  load: () => Promise<void>;
};

export function useWatchlistForm({
  t,
  origin,
  destination,
  travelDate,
  targetPrice,
  activePicker,
  compatibleOrigins,
  compatibleDestinations,
  setOrigin,
  setDestination,
  setTravelDate,
  setTargetPrice,
  setMessage,
  setMessageType,
  setShowAdd,
  setActivePicker,
  setSelectedCountry,
  load,
}: UseWatchlistFormInput) {
  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setMessage("");
    setMessageType("error");

    if (!travelDate) {
      setMessage(t("watchlist.messages.selectDateBeforeSave"));
      return;
    }
    if (!origin || !destination) {
      setMessage(t("watchlist.messages.completeRoute"));
      return;
    }
    if (compatibleDestinations.length > 0 && !compatibleDestinations.includes(destination)) {
      setMessage(t("watchlist.messages.destinationNotCompatible"));
      return;
    }
    if (compatibleOrigins.length > 0 && !compatibleOrigins.includes(origin)) {
      setMessage(t("watchlist.messages.originNotCompatible"));
      return;
    }

    try {
      await apiFetch<Watch>("/watchlist", {
        method: "POST",
        body: JSON.stringify({
          origin_iata: origin,
          destination_iata: destination,
          travel_date_local: travelDate,
          target_price: targetPrice ? Number(targetPrice) : null,
        }),
      });
      await load();
      setMessage(t("watchlist.messages.flightCreated"));
      setMessageType("success");
      setShowAdd(false);
      setOrigin("");
      setDestination("");
      setTravelDate("");
      setTargetPrice("");
    } catch {
      setMessage(t("watchlist.messages.createError"));
      setMessageType("error");
    }
  }

  function openPicker(which: PickerField): void {
    if (!travelDate) {
      setMessage(t("watchlist.messages.selectDateBeforeAirports"));
      setMessageType("error");
      return;
    }
    const current = which === "origin" ? origin : destination;
    const country = findCountryByIata(current) || COUNTRY_AIRPORTS[0] || null;
    setSelectedCountry(country);
    setActivePicker(which);
  }

  function clearSelection(): void {
    if (activePicker === "origin") setOrigin("");
    if (activePicker === "destination") setDestination("");
  }

  function selectAirport(iata: string): void {
    if (activePicker === "origin") {
      setOrigin(iata);
    } else if (activePicker === "destination") {
      setDestination(iata);
    }
    setActivePicker(null);
  }

  return {
    onSubmit,
    openPicker,
    clearSelection,
    selectAirport,
  };
}
