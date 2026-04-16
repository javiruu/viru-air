import React from "react";

import { QuickSearchLoadingSubcheckStatus } from "@/modules/quick-search/types";

type LoadingSubcheck = {
  id: string;
  label: string;
  status: QuickSearchLoadingSubcheckStatus;
};

type Props = {
  show: boolean;
  loadingVisualHold: boolean;
  loadingAria: string;
  loadingPhaseLabel: string;
  progressPercent: number;
  loadingSubcheckTitle: string;
  loadingSubchecks: LoadingSubcheck[];
  loadingSubcheckDone: string;
  loadingSubcheckActive: string;
  prefersReducedMotion: boolean;
  boardedCount: number;
  showBoarding: boolean;
  boardingPassengers: number;
  loadingTitle: string;
  loadingText: string;
};

export function QuickSearchLoadingProgress(props: Props) {
  if (!props.show && !props.loadingVisualHold) return null;
  return (
    <div className="qs-state qs-state-loading">
      <section
        className="qs-boarding"
        role="status"
        aria-live="polite"
        aria-label={props.loadingAria}
        style={{ width: "100%", maxWidth: 520, margin: "0 auto 8px", minHeight: 110 }}
      >
        <div
          className="qs-boarding-head"
          style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, marginBottom: 8 }}
        >
          <span className="muted">{props.loadingPhaseLabel}</span>
          <strong>{props.progressPercent}%</strong>
        </div>
        <div className="qs-boarding-subchecks" aria-label={props.loadingSubcheckTitle}>
          <span className="qs-boarding-subchecks-title">{props.loadingSubcheckTitle}</span>
          <ul className="qs-boarding-subchecks-list">
            {props.loadingSubchecks.map((item) => (
              <li key={item.id} className={`qs-boarding-subcheck qs-boarding-subcheck--${item.status}`}>
                <span className="qs-boarding-subcheck-dot" aria-hidden="true" />
                <span className="qs-boarding-subcheck-text">{item.label}</span>
                <span className="qs-boarding-subcheck-state">
                  {item.status === "done"
                    ? props.loadingSubcheckDone
                    : item.status === "active"
                      ? props.loadingSubcheckActive
                      : ""}
                </span>
              </li>
            ))}
          </ul>
        </div>
        <div className="qs-boarding-track qs-loading-progress" aria-hidden="true">
          <div
            style={{
              width: `${props.progressPercent}%`,
              height: 10,
              borderRadius: 999,
              background: "var(--qs-boarding-ink, #0F172A)",
              transition: props.prefersReducedMotion ? "none" : "width 180ms ease",
              position: "absolute",
              left: 10,
              right: "auto",
              top: 10,
            }}
          />
          <div
            className="qs-boarding-passengers"
            data-no-marker="true"
            style={{
              ["--qs-board-step" as any]: props.boardedCount,
              visibility: props.showBoarding ? "visible" : "hidden",
            }}
          >
            {Array.from({ length: props.boardingPassengers }).map((_, idx) => {
              const isHidden = !props.showBoarding || idx < props.boardedCount;
              return (
                <span
                  key={`boarding-passenger-${idx}`}
                  style={{ visibility: isHidden ? "hidden" : "visible" }}
                />
              );
            })}
          </div>
          <span
            className={`qs-boarding-plane${props.progressPercent >= 95 && props.progressPercent < 100 ? " qs-boarding-plane--ready" : ""}${props.progressPercent === 100 ? " qs-boarding-plane--takeoff" : ""}`}
          />
        </div>
      </section>
      <h3>{props.loadingTitle}</h3>
      <p>{props.loadingText}</p>
      <div className="qs-skeleton-cards" aria-hidden="true">
        {Array.from({ length: 4 }).map((_, idx) => (
          <article key={`skeleton-card-${idx}`} className="qs-skeleton-card">
            <div className="qs-skeleton-row qs-skeleton-route" />
            <div className="qs-skeleton-row qs-skeleton-meta" />
            <div className="qs-skeleton-row qs-skeleton-meta short" />
            <div className="qs-skeleton-row qs-skeleton-price" />
          </article>
        ))}
      </div>
    </div>
  );
}
