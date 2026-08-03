import {
  CheckCircle2,
  Flame,
  ShieldCheck,
  TicketCheck,
  UsersRound,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { useI18n } from "@/i18n";
import { apiFetch } from "@/modules/shared/api";
import { getCommunityHubParticipation } from "@/modules/watchlist/communityHubPresentation";
import type { Watch } from "@/modules/watchlist/types";

type ContributorStats = {
  total_contributions: number;
  streak_weeks: number;
};

type CommunityHubOverviewProps = {
  readonly watch: Watch;
  readonly isSaving: boolean;
  readonly onMarkPurchased: () => void;
  readonly onBeginContribution: () => void;
  readonly onDeleteResponse: () => void;
};

export function CommunityHubOverview({
  watch,
  isSaving,
  onMarkPurchased,
  onBeginContribution,
  onDeleteResponse,
}: CommunityHubOverviewProps) {
  const { t, localeTag } = useI18n();
  const [contributorStats, setContributorStats] = useState<ContributorStats | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiFetch<ContributorStats>("/watchlist/contributor-stats")
      .then((data) => {
        if (!cancelled) setContributorStats(data);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);
  const pricing = watch.community_pricing;
  const aggregate = pricing.aggregate;
  const participation = getCommunityHubParticipation(pricing);
  const numberFormatter = useMemo(
    () =>
      new Intl.NumberFormat(localeTag, {
        maximumFractionDigits: 2,
      }),
    [localeTag],
  );
  const currencyFormatter = useMemo(
    () =>
      new Intl.NumberFormat(localeTag, {
        style: "currency",
        currency: "EUR",
        maximumFractionDigits: 2,
      }),
    [localeTag],
  );
  const watchersRaw = Number(watch.watchers_count ?? 0);
  const watchersCount = Number.isFinite(watchersRaw)
    ? Math.max(0, Math.floor(watchersRaw))
    : 0;
  const publicRange =
    aggregate.is_public &&
    aggregate.min_price !== null &&
    aggregate.max_price !== null;
  const responsePrice =
    pricing.response?.flew && pricing.response.price_per_traveler !== null
      ? currencyFormatter.format(pricing.response.price_per_traveler)
      : null;

  return (
    <div className="community-hub-overview">
      <div className="community-hub-insights">
        <article className="community-hub-insight community-hub-insight--primary">
          <TicketCheck aria-hidden="true" />
          <span>{t("watchlist.communityPricing.routePriceLabel")}</span>
          <strong>
            {publicRange
              ? t("watchlist.communityPricing.aggregateRange", {
                  min: numberFormatter.format(aggregate.min_price ?? 0),
                  max: numberFormatter.format(aggregate.max_price ?? 0),
                })
              : t("watchlist.communityPricing.buildingRange")}
          </strong>
          <small>
            {publicRange
              ? t("watchlist.communityPricing.sampleCount", {
                  count: aggregate.sample_size,
                })
              : t("watchlist.communityPricing.thresholdProgress", {
                  count: aggregate.sample_size,
                  minimum: aggregate.minimum_sample_size,
                })}
          </small>
        </article>
        <article className="community-hub-insight">
          <UsersRound aria-hidden="true" />
          <span>{t("watchlist.communityPricing.routeWatchersLabel")}</span>
          <strong className="tabular-nums">{watchersCount}</strong>
          <small>
            {watchersCount === 1
              ? t("watchlist.communityPricing.routeWatcherSingle")
              : t("watchlist.communityPricing.routeWatchers", {
                  count: watchersCount,
                })}
          </small>
        </article>
      </div>

      <div className="community-hub-privacy">
        <ShieldCheck aria-hidden="true" />
        <p>
          <strong>{t("watchlist.communityPricing.privacyTitle")}</strong>
          <span>{t("watchlist.communityPricing.privacyBody")}</span>
        </p>
      </div>

      {contributorStats && contributorStats.streak_weeks >= 2 ? (
        <div className="community-hub-streak">
          <Flame aria-hidden="true" />
          <span>
            {t("watchlist.communityPricing.streakBanner", {
              weeks: contributorStats.streak_weeks,
              total: contributorStats.total_contributions,
            })}
          </span>
        </div>
      ) : null}

      <section className="community-hub-contribution">
        <span className="community-pricing-step-label">
          {t("watchlist.communityPricing.yourContribution")}
        </span>
        {participation === "purchase" ? (
          <>
            <h3>{t("watchlist.communityPricing.purchaseTitle")}</h3>
            <p>{t("watchlist.communityPricing.purchaseBody")}</p>
            <button
              className="btn-primary"
              type="button"
              disabled={isSaving}
              onClick={onMarkPurchased}
            >
              {isSaving
                ? t("watchlist.communityPricing.saving")
                : t("watchlist.communityPricing.markPurchased")}
            </button>
          </>
        ) : participation === "contribute" ? (
          <>
            <h3>{t("watchlist.communityPricing.contributeTitle")}</h3>
            <p>{t("watchlist.communityPricing.contributeBody")}</p>
            <button
              className="btn-primary"
              type="button"
              disabled={isSaving}
              onClick={onBeginContribution}
            >
              {t("watchlist.communityPricing.respond")}
            </button>
          </>
        ) : (
          <>
            <div className="community-hub-contributed">
              <CheckCircle2 aria-hidden="true" />
              <div>
                <h3>{t("watchlist.communityPricing.contributedTitle")}</h3>
                <p>
                  {responsePrice
                    ? t("watchlist.communityPricing.contributedPrice", {
                        price: responsePrice,
                      })
                    : t("watchlist.communityPricing.contributedNoFlight")}
                </p>
              </div>
            </div>
            <div className="community-pricing-actions">
              <button
                className="btn-secondary"
                type="button"
                disabled={isSaving}
                onClick={onBeginContribution}
              >
                {t("watchlist.communityPricing.editResponse")}
              </button>
              <button
                className="btn-ghost"
                type="button"
                disabled={isSaving}
                onClick={onDeleteResponse}
              >
                {t("watchlist.communityPricing.deleteResponse")}
              </button>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
