export type WeightKey = "price" | "speed" | "climate" | "trend" | "novelty";

export const DEFAULT_WEIGHTS: Record<WeightKey, number> = {
  price: 0.4,
  speed: 0.2,
  climate: 0.2,
  trend: 0.1,
  novelty: 0.1,
};

export type WeightImpactLine = {
  key: WeightKey;
  deltaPoints: number;
};

export type WeightPrioritySummary = {
  primary: WeightKey;
  secondary: WeightKey;
  percentMore: number;
};

function sortByWeightDesc(weights: Record<WeightKey, number>): WeightKey[] {
  return (Object.keys(weights) as WeightKey[]).sort((a, b) => weights[b] - weights[a]);
}

export function getWeightImpactLines(
  weights: Record<WeightKey, number>,
  baseline: Record<WeightKey, number> = DEFAULT_WEIGHTS,
): WeightImpactLine[] {
  return (Object.keys(weights) as WeightKey[]).map((key) => ({
    key,
    deltaPoints: Math.round((weights[key] - baseline[key]) * 100),
  }));
}

export function getWeightPrioritySummary(
  weights: Record<WeightKey, number>,
): WeightPrioritySummary | null {
  const [primary, secondary] = sortByWeightDesc(weights);
  if (!primary || !secondary) return null;
  if (weights[secondary] <= 0) {
    return { primary, secondary, percentMore: 100 };
  }
  const percentMore = Math.round((weights[primary] / weights[secondary] - 1) * 100);
  return { primary, secondary, percentMore: Math.max(0, percentMore) };
}
