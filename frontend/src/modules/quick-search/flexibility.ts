export type QuickSearchFlexPreset = "exact" | "plus-1" | "plus-2" | "plus-3" | "custom";

export function clampQuickSearchFlexDays(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.min(7, Math.max(0, Math.trunc(value)));
}

export function getQuickSearchFlexPreset(daysBefore: number, daysAfter: number): QuickSearchFlexPreset {
  if (daysBefore === 0 && daysAfter === 0) return "exact";
  if (daysBefore === 1 && daysAfter === 1) return "plus-1";
  if (daysBefore === 2 && daysAfter === 2) return "plus-2";
  if (daysBefore === 3 && daysAfter === 3) return "plus-3";
  return "custom";
}

export function formatQuickSearchFlexSummary(
  daysBefore: number,
  daysAfter: number,
  labels: {
    exact: string;
    plusOne: string;
    plusTwo: string;
    plusThree: string;
    customTemplate: string;
  },
): string {
  const preset = getQuickSearchFlexPreset(daysBefore, daysAfter);
  if (preset === "exact") return labels.exact;
  if (preset === "plus-1") return labels.plusOne;
  if (preset === "plus-2") return labels.plusTwo;
  if (preset === "plus-3") return labels.plusThree;
  return labels.customTemplate
    .replace("{before}", String(daysBefore))
    .replace("{after}", String(daysAfter));
}
