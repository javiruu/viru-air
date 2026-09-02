import React from "react";

import { resolveQuickSearchProviderPresentation } from "@/modules/quick-search/providerPresentation";
import type { QuickSearchProviderId } from "@/modules/quick-search/providerPresentation";
import { RyanairIcon, VuelingIcon, WizzAirIcon, EasyJetIcon, IberiaIcon, DuffelIcon, GenericProviderIcon } from "@/icons";

function ProviderLogo({
  providerId,
  className,
  size,
}: {
  providerId: QuickSearchProviderId;
  className: string;
  size: number;
}) {
  if (providerId === "ryanair") {
    return <RyanairIcon className={className} size={size} />;
  }
  if (providerId === "vueling") {
    return <VuelingIcon className={className} size={size} />;
  }
  if (providerId === "wizzair") {
    return <WizzAirIcon className={className} size={size} />;
  }
  if (providerId === "easyjet") {
    return <EasyJetIcon className={className} size={size} />;
  }
  if (providerId === "iberia") {
    return <IberiaIcon className={className} size={size} />;
  }
  if (providerId === "duffel") {
    return <DuffelIcon className={className} size={size} />;
  }
  return <GenericProviderIcon className={className} size={size} />;
}

type Props = {
  source: unknown;
  unknownLabel?: string;
  variant?: "badge" | "logo";
  href?: string;
  linkAriaLabel?: string;
  onClick?: () => void;
};

export function QuickSearchProviderBadge({
  source,
  unknownLabel = "Unknown",
  variant = "badge",
  href,
  linkAriaLabel,
  onClick,
}: Props) {
  const provider = resolveQuickSearchProviderPresentation(source, unknownLabel);

  if (variant === "logo") {
    const logoContent = (
      <>
        <ProviderLogo providerId={provider.id} className="qs-provider-logo-mark" size={32} />
        <span className="qs-provider-logo-name">{provider.label}</span>
      </>
    );

    if (href) {
      return (
        <a
          className={`qs-provider-logo qs-provider-logo--${provider.id}`}
          href={href}
          target="_blank"
          rel="noreferrer"
          aria-label={linkAriaLabel ?? provider.label}
          title={provider.label}
          onClick={onClick}
        >
          {logoContent}
        </a>
      );
    }

    return (
      <span
        className={`qs-provider-logo qs-provider-logo--${provider.id}`}
        aria-label={provider.label}
        title={provider.label}
      >
        {logoContent}
      </span>
    );
  }

  return (
    <span className={`qs-provider-badge qs-provider-badge--${provider.id}`}>
      <ProviderLogo providerId={provider.id} className="qs-provider-badge-logo" size={24} />
      <span>{provider.label}</span>
    </span>
  );
}
