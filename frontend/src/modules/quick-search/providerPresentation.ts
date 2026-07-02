export type QuickSearchProviderId = "ryanair" | "vueling" | "wizzair" | "easyjet" | "duffel" | "unknown";

/** Initial provider search statuses shown during quick-search loading. */
export const INITIAL_PROVIDER_SEARCH_STATUSES: Array<{
  id: string;
  label: string;
  status: "searching";
}> = [
  { id: "ryanair", label: "Ryanair", status: "searching" },
  { id: "vueling", label: "Vueling", status: "searching" },
  { id: "wizzair", label: "Wizz Air", status: "searching" },
  { id: "easyjet", label: "easyJet", status: "searching" },
  { id: "duffel", label: "Duffel", status: "searching" },
] as const;

export type QuickSearchProviderPresentation = {
  id: QuickSearchProviderId;
  label: string;
  rawSource: string | null;
};

export function resolveQuickSearchProviderPresentation(
  source: unknown,
  unknownLabel = "Unknown",
): QuickSearchProviderPresentation {
  const rawSource = typeof source === "string" ? source.trim() : "";
  if (!rawSource) {
    return {
      id: "unknown",
      label: unknownLabel,
      rawSource: null,
    };
  }

  const normalized = rawSource.toLowerCase();
  if (normalized.includes("wizz")) {
    return {
      id: "wizzair",
      label: "Wizz Air",
      rawSource,
    };
  }
  if (normalized.includes("easyjet") || normalized.includes("easy jet")) {
    return {
      id: "easyjet",
      label: "easyJet",
      rawSource,
    };
  }
  if (normalized.includes("ryanair")) {
    return {
      id: "ryanair",
      label: "Ryanair",
      rawSource,
    };
  }
  if (normalized.includes("vueling")) {
    return {
      id: "vueling",
      label: "Vueling",
      rawSource,
    };
  }
  if (normalized.includes("duffel")) {
    return {
      id: "duffel",
      label: "Duffel",
      rawSource,
    };
  }

  return {
    id: "unknown",
    label: rawSource,
    rawSource,
  };
}
