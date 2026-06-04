import React from "react";

import { useI18n } from "@/i18n";

export function DoorToDoorLoadingState() {
  const { t } = useI18n();
  return (
    <section className="panel d2d-loading-state d2d-state-enter" role="status" aria-live="polite" aria-label={t("doorToDoor.states.loadingTitle")}>
      <div className="d2d-loading-header">
        <div className="d2d-loading-radar" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <div>
          <h2>{t("doorToDoor.states.loadingTitle")}</h2>
          <p className="panel-note">{t("doorToDoor.states.loadingBody")}</p>
        </div>
      </div>
      <div className="d2d-loading-skeletons" aria-hidden="true">
        {[1, 2, 3].map((i) => (
          <div key={i} className="d2d-skeleton-card">
            <div className="d2d-skeleton-line d2d-skeleton-route" />
            <div className="d2d-skeleton-line d2d-skeleton-meta" />
            <div className="d2d-skeleton-line d2d-skeleton-price" />
          </div>
        ))}
      </div>
    </section>
  );
}