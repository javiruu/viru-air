const QUICK_SEARCH_PROVIDER_PRESENTATIONS = [
  { id: "ryanair", label: "Ryanair", aliases: ["ryanair", "ryan air"] },
  { id: "vueling", label: "Vueling", aliases: ["vueling"] },
  { id: "wizzair", label: "Wizz Air", aliases: ["wizzair", "wizz air", "wizz"] },
  { id: "easyjet", label: "easyJet", aliases: ["easyjet", "easy jet", "ezj", "ezy", "u2"] },
  { id: "duffel", label: "Duffel", aliases: ["duffel"] },
] as const;

type KnownQuickSearchProviderPresentation = (typeof QUICK_SEARCH_PROVIDER_PRESENTATIONS)[number];
export type QuickSearchProviderId = KnownQuickSearchProviderPresentation["id"] | "unknown";

/** Initial provider search statuses shown during quick-search loading. */
export const INITIAL_PROVIDER_SEARCH_STATUSES: Array<{
  id: string;
  label: string;
  status: "searching";
}> = [
  ...QUICK_SEARCH_PROVIDER_PRESENTATIONS.map((provider) => ({
    id: provider.id,
    label: provider.label,
    status: "searching" as const,
  })),
] as const;

export type QuickSearchProviderPresentation = {
  id: QuickSearchProviderId;
  label: string;
  rawSource: string | null;
};

function sourceIncludesAlias(source: string, alias: string): boolean {
  const normalizedSource = source.toLowerCase().replace(/[-_]+/g, " ");
  const compactSource = normalizedSource.replace(/\s+/g, "");
  const normalizedAlias = alias.toLowerCase().replace(/[-_]+/g, " ");
  const compactAlias = normalizedAlias.replace(/\s+/g, "");
  return normalizedSource.includes(normalizedAlias) || compactSource.includes(compactAlias);
}

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

  const provider = QUICK_SEARCH_PROVIDER_PRESENTATIONS.find((candidate) =>
    candidate.aliases.some((alias) => sourceIncludesAlias(rawSource, alias)),
  );
  if (provider) return { id: provider.id, label: provider.label, rawSource };

  return {
    id: "unknown",
    label: rawSource,
    rawSource,
  };
}
