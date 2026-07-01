import React from "react";

export type QuickSearchSummaryChip = {
  id: string;
  label: string;
  tone?: "route" | "search" | "result" | "advanced";
};

type QuickSearchSummaryChipsProps = {
  title: string;
  chips: QuickSearchSummaryChip[];
  onOpenAdvanced?: () => void;
  moreOptionsLabel?: string;
};

export function QuickSearchSummaryChips(props: QuickSearchSummaryChipsProps) {
  const { title, chips } = props;
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
        {props.onOpenAdvanced && props.moreOptionsLabel ? (
          <button
            type="button"
            className="btn-ghost btn-compact qs-summary-chips-more"
            onClick={props.onOpenAdvanced}
            data-ui="qs-summary-chips-more"
          >
            <svg className="qs-inline-icon" viewBox="0 0 24 24" aria-hidden="true" width="16" height="16">
              <path
                d="M6 9l6 6 6-6"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            {props.moreOptionsLabel}
          </button>
        ) : null}
      </div>
    </section>
  );
}
