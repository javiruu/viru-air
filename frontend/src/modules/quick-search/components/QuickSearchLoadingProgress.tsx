import React from "react";

import { QuickSearchLoadingSubcheckStatus } from "@/modules/quick-search/types";
import { RyanairIcon, WizzAirIcon, GenericProviderIcon } from "@/icons";

type LoadingSubcheck = {
  id: string;
  label: string;
  status: QuickSearchLoadingSubcheckStatus;
};

export type ProviderSearchStatus = {
  id: string;
  label: string;
  status: "searching" | "found" | "error" | "pending";
  resultsCount?: number;
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
  loadingTotalText: string;
  loadingProgressText: string;
  loadingScopeText: string;
  /** Provider search statuses shown during loading */
  providerStatuses?: ProviderSearchStatus[];
};

function ProviderSearchIcon({ status }: { status: ProviderSearchStatus["status"] }) {
  if (status === "searching") {
    return (
      <span className="qs-provider-loading-dots" aria-label="Buscando...">
        <span className="qs-provider-loading-dot" />
        <span className="qs-provider-loading-dot" />
        <span className="qs-provider-loading-dot" />
      </span>
    );
  }
  if (status === "found") {
    return (
      <span className="qs-provider-status-icon qs-provider-status-icon--found" aria-label="Resultados encontrados">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.15" />
          <path d="M8 12l3 3 5-6" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
    );
  }
  if (status === "error") {
    return (
      <span className="qs-provider-status-icon qs-provider-status-icon--error" aria-label="Error">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.15" />
          <path d="M8 8l8 8M16 8l-8 8" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
        </svg>
      </span>
    );
  }
  // pending
  return (
    <span className="qs-provider-status-icon qs-provider-status-icon--pending" aria-label="Pendiente">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.1" />
        <circle cx="12" cy="12" r="4" fill="currentColor" opacity="0.3" />
      </svg>
    </span>
  );
}

function ProviderLogoSmall({ providerId }: { providerId: string }) {
  if (providerId === "ryanair") {
    return <RyanairIcon className="qs-provider-mini-logo" size={24} />;
  }
  if (providerId === "wizzair") {
    return <WizzAirIcon className="qs-provider-mini-logo" size={24} />;
  }
  return <GenericProviderIcon className="qs-provider-mini-logo" size={24} />;
}

export function QuickSearchLoadingProgress(props: Props) {
  if (!props.show && !props.loadingVisualHold) return null;
  const hasProviders = props.providerStatuses && props.providerStatuses.length > 0;
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
              background: "var(--qs-boarding-ink, var(--color-text-primary))",
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

        {/* Provider search status badges */}
        {hasProviders && (
          <div className="qs-provider-loading-badges" role="status" aria-label="Estado de búsqueda por aerolínea">
            {props.providerStatuses!.map((pv) => (
              <div
                key={pv.id}
                className={`qs-provider-loading-badge qs-provider-loading-badge--${pv.status}`}
              >
                <ProviderLogoSmall providerId={pv.id} />
                <span className="qs-provider-loading-name">{pv.label}</span>
                <ProviderSearchIcon status={pv.status} />
                {pv.resultsCount !== undefined && pv.resultsCount > 0 && (
                  <span className="qs-provider-loading-count">{pv.resultsCount}</span>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
      <h3>{props.loadingTitle}</h3>
      <p>{props.loadingText}</p>
      <div className="qs-loading-kpis" aria-live="polite">
        <p className="qs-loading-kpi">{props.loadingTotalText}</p>
        <p className="qs-loading-kpi"><strong>{props.loadingProgressText}</strong></p>
        <p className="qs-loading-kpi qs-loading-kpi-muted">{props.loadingScopeText}</p>
      </div>
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
