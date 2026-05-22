import React from "react";

import { useI18n } from "@/i18n";

export function DoorToDoorEmptyState({ hasWatch }: { hasWatch: boolean }) {
  const { t } = useI18n();
  return (
    <section className="panel panel-soft d2d-state-card d2d-empty-state">
      <span className="d2d-radar-dot" aria-hidden="true" />
      <h2>{hasWatch ? t("doorToDoor.states.emptyTitleWithWatch") : t("doorToDoor.states.emptyTitleNoWatch")}</h2>
      <p>{hasWatch ? t("doorToDoor.states.emptyBodyWithWatch") : t("doorToDoor.states.emptyBodyNoWatch")}</p>
    </section>
  );
}