import { UsersRound } from "lucide-react";

import { useI18n } from "@/i18n";
import type { CommunityPriceAggregate } from "@/modules/watchlist/types";

type CommunityPriceReferenceBandProps = {
  readonly aggregate: CommunityPriceAggregate | undefined;
};

export function CommunityPriceReferenceBand({
  aggregate,
}: CommunityPriceReferenceBandProps) {
  const { t, localeTag } = useI18n();
  if (
    !aggregate?.is_public ||
    aggregate.min_price === null ||
    aggregate.max_price === null
  ) {
    return null;
  }
  const formatter = new Intl.NumberFormat(localeTag, { maximumFractionDigits: 0 });
  const range = `${formatter.format(aggregate.min_price)}–${formatter.format(aggregate.max_price)}`;

  return (
    <div className="community-reference-band" role="status">
      <UsersRound aria-hidden="true" />
      <div>
        <strong>{t("watchlist.communitySignals.referenceTitle")}</strong>
        <span>{t("watchlist.communitySignals.referenceRange", { range })}</span>
      </div>
    </div>
  );
}
