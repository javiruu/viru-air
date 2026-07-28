export const FARE_EXTRA_KINDS = [
  "cabin_bag_10kg",
  "checked_bag_20kg",
  "insurance",
  "fast_track",
  "priority_boarding",
  "seat_selection",
  "flexible_ticket",
] as const;

export const FARE_AIRLINE_IDS = [
  "ryanair",
  "vueling",
  "wizzair",
  "easyjet",
] as const;

export type FareExtraKind = (typeof FARE_EXTRA_KINDS)[number];
export type FareAirlineId = (typeof FARE_AIRLINE_IDS)[number];

export type FareComparisonExtra = {
  readonly kind: FareExtraKind;
  readonly selected: boolean;
};

export type FareComparisonProfile = {
  readonly travelers: number;
  readonly airline_id?: FareAirlineId | null;
  readonly flight_count?: number;
  readonly extras: readonly FareComparisonExtra[];
};

export type ComparableFare = {
  readonly base_total: number;
  readonly extras_min_total: number;
  readonly extras_max_total: number | null;
  readonly comparable_min_total: number;
  readonly comparable_max_total: number | null;
  readonly is_complete: boolean;
  readonly unavailable_kinds: readonly FareExtraKind[];
  readonly airline_id: FareAirlineId | null;
  readonly airline_label: string | null;
  readonly source_url: string | null;
  readonly source_checked_on: string | null;
};

type FareOffer = {
  readonly id: string;
  readonly covers: readonly FareExtraKind[];
  readonly billing_unit: "per_flight" | "per_booking";
  readonly minimum_per_traveler_per_unit: number;
  readonly maximum_per_traveler_per_unit: number | null;
};

type AirlineTariff = {
  readonly id: FareAirlineId;
  readonly label: string;
  readonly currency: "EUR";
  readonly aliases: readonly string[];
  readonly source_url: string;
  readonly source_checked_on: string;
  readonly offers: readonly FareOffer[];
};

const SOURCE_CHECKED_ON = "2026-07-28";

const AIRLINE_TARIFFS: Readonly<Record<FareAirlineId, AirlineTariff>> = {
  ryanair: {
    id: "ryanair",
    label: "Ryanair",
    currency: "EUR",
    aliases: ["fr", "ryr", "ryanair", "ryanair public fares"],
    source_url: "https://www.ryanair.com/no/no/nyttig-info/hjelpesenter/gebyrer",
    source_checked_on: SOURCE_CHECKED_ON,
    offers: [
      {
        id: "priority_2_cabin_bags",
        covers: ["cabin_bag_10kg", "priority_boarding"],
        billing_unit: "per_flight",
        minimum_per_traveler_per_unit: 6,
        maximum_per_traveler_per_unit: 36,
      },
      {
        id: "checked_bag_20kg",
        covers: ["checked_bag_20kg"],
        billing_unit: "per_flight",
        minimum_per_traveler_per_unit: 18.99,
        maximum_per_traveler_per_unit: 59.99,
      },
      {
        id: "seat_selection",
        covers: ["seat_selection"],
        billing_unit: "per_flight",
        minimum_per_traveler_per_unit: 4.5,
        maximum_per_traveler_per_unit: 33,
      },
    ],
  },
  vueling: {
    id: "vueling",
    label: "Vueling",
    currency: "EUR",
    aliases: ["vy", "vlg", "vueling"],
    source_url: "https://www.vueling.com/en/vueling-services/supplementary-service-rates/",
    source_checked_on: SOURCE_CHECKED_ON,
    offers: [
      {
        id: "cabin_bag_10kg",
        covers: ["cabin_bag_10kg"],
        billing_unit: "per_flight",
        minimum_per_traveler_per_unit: 10,
        maximum_per_traveler_per_unit: 59,
      },
      {
        id: "checked_bag_20kg",
        covers: ["checked_bag_20kg"],
        billing_unit: "per_flight",
        minimum_per_traveler_per_unit: 14,
        maximum_per_traveler_per_unit: 96,
      },
      {
        id: "standard_seat",
        covers: ["seat_selection"],
        billing_unit: "per_flight",
        minimum_per_traveler_per_unit: 5,
        maximum_per_traveler_per_unit: 30,
      },
      {
        id: "flex_pack",
        covers: ["flexible_ticket"],
        billing_unit: "per_booking",
        minimum_per_traveler_per_unit: 10,
        maximum_per_traveler_per_unit: 50,
      },
    ],
  },
  wizzair: {
    id: "wizzair",
    label: "Wizz Air",
    currency: "EUR",
    aliases: ["w6", "wzz", "wizz", "wizzair", "wizz air"],
    source_url: "https://wizzair.com/en-gb/information-and-services/wizz-services/wizz-priority",
    source_checked_on: SOURCE_CHECKED_ON,
    offers: [
      {
        id: "wizz_priority",
        covers: ["cabin_bag_10kg", "priority_boarding"],
        billing_unit: "per_flight",
        minimum_per_traveler_per_unit: 10,
        maximum_per_traveler_per_unit: 60,
      },
    ],
  },
  easyjet: {
    id: "easyjet",
    label: "easyJet",
    currency: "EUR",
    aliases: ["u2", "ezy", "ezj", "easyjet", "easy jet"],
    source_url: "https://www.easyjet.com/en/terms-and-conditions/fees",
    source_checked_on: SOURCE_CHECKED_ON,
    offers: [],
  },
} as const;

function normalizeAirlineToken(value: string): string {
  return value.trim().toLowerCase().replace(/[-_]+/g, " ").replace(/\s+/g, " ");
}

function findFareAirline(value: string): FareAirlineId | null {
  const normalized = normalizeAirlineToken(value);
  if (!normalized) return null;
  const compact = normalized.replace(/\s+/g, "");
  const tariff = Object.values(AIRLINE_TARIFFS).find((candidate) =>
    candidate.aliases.some((alias) => {
      const normalizedAlias = normalizeAirlineToken(alias);
      const compactAlias = normalizedAlias.replace(/\s+/g, "");
      return normalized === normalizedAlias
        || normalized.includes(normalizedAlias)
        || compact.includes(compactAlias);
    }),
  );
  return tariff?.id ?? null;
}

export function resolveFareAirline(
  provider: string | null | undefined,
  carrierCodes: readonly (string | null | undefined)[] = [],
): FareAirlineId | null {
  const carrierAirlines = new Set<FareAirlineId>();
  let hasUnsupportedCarrier = false;
  for (const carrierCode of carrierCodes) {
    if (!carrierCode) continue;
    const airline = findFareAirline(carrierCode);
    if (airline) {
      carrierAirlines.add(airline);
    } else if (carrierCode.trim()) {
      hasUnsupportedCarrier = true;
    }
  }
  if (hasUnsupportedCarrier) return null;
  if (carrierAirlines.size > 1) return null;
  if (carrierAirlines.size === 1) return [...carrierAirlines][0] ?? null;
  return provider ? findFareAirline(provider) : null;
}

export function createEmptyFareComparisonProfile(travelers: number): FareComparisonProfile {
  return {
    travelers: Math.max(1, Math.min(9, Math.trunc(travelers))),
    airline_id: null,
    flight_count: 1,
    extras: FARE_EXTRA_KINDS.map((kind) => ({
      kind,
      selected: false,
    })),
  };
}

export function attachFareAirline(
  profile: FareComparisonProfile,
  provider: string | null | undefined,
  carrierCodes: readonly (string | null | undefined)[] = [],
  flightCount = profile.flight_count ?? 1,
): FareComparisonProfile {
  const airlineId = resolveFareAirline(provider, carrierCodes);
  return {
    ...profile,
    ...(airlineId ? { airline_id: airlineId } : {}),
    flight_count: Math.max(1, Math.min(8, Math.trunc(flightCount))),
  };
}

function roundMoney(value: number): number {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

export function calculateComparableFare(
  baseTotal: number,
  currency: string,
  profile: FareComparisonProfile,
  provider: string | null | undefined,
  carrierCodes: readonly (string | null | undefined)[] = [],
  flightCount = profile.flight_count ?? 1,
): ComparableFare {
  const airlineId = profile.airline_id ?? resolveFareAirline(provider, carrierCodes);
  const tariff = airlineId ? AIRLINE_TARIFFS[airlineId] : null;
  const selectedKinds = new Set(
    profile.extras.filter((extra) => extra.selected).map((extra) => extra.kind),
  );
  const pricedKinds = new Set<FareExtraKind>();
  const matchedOffers = tariff && tariff.currency === currency.toUpperCase()
    ? tariff.offers.filter((offer) => offer.covers.some((kind) => selectedKinds.has(kind)))
    : [];
  const billableFlights = Math.max(1, Math.min(8, Math.trunc(flightCount)));

  let minimumPerTraveler = 0;
  let maximumPerTraveler = 0;
  let hasOpenMaximum = false;
  for (const offer of matchedOffers) {
    const unitCount = offer.billing_unit === "per_flight" ? billableFlights : 1;
    minimumPerTraveler += offer.minimum_per_traveler_per_unit * unitCount;
    if (offer.maximum_per_traveler_per_unit === null) {
      hasOpenMaximum = true;
    } else {
      maximumPerTraveler += offer.maximum_per_traveler_per_unit * unitCount;
    }
    for (const kind of offer.covers) {
      if (selectedKinds.has(kind)) pricedKinds.add(kind);
    }
  }

  const unavailableKinds = [...selectedKinds].filter((kind) => !pricedKinds.has(kind));
  const extrasMinTotal = roundMoney(minimumPerTraveler * profile.travelers);
  const extrasMaxTotal = hasOpenMaximum || unavailableKinds.length > 0
    ? null
    : roundMoney(maximumPerTraveler * profile.travelers);

  return {
    base_total: baseTotal,
    extras_min_total: extrasMinTotal,
    extras_max_total: extrasMaxTotal,
    comparable_min_total: roundMoney(baseTotal + extrasMinTotal),
    comparable_max_total: extrasMaxTotal === null
      ? null
      : roundMoney(baseTotal + extrasMaxTotal),
    is_complete: unavailableKinds.length === 0,
    unavailable_kinds: unavailableKinds,
    airline_id: airlineId,
    airline_label: tariff?.label ?? null,
    source_url: tariff?.source_url ?? null,
    source_checked_on: tariff?.source_checked_on ?? null,
  };
}
