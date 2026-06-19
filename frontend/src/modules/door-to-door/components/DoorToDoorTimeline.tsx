import React from "react";

import { useI18n } from "@/i18n";
import type { DoorToDoorFlight, DoorToDoorOption } from "@/modules/door-to-door/types";

function shortTime(value?: string | null, fallback?: string) {
  if (!value) return fallback ?? "--";
  return new Intl.DateTimeFormat("es-ES", { hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

function timeRangeLabel(departureAt: string | null | undefined, arrivalAt: string | null | undefined, fallback: string) {
  if (!departureAt || !arrivalAt) return fallback;
  return `${shortTime(departureAt)} - ${shortTime(arrivalAt)}`;
}

export function DoorToDoorTimeline({ option, flight }: { option: DoorToDoorOption | null; flight?: DoorToDoorFlight | null }) {
  const { t } = useI18n();
  const legs = option?.legs ?? [];
  return (
    <section className="panel panel-soft d2d-timeline-panel">
      <div className="panel-header">
        <h2 className="panel-title">{t("doorToDoor.timeline.title")}</h2>
        {flight?.flight_time_confidence === "estimated" ? <span className="status-pill warning">{t("doorToDoor.timeline.estimatedSchedule")}</span> : null}
      </div>
      {legs.length === 0 ? (
        <p className="panel-note">{t("doorToDoor.timeline.empty")}</p>
      ) : (
        <ol className="d2d-timeline">
          {legs.map((leg, index) => (
            <li key={`${leg.type}-${leg.mode}-${index}`}>
              <span className={`d2d-timeline-node d2d-mode-${leg.mode}`} aria-hidden="true" />
              <div>
                <strong>{leg.from} {"->"} {leg.to}</strong>
                <p>
                  {leg.mode === "flight" ? t("doorToDoor.timeline.flight") : t("doorToDoor.timeline.ground")}
                  {" · "}
                  {leg.duration_minutes != null ? `${leg.duration_minutes} min` : t("doorToDoor.option.durationUnconfirmed")}
                  {" · "}
                  {timeRangeLabel(leg.departure_at, leg.arrival_at, t("doorToDoor.option.scheduleUnconfirmed"))}
                </p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
