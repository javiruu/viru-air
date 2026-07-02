import React from "react";

export type QuickSearchSummaryChip = {
  id: string;
  label: string;
  tone?: "route" | "search" | "result" | "advanced";
  emphasis?: boolean;
};

type QuickSearchSummaryChipsProps = {
  title: string;
  headline: string;
  caption: string;
  chips: QuickSearchSummaryChip[];
  missingBadges?: string[];
  onOpenAdvanced?: () => void;
  moreOptionsLabel?: string;
};

export function QuickSearchSummaryChips(props: QuickSearchSummaryChipsProps) {
  const { title, headline, caption, chips, missingBadges = [] } = props;
  if (chips.length === 0) return null;

  return (
    <section className="qs-summary-chips-panel" aria-label={title} data-ui="qs-summary-chips">
      <div className="qs-summary-chips-head">
        <span className="qs-summary-chips-title">{title}</span>
        <strong>{headline}</strong>
        <p>{caption}</p>
      </div>
      <div className="qs-summary-chips-list">
        {chips.map((chip) => (
          <span
            key={chip.id}
            className={[
              "qs-summary-chip-compact",
              `qs-summary-chip-compact-${chip.tone ?? "search"}`,
              chip.emphasis ? "qs-summary-chip-compact-highlight" : "",
            ].filter(Boolean).join(" ")}
          >
            {chip.label}
          </span>
        ))}
        {props.onOpenAdvanced && props.moreOptionsLabel ? (
          <button
            type="button"
            className="btn-ghost btn-compact qs-summary-chips-more"
            onClick={props.onOpenAdvanced}
            aria-haspopup="dialog"
            aria-controls="qs-advanced-drawer"
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
      {missingBadges.length > 0 ? (
        <div className="qs-summary-missing">
          {missingBadges.map((badge) => (
            <span key={badge} className="qs-summary-missing-badge">{badge}</span>
          ))}
        </div>
      ) : null}
    </section>
  );
}
