export function getOfficialRyanairFlightDeepLink(value: string | null | undefined): string {
  if (!value) return "";
  try {
    const parsed = new URL(value, "https://www.ryanair.com");
    const host = parsed.hostname.toLowerCase();
    const isRyanairHost = host === "ryanair.com" || host.endsWith(".ryanair.com");
    const isFlightSelectPath = parsed.pathname.toLowerCase().includes("/trip/flights/select");
    if (!isRyanairHost || !isFlightSelectPath) return "";
    const queryMap = new Map<string, string>();
    for (const [key, raw] of parsed.searchParams.entries()) {
      queryMap.set(key.toLowerCase(), raw);
    }
    const pick = (...keys: string[]) => {
      for (const key of keys) {
        const queryValue = queryMap.get(key.toLowerCase());
        if (queryValue) return queryValue;
      }
      return "";
    };
    const origin = pick("originIata", "origin_iata", "tpOriginIata");
    const destination = pick("destinationIata", "destination_iata", "tpDestinationIata");
    const dateOut = pick("dateOut", "date_out", "tpStartDate");
    if (!origin || !destination || !dateOut) return "";
    const localeMatch = parsed.pathname.match(/^\/([a-z]{2})\/([a-z]{2})\/trip\/flights\/select/i);
    const localePath = localeMatch ? `/${localeMatch[1].toLowerCase()}/${localeMatch[2].toLowerCase()}` : "/es/es";
    const normalized = new URL(`https://www.ryanair.com${localePath}/trip/flights/select`);
    const adults = pick("adults", "tpAdults") || "1";
    const teens = pick("teens", "tpTeens") || "0";
    const children = pick("children", "tpChildren") || "0";
    const infants = pick("infants", "tpInfants") || "0";
    const dateIn = pick("dateIn", "date_in", "tpEndDate");
    const isReturn = pick("isReturn") || (dateIn ? "true" : "false");
    const params: Record<string, string> = {
      adults,
      teens,
      children,
      infants,
      dateOut,
      dateIn,
      isConnectedFlight: pick("isConnectedFlight") || "false",
      discount: pick("discount", "tpDiscount") || "0",
      promoCode: pick("promoCode", "tpPromoCode"),
      isReturn,
      originIata: origin.toUpperCase(),
      destinationIata: destination.toUpperCase(),
      originMac: pick("originMac", "tpOriginMac"),
      destinationMac: pick("destinationMac", "tpDestinationMac"),
      tpAdults: adults,
      tpTeens: teens,
      tpChildren: children,
      tpInfants: infants,
      tpStartDate: dateOut,
      tpEndDate: dateIn,
      tpDiscount: pick("tpDiscount", "discount") || "0",
      tpPromoCode: pick("tpPromoCode", "promoCode"),
      tpOriginIata: origin.toUpperCase(),
      tpDestinationIata: destination.toUpperCase(),
      tpOriginMac: pick("tpOriginMac", "originMac"),
      tpDestinationMac: pick("tpDestinationMac", "destinationMac"),
    };
    for (const [key, paramValue] of Object.entries(params)) {
      normalized.searchParams.set(key, paramValue);
    }
    return normalized.toString();
  } catch {
    return "";
  }
}

export function getOfficialRyanairRouteDeepLink(
  value: string | null | undefined,
  origin: string,
  destination: string,
  dateOut: string,
): string {
  const normalized = getOfficialRyanairFlightDeepLink(value);
  if (!normalized || !origin || !destination || !dateOut) return "";
  const parsed = new URL(normalized);
  const routeParams: Record<string, string> = {
    originIata: origin.toUpperCase(),
    destinationIata: destination.toUpperCase(),
    dateOut,
    originMac: "",
    destinationMac: "",
    tpOriginIata: origin.toUpperCase(),
    tpDestinationIata: destination.toUpperCase(),
    tpStartDate: dateOut,
    tpOriginMac: "",
    tpDestinationMac: "",
  };
  for (const [key, routeValue] of Object.entries(routeParams)) {
    parsed.searchParams.set(key, routeValue);
  }
  return parsed.toString();
}

export function isOfficialWizzAirDeepLink(value: string | null | undefined): boolean {
  if (!value) return false;
  try {
    const parsed = new URL(value, "https://www.wizzair.com");
    const host = parsed.hostname.toLowerCase();
    return host === "wizzair.com" || host.endsWith(".wizzair.com");
  } catch {
    return false;
  }
}

export function isGenericHttpLink(value: string | null | undefined): boolean {
  if (!value) return false;
  try {
    const parsed = new URL(value);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}
