export type ScoreBand = "high" | "midHigh" | "midLow" | "low";

export function getScoreBand(score: number): ScoreBand {
  if (score >= 70) return "high";
  if (score >= 50) return "midHigh";
  if (score >= 30) return "midLow";
  return "low";
}

export function getScoreClass(score: number): string {
  const band = getScoreBand(score);
  return `reco-score-band-${band}`;
}

export function getScoreLabelKey(score: number): string {
  const band = getScoreBand(score);
  return `recommendations.scoreBand.${band}`;
}
