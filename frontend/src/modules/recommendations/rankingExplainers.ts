type Trend = "up" | "down" | "flat";

export type RankingReason = {
  key: string;
  tone: "positive" | "neutral" | "negative";
  params?: Record<string, string | number>;
};

type WeatherInfo = {
  temp_max?: number | null;
  temp_min?: number | null;
  precip_probability?: number | null;
} | null;

type RankingExplainerInput = {
  price: number;
  avg_price?: number | null;
  trend: Trend;
  weather?: WeatherInfo;
};

function safePercent(value: number): number {
  return Math.round(Math.abs(value));
}

export function buildRankingReasons(input: RankingExplainerInput): RankingReason[] {
  const reasons: RankingReason[] = [];
  const avgPrice = input.avg_price ?? null;

  if (avgPrice && avgPrice > 0) {
    const diffRatio = ((input.price - avgPrice) / avgPrice) * 100;
    if (diffRatio <= -10) {
      reasons.push({
        key: "recommendations.reasons.priceBelowAvg",
        tone: "positive",
        params: { percent: safePercent(diffRatio) },
      });
    } else if (diffRatio >= 10) {
      reasons.push({
        key: "recommendations.reasons.priceAboveAvg",
        tone: "negative",
        params: { percent: safePercent(diffRatio) },
      });
    } else {
      reasons.push({
        key: "recommendations.reasons.priceNearAvg",
        tone: "neutral",
      });
    }
  }

  if (input.trend === "down") {
    reasons.push({ key: "recommendations.reasons.trendDown", tone: "positive" });
  } else if (input.trend === "up") {
    reasons.push({ key: "recommendations.reasons.trendUp", tone: "negative" });
  } else {
    reasons.push({ key: "recommendations.reasons.trendFlat", tone: "neutral" });
  }

  const precip = input.weather?.precip_probability ?? null;
  if (typeof precip === "number") {
    if (precip >= 55) {
      reasons.push({
        key: "recommendations.reasons.weatherUnstable",
        tone: "negative",
        params: { percent: Math.round(precip) },
      });
    } else if (precip <= 30) {
      reasons.push({
        key: "recommendations.reasons.weatherStable",
        tone: "positive",
        params: { percent: Math.round(precip) },
      });
    }
  }

  return reasons.slice(0, 3);
}
