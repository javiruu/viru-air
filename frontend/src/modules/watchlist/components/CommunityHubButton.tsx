import { Check, Plane } from "lucide-react";

import { useI18n } from "@/i18n";
import { getCommunityHubIndicator } from "@/modules/watchlist/communityHubPresentation";
import type { Watch } from "@/modules/watchlist/types";

type CommunityHubButtonProps = {
  readonly watch: Watch;
  readonly onOpen: (watch: Watch, trigger: HTMLButtonElement) => void;
};

export function CommunityHubButton({
  watch,
  onOpen,
}: CommunityHubButtonProps) {
  const { t } = useI18n();
  const indicator = getCommunityHubIndicator(watch.community_pricing);
  const label = t(`watchlist.communityPricing.indicator.${indicator}`, {
    origin: watch.origin_iata,
    destination: watch.destination_iata,
  });

  return (
    <button
      className={`watch-community-hub-button is-${indicator}`}
      type="button"
      aria-label={label}
      aria-haspopup="dialog"
      title={label}
      onClick={(event) => {
        event.stopPropagation();
        onOpen(watch, event.currentTarget);
      }}
    >
      <Plane aria-hidden="true" />
      {indicator === "contributed" ? (
        <span className="watch-community-hub-check" aria-hidden="true">
          <Check />
        </span>
      ) : (
        <span className="watch-community-hub-signal" aria-hidden="true" />
      )}
    </button>
  );
}
