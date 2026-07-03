const PROVIDER_PRESENTATIONS = [
  { id: "ryanair", label: "Ryanair", aliases: ["ryanair", "ryan air"] },
  { id: "vueling", label: "Vueling", aliases: ["vueling"] },
  { id: "wizzair", label: "Wizz Air", aliases: ["wizzair", "wizz air", "wizz"] },
  { id: "easyjet", label: "easyJet", aliases: ["easyjet", "easy jet", "ezj", "ezy", "u2"] },
  { id: "duffel", label: "Duffel", aliases: ["duffel"] },
] as const;

type KnownProviderPresentation = (typeof PROVIDER_PRESENTATIONS)[number];
export type ProviderId = KnownProviderPresentation["id"] | "unknown";

export const INITIAL_PROVIDER_SEARCH_STATUSES: Array<{
  id: string;
  label: string;
  status: "searching";
}> = [
  ...PROVIDER_PRESENTATIONS.map((provider) => ({
    id: provider.id,
    label: provider.label,
    status: "searching" as const,
  })),
] as const;

export type ProviderPresentation = {
  id: ProviderId;
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

export function resolveProviderPresentation(source: unknown, unknownLabel = "Unknown"): ProviderPresentation {
  const rawSource = typeof source === "string" ? source.trim() : "";
  if (!rawSource) {
    return {
      id: "unknown",
      label: unknownLabel,
      rawSource: null,
    };
  }

  const provider = PROVIDER_PRESENTATIONS.find((candidate) =>
    candidate.aliases.some((alias) => sourceIncludesAlias(rawSource, alias)),
  );
  if (provider) return { id: provider.id, label: provider.label, rawSource };

  return {
    id: "unknown",
    label: rawSource,
    rawSource,
  };
}
