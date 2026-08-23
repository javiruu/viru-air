import { Check, Plane, UsersRound } from "lucide-react";

import { useI18n } from "@/i18n";
import { getCommunityHubIndicator } from "@/modules/watchlist/communityHubPresentation";
import type { Watch } from "@/modules/watchlist/types";

type CommunityHubButtonProps = {
  readonly watch: Watch;
  readonly onOpen: (watch: Watch, trigger: HTMLButtonElement) => void;
  readonly variant?: "default" | "ticket";
};

export function CommunityHubButton({
  watch,
  onOpen,
  variant = "default",
}: CommunityHubButtonProps) {
  const { t } = useI18n();
  const indicator = getCommunityHubIndicator(watch.community_pricing);
  const label = t(`watchlist.communityPricing.indicator.${indicator}`, {
    origin: watch.origin_iata,
    destination: watch.destination_iata,
  });

  return (
    <button
      className={`watch-community-hub-button is-${indicator} ${variant === "ticket" ? "watch-community-hub-button--ticket" : ""}`}
      type="button"
      aria-label={label}
      aria-haspopup="dialog"
      title={label}
      onClick={(event) => {
        event.stopPropagation();
        onOpen(watch, event.currentTarget);
      }}
    >
      {variant === "ticket" ? (
        <>
          <span className="watch-ticket-community-orbit" aria-hidden="true" />
          <Plane aria-hidden="true" />
        </>
      ) : <UsersRound aria-hidden="true" />}
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
