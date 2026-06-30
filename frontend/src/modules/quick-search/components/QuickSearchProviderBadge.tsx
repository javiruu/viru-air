import React from "react";

import { resolveQuickSearchProviderPresentation } from "@/modules/quick-search/providerPresentation";
import { RyanairIcon, VuelingIcon, WizzAirIcon, DuffelIcon, GenericProviderIcon } from "@/icons";

function ProviderLogo({ providerId }: { providerId: "ryanair" | "vueling" | "wizzair" | "duffel" | "unknown" }) {
  if (providerId === "ryanair") {
    return <RyanairIcon className="qs-provider-badge-logo" size={24} />;
  }
  if (providerId === "vueling") {
    return <VuelingIcon className="qs-provider-badge-logo" size={24} />;
  }
  if (providerId === "wizzair") {
    return <WizzAirIcon className="qs-provider-badge-logo" size={24} />;
  }
  if (providerId === "duffel") {
    return <DuffelIcon className="qs-provider-badge-logo" size={24} />;
  }
  return <GenericProviderIcon className="qs-provider-badge-logo" size={24} />;
}

type Props = {
  source: unknown;
  unknownLabel?: string;
};

export function QuickSearchProviderBadge({ source, unknownLabel = "Unknown" }: Props) {
  const provider = resolveQuickSearchProviderPresentation(source, unknownLabel);

  return (
    <span className={`qs-provider-badge qs-provider-badge--${provider.id}`}>
      <ProviderLogo providerId={provider.id} />
      <span>{provider.label}</span>
    </span>
  );
}
