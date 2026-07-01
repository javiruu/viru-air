import React from "react";

export type QuickSearchSummaryChip = {
  id: string;
  label: string;
  tone?: "route" | "search" | "result" | "advanced";
};

type QuickSearchSummaryChipsProps = {
  title: string;
  chips: QuickSearchSummaryChip[];
};

export function QuickSearchSummaryChips({ title, chips }: QuickSearchSummaryChipsProps) {
  if (chips.length === 0) return null;

  return (
    <section className="qs-summary-chips-panel" aria-label={title} data-ui="qs-summary-chips">
      <span className="qs-summary-chips-title">{title}</span>
      <div className="qs-summary-chips-list">
        {chips.map((chip) => (
          <span key={chip.id} className={`qs-summary-chip-compact qs-summary-chip-compact-${chip.tone ?? "search"}`}>
            {chip.label}
          </span>
        ))}
      </div>
    </section>
  );
}
