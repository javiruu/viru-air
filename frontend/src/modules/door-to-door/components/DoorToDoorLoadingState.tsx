import React from "react";

import { useI18n } from "@/i18n";
import { BoneyardLoad, LoadReference } from "@/modules/shared/BoneyardLoad";

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
      <BoneyardLoad name="door-to-door-results-load" className="d2d-loading-bones" ariaLabel={t("doorToDoor.states.loadingTitle")}>
        {[1, 2, 3].map((i) => (
          <div key={i} className="d2d-load-card">
            <LoadReference className="d2d-load-route" />
            <LoadReference className="d2d-load-meta" />
            <LoadReference className="d2d-load-price" />
          </div>
        ))}
      </BoneyardLoad>
    </section>
  );
}
