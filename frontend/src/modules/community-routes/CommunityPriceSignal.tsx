import { UsersRound } from "lucide-react";

import { useI18n } from "@/i18n";
import type { CommunityRouteInsight } from "@/modules/community-routes/communityRoutesTypes";

type CommunityPriceSignalProps = {
  readonly insight: CommunityRouteInsight | undefined;
  readonly localeTag: string;
};

export function CommunityPriceSignal({
  insight,
  localeTag,
}: CommunityPriceSignalProps) {
  const { t } = useI18n(localeTag);
  if (
    !insight ||
    insight.sample_size < 3 ||
    insight.min_price === null ||
    insight.max_price === null
  ) {
    return null;
  }
  const formatter = new Intl.NumberFormat(localeTag, {
    maximumFractionDigits: 0,
  });
  const range = `${formatter.format(insight.min_price)}–${formatter.format(insight.max_price)} €`;
  const copy = t("watchlist.communityPricing.publicAggregateInline", {
    count: insight.sample_size,
    range,
  });

  return (
    <p className="community-price-signal">
      <UsersRound aria-hidden="true" />
      <span>{copy}</span>
    </p>
  );
}
