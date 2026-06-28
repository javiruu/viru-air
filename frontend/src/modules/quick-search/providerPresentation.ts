export type QuickSearchProviderId = "ryanair" | "wizzair" | "duffel" | "unknown";

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
  if (normalized.includes("ryanair")) {
    return {
      id: "ryanair",
      label: "Ryanair",
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
