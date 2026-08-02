import { TrendingUp, UsersRound } from "lucide-react";

import { useI18n } from "@/i18n";
import type { CommunityRouteInsight } from "@/modules/community-routes/communityRoutesTypes";

type CommunityRouteSignalProps = {
  readonly watchersCount: number;
  readonly insight: CommunityRouteInsight | undefined;
};

export function CommunityRouteSignal({
  watchersCount,
  insight,
}: CommunityRouteSignalProps) {
  const { t } = useI18n();
  const showWatchers = watchersCount > 5;
  const isTrending = insight?.is_trending === true;
  if (!showWatchers && !isTrending) return null;

  const label = showWatchers && isTrending
    ? t("watchlist.communitySignals.combined", { count: watchersCount })
    : showWatchers
      ? t("watchlist.communitySignals.watching", { count: watchersCount })
      : t("watchlist.communitySignals.trending");

  return (
    <span className="community-watch-signal">
      {isTrending ? <TrendingUp aria-hidden="true" /> : <UsersRound aria-hidden="true" />}
      {label}
    </span>
  );
}
