import React from "react";

import { resolveQuickSearchProviderPresentation } from "@/modules/quick-search/providerPresentation";

function ProviderLogo({ providerId }: { providerId: "ryanair" | "wizzair" | "duffel" | "unknown" }) {
  if (providerId === "ryanair") {
    return (
      <svg className="qs-provider-badge-logo" viewBox="0 0 24 24" aria-hidden="true">
        <rect x="1.5" y="1.5" width="21" height="21" rx="6" fill="#123A83" />
        <path
          d="M8 15.8c2.7-.4 5-.6 7-.5 1.5.1 2.5.4 3.2.8-.9-1.8-2.4-3.7-4.6-5.9l-1.5 2.2-1.8-4.9 4.9 1.8-1.5 2c2.1 1.7 3.8 3.6 5 5.8-2.6-.8-5.9-.9-10-.3z"
          fill="#F7C948"
        />
      </svg>
    );
  }

  if (providerId === "wizzair") {
    return (
      <svg className="qs-provider-badge-logo" viewBox="0 0 24 24" aria-hidden="true">
        <rect x="1.5" y="1.5" width="21" height="21" rx="6" fill="#C2187A" />
        <path
          d="M5.5 8.2h2.3l1.6 6.1 1.4-4 1.4 4 1.6-6.1h2.3l-2.7 8.6h-2.1L12 12.9l-1.4 3.9H8.4z"
          fill="#fff"
        />
        <path d="M6 17.6h12" stroke="#59D4FF" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    );
  }

  if (providerId === "duffel") {
    return (
      <svg className="qs-provider-badge-logo" viewBox="0 0 24 24" aria-hidden="true">
        <rect x="1.5" y="1.5" width="21" height="21" rx="6" fill="#1F2937" />
        <path
          d="M7.5 7.5h4.8c2.8 0 4.7 1.8 4.7 4.5s-1.9 4.5-4.7 4.5H7.5zm2.2 2v5h2.3c1.6 0 2.7-1 2.7-2.5s-1.1-2.5-2.7-2.5z"
          fill="#F3F4F6"
        />
      </svg>
    );
  }

  return (
    <svg className="qs-provider-badge-logo" viewBox="0 0 24 24" aria-hidden="true">
      <rect x="1.5" y="1.5" width="21" height="21" rx="6" fill="#CBD5E1" />
      <path d="M12 6.5v11M6.5 12h11" stroke="#475569" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
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
