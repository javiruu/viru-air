import React from "react";

import { useI18n } from "@/i18n";
import type { DoorToDoorCorridor } from "@/modules/door-to-door/types";

type Props = {
  hasWatch: boolean;
  corridors: DoorToDoorCorridor[];
  corridorsLoaded: boolean;
};

function statusTone(status: DoorToDoorCorridor["status"]): string {
  if (status === "verified") return "success";
  if (status === "verified_limited") return "warning";
  return "info";
}

export function DoorToDoorEmptyState({ hasWatch, corridors, corridorsLoaded }: Props) {
  const { t } = useI18n();
  const verified = corridors.filter((c) => c.status === "verified" || c.status === "verified_limited");
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

      {corridorsLoaded && verified.length > 0 ? (
        <aside className="d2d-empty-corridors" aria-label={t("doorToDoor.corridors.title")}>
          <header className="d2d-empty-corridors-head">
            <h3>{t("doorToDoor.corridors.title")}</h3>
            <p className="panel-note">{t("doorToDoor.corridors.body")}</p>
          </header>
          <ul className="d2d-empty-corridors-list">
            {verified.map((corridor) => (
              <li key={corridor.id} className="d2d-empty-corridor-item">
                <span className={`status-pill ${statusTone(corridor.status)}`}>
                  {t(`doorToDoor.corridors.status.${corridor.status}`)}
                </span>
                <strong>{corridor.origin_area}</strong>
                <span className="d2d-empty-corridor-arrow" aria-hidden="true">→</span>
                <strong>{corridor.destination_airport}</strong>
                {corridor.both_legs ? (
                  <span className="d2d-empty-corridor-pill" title={t("doorToDoor.corridors.bothLegs")}>
                    {t("doorToDoor.corridors.bothLegs")}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        </aside>
      ) : null}
    </section>
  );
}
