import type { HotelParityOut, HotelRateOut } from "./types";

export type HotelSignalAssessment = {
  level: "none" | "limited" | "scored";
  status: "warning" | "info" | "success" | "error";
  providerLabelKey:
    | "hotels.provider.noObservations"
    | "hotels.provider.noSignal"
    | "hotels.provider.active";
  parityBadgeKey:
    | "hotels.provider.noObservations"
    | "hotels.parity.limited"
    | "hotels.parity.stable"
    | "hotels.parity.tensioned"
    | "hotels.parity.breach";
  detailKey:
    | "hotels.parity.insufficientData"
    | "hotels.parity.limitedDetail"
    | "hotels.parity.empty";
};

export function assessHotelSignal(
  rates: HotelRateOut[],
  signal: HotelParityOut | null,
): HotelSignalAssessment {
  if (rates.length === 0) {
    return {
      level: "none",
      status: "warning",
      providerLabelKey: "hotels.provider.noObservations",
      parityBadgeKey: "hotels.provider.noObservations",
      detailKey: "hotels.parity.insufficientData",
    };
  }

  if (
    signal === null ||
    signal.provider_count < 2 ||
    signal.lowest_price === null ||
    signal.highest_price === null ||
    signal.spread_percent === null
  ) {
    return {
      level: "limited",
      status: "info",
      providerLabelKey: "hotels.provider.noSignal",
      parityBadgeKey: "hotels.parity.limited",
      detailKey: signal === null ? "hotels.parity.empty" : "hotels.parity.limitedDetail",
    };
  }

  if (signal.label === "breach") {
    return {
      level: "scored",
      status: "error",
      providerLabelKey: "hotels.provider.active",
      parityBadgeKey: "hotels.parity.breach",
      detailKey: "hotels.parity.limitedDetail",
    };
  }

  if (signal.label === "tensioned") {
    return {
      level: "scored",
      status: "warning",
      providerLabelKey: "hotels.provider.active",
      parityBadgeKey: "hotels.parity.tensioned",
      detailKey: "hotels.parity.limitedDetail",
    };
  }

  return {
    level: "scored",
    status: "success",
    providerLabelKey: "hotels.provider.active",
    parityBadgeKey: "hotels.parity.stable",
    detailKey: "hotels.parity.limitedDetail",
  };
}
