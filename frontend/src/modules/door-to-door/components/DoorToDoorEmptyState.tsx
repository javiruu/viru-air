import React from "react";

import { useI18n } from "@/i18n";

export function DoorToDoorEmptyState({ hasWatch }: { hasWatch: boolean }) {
  const { t } = useI18n();
  return (
    <section className="panel panel-soft d2d-state-card d2d-empty-state d2d-state-enter" role="status">
      <div className="d2d-empty-visual" aria-hidden="true">
        <div className="d2d-empty-route">
          <span className="d2d-empty-dot d2d-empty-origin" />
          <span className="d2d-empty-line" />
          <span className="d2d-empty-plane">✈</span>
          <span className="d2d-empty-line" />
          <span className="d2d-empty-dot d2d-empty-dest" />
        </div>
        <span className="d2d-radar-dot" aria-hidden="true" />
      </div>
      <h2>{hasWatch ? t("doorToDoor.states.emptyTitleWithWatch") : t("doorToDoor.states.emptyTitleNoWatch")}</h2>
      <p>{hasWatch ? t("doorToDoor.states.emptyBodyWithWatch") : t("doorToDoor.states.emptyBodyNoWatch")}</p>
    </section>
  );
}