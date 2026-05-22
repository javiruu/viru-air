import React from "react";

import { useI18n } from "@/i18n";

export function DoorToDoorLoadingState() {
  const { t } = useI18n();
  return (
    <section className="panel d2d-loading-state" role="status" aria-live="polite">
      <div className="d2d-loading-radar" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <div>
        <h2>{t("doorToDoor.states.loadingTitle")}</h2>
        <p className="panel-note">{t("doorToDoor.states.loadingBody")}</p>
      </div>
    </section>
  );
}