import React from "react";

import { ZeroResultRelaxAction } from "@/modules/quick-search/types";

type Props = {
  searchState: "idle" | "loading" | "success" | "empty" | "error" | "rate";
  rateLimitSeconds: number;
  searchError: string | null;
  emptyStateMainTitle: string;
  locale: "es" | "en";
  zeroResultCauses: string[];
  visibleZeroResultCauses: string[];
  canExpandZeroResultCauses: boolean;
  emptyCausesExpanded: boolean;
  zeroResultActions: Array<{ id: ZeroResultRelaxAction; label: string }>;
  onToggleEmptyCauses: () => void;
  onRelaxAction: (action: ZeroResultRelaxAction) => void;
  onRunSearch: () => void;
  onEmptyCta: () => void;
  t: (key: any) => string;
};

export function QuickSearchStatePanels(props: Props) {
  if (props.searchState === "idle") {
    return (
      <div className="qs-state">
        <h3>{props.t("searchReadyTitle")}</h3>
        <p>{props.t("searchReadyText")}</p>
        <span className="muted">{props.t("searchReadyHint")}</span>
      </div>
    );
  }

  if (props.searchState === "rate") {
    return (
      <div className="qs-state">
        <h3>{props.t("rateLimitTitle")}</h3>
        <p>{props.t("rateLimitText")}</p>
        <span className="muted">{props.t("stateRateHint")}</span>
        <span className="muted">{props.t("rateLimitCountdown")} {props.rateLimitSeconds}s</span>
      </div>
    );
  }

  if (props.searchState === "error") {
    return (
      <div className="qs-state">
        <h3>{props.t("errorTitle")}</h3>
        <p>{props.searchError || props.t("searchFailed")}</p>
        <span className="muted">{props.t("stateErrorHint")}</span>
        <button type="button" className="btn-ghost" onClick={props.onRunSearch}>
          {props.t("errorRetry")}
        </button>
      </div>
    );
  }

  if (props.searchState === "empty") {
    return (
      <div className="qs-state">
        <h3 className="qs-empty-title">{props.emptyStateMainTitle}</h3>
        <p>{props.t("emptyText")}</p>
        <span className="muted">{props.t("stateEmptyHint")}</span>
        <button type="button" className="btn-search qs-empty-primary-cta" onClick={props.onEmptyCta}>
          {props.t("emptyCta")}
        </button>
        {props.zeroResultCauses.length > 0 ? (
          <div className="qs-empty-cause-block">
            <strong>{props.t("emptyLikelyCausesTitle")}</strong>
            <ul className="qs-empty-causes">
              {props.visibleZeroResultCauses.map((cause, idx) => (
                <li key={`${cause}-${idx}`}>{cause}</li>
              ))}
            </ul>
            {props.canExpandZeroResultCauses ? (
              <button
                type="button"
                className="btn-ghost btn-compact"
                aria-expanded={props.emptyCausesExpanded}
                onClick={props.onToggleEmptyCauses}
              >
                {props.emptyCausesExpanded ? props.t("emptyShowLess") : props.t("emptyShowMore")}
              </button>
            ) : null}
          </div>
        ) : null}
        {props.zeroResultActions.length > 0 ? (
          <div className="qs-empty-actions">
            <span className="muted">{props.t("emptyRelaxActionsTitle")}</span>
            {props.zeroResultActions.map((action) => (
              <button key={action.id} type="button" className="btn-ghost" onClick={() => props.onRelaxAction(action.id)}>
                {action.label}
              </button>
            ))}
          </div>
        ) : null}
      </div>
    );
  }

  return null;
}
