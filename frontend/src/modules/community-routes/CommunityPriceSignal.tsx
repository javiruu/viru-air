import { UsersRound } from "lucide-react";

import type { CommunityRouteInsight } from "@/modules/community-routes/communityRoutesTypes";

type CommunityPriceSignalProps = {
  readonly insight: CommunityRouteInsight | undefined;
  readonly localeTag: string;
};

export function CommunityPriceSignal({
  insight,
  localeTag,
}: CommunityPriceSignalProps) {
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
  const copy = localeTag.toLowerCase().startsWith("es")
    ? `${insight.sample_size} viajeros de Viru pagaron ${range} por persona en esta ruta.`
    : `${insight.sample_size} Viru travelers paid ${range} per person on this route.`;

  return (
    <p className="community-price-signal">
      <UsersRound aria-hidden="true" />
      <span>{copy}</span>
    </p>
  );
}
