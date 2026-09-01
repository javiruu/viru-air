export type HeroOpportunityWatch = {
  latest_snapshot?: {
    raw_price: number;
    raw_currency: string;
  } | null;
};

export type HeroOpportunityPriceSummary = {
  latest_price: number | null;
  delta_pct: number | null;
};

export type HeroOpportunityMetrics = {
  latestPrice: number | null;
  currency: string | null;
  deltaPct: number | null;
};

export function getHeroOpportunityMetrics(
  watch: HeroOpportunityWatch | null,
  summary: HeroOpportunityPriceSummary | null,
): HeroOpportunityMetrics {
  return {
    latestPrice: watch?.latest_snapshot?.raw_price ?? summary?.latest_price ?? null,
    currency: watch?.latest_snapshot?.raw_currency ?? null,
    deltaPct: summary?.delta_pct ?? null,
  };
}
