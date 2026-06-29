import React from "react";
import {
  AlertTriangle,
  Clock3,
  PlaneTakeoff,
  Radar,
  Search,
  SlidersHorizontal,
  type LucideIcon,
} from "lucide-react";

import type { ZeroResultRelaxAction } from "@/modules/quick-search/types";
import type { QuickSearchCopyKey } from "@/modules/shared/quickSearchCopy";

type StateTone = "idle" | "loading" | "empty" | "error" | "rate";

function StateSignal({ tone, Icon }: { readonly tone: StateTone; readonly Icon: LucideIcon }) {
  return (
    <div className={`qs-state-visual qs-state-visual-${tone}`} aria-hidden="true">
      <span className="qs-state-radar-ring" />
      <span className="qs-state-route-line" />
      <span className="qs-state-node qs-state-node-origin" />
      <span className="qs-state-node qs-state-node-destination" />
      <span className="qs-state-icon-shell">
        <Icon className="qs-state-signal-icon" />
      </span>
    </div>
  );
}

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
  t: (key: QuickSearchCopyKey) => string;
};

export function QuickSearchStatePanels(props: Props) {
  if (props.searchState === "idle") {
    return (
      <div className="qs-state qs-state-idle">
        <StateSignal tone="idle" Icon={PlaneTakeoff} />
        <div className="qs-state-copy">
          <span className="qs-state-kicker">{props.t("stateIdleKicker")}</span>
          <h3>{props.t("searchReadyTitle")}</h3>
          <p>{props.t("searchReadyText")}</p>
          <span className="muted">{props.t("searchReadyHint")}</span>
        </div>
      </div>
    );
  }

  if (props.searchState === "loading") {
    return (
      <div className="qs-state qs-state-loading" aria-live="polite">
        <StateSignal tone="loading" Icon={Radar} />
        <div className="qs-state-copy">
          <span className="qs-state-kicker">{props.t("stateLoadingKicker")}</span>
          <h3>{props.t("loadingTitle")}</h3>
          <p>{props.t("loadingText")}</p>
          <span className="muted">{props.t("loadingSubcheckTitle")}</span>
        </div>
      </div>
    );
  }

  if (props.searchState === "rate") {
    return (
      <div className="qs-state qs-state-rate">
        <StateSignal tone="rate" Icon={Clock3} />
        <div className="qs-state-copy">
          <span className="qs-state-kicker">{props.t("stateRateKicker")}</span>
          <h3>{props.t("rateLimitTitle")}</h3>
          <p>{props.t("rateLimitText")}</p>
          <span className="muted">{props.t("stateRateHint")}</span>
          <span className="muted">{props.t("rateLimitCountdown")} {props.rateLimitSeconds}s</span>
        </div>
      </div>
    );
  }

  if (props.searchState === "error") {
    return (
      <div className="qs-state qs-state-error">
        <StateSignal tone="error" Icon={AlertTriangle} />
        <div className="qs-state-copy">
          <span className="qs-state-kicker">{props.t("stateErrorKicker")}</span>
          <h3>{props.t("errorTitle")}</h3>
          <p>{props.searchError || props.t("searchFailed")}</p>
          <span className="muted">{props.t("stateErrorHint")}</span>
          <button type="button" className="btn-ghost qs-state-inline-action" onClick={props.onRunSearch}>
            <Search className="qs-button-icon" aria-hidden="true" />
            {props.t("errorRetry")}
          </button>
        </div>
      </div>
    );
  }

  if (props.searchState === "empty") {
    return (
      <div className="qs-state qs-state-empty">
        <StateSignal tone="empty" Icon={Radar} />
        <div className="qs-state-copy">
          <span className="qs-state-kicker">{props.t("stateEmptyKicker")}</span>
          <h3 className="qs-empty-title">{props.emptyStateMainTitle}</h3>
          <p>{props.t("emptyText")}</p>
          <span className="muted">{props.t("stateEmptyHint")}</span>
          <button type="button" className="btn-search qs-empty-primary-cta" onClick={props.onEmptyCta}>
            <SlidersHorizontal className="qs-button-icon" aria-hidden="true" />
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
                  <SlidersHorizontal className="qs-button-icon" aria-hidden="true" />
                  {action.label}
                </button>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    );
  }

  return null;
}
