import React from "react";

import { resolveQuickSearchProviderPresentation } from "@/modules/quick-search/providerPresentation";
import { RyanairIcon, WizzAirIcon, GenericProviderIcon } from "@/icons";

const DUFFEL_ICON_COLOR = "#1F2937";

function ProviderLogo({ providerId }: { providerId: "ryanair" | "wizzair" | "duffel" | "unknown" }) {
  if (providerId === "ryanair") {
    return <RyanairIcon className="qs-provider-badge-logo" size={24} />;
  }
  if (providerId === "wizzair") {
    return <WizzAirIcon className="qs-provider-badge-logo" size={24} />;
  }
  if (providerId === "duffel") {
    return (
      <svg className="qs-provider-badge-logo" viewBox="0 0 24 24" fill={DUFFEL_ICON_COLOR} aria-hidden="true">
        <rect x="1.5" y="1.5" width="21" height="21" rx="6" />
        <path
          d="M7.5 7.5h4.8c2.8 0 4.7 1.8 4.7 4.5s-1.9 4.5-4.7 4.5H7.5zm2.2 2v5h2.3c1.6 0 2.7-1 2.7-2.5s-1.1-2.5-2.7-2.5z"
          fill="#F3F4F6"
        />
      </svg>
    );
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
