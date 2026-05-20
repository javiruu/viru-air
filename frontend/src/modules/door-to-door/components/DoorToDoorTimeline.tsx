import React from "react";
import type { DoorToDoorFlight, DoorToDoorOption } from "@/modules/door-to-door/types";

function shortTime(value?: string | null) {
  if (!value) return "--";
  return new Intl.DateTimeFormat("es-ES", { hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

export function DoorToDoorTimeline({ option, flight }: { option: DoorToDoorOption | null; flight?: DoorToDoorFlight | null }) {
  const legs = option?.legs ?? [];
  return (
    <section className="panel panel-soft d2d-timeline-panel">
      <div className="panel-header">
        <h2 className="panel-title">Timeline de tramos</h2>
        {flight?.flight_time_confidence === "estimated" ? <span className="status-pill warning">Horario estimado</span> : null}
      </div>
      {legs.length === 0 ? (
        <p className="panel-note">Calcula una ruta para ver salida terrestre, vuelo y llegada terrestre.</p>
      ) : (
        <ol className="d2d-timeline">
          {legs.map((leg, index) => (
            <li key={`${leg.type}-${leg.mode}-${index}`}>
              <span className={`d2d-timeline-node d2d-mode-${leg.mode}`} aria-hidden="true" />
              <div>
                <strong>{leg.from} → {leg.to}</strong>
                <p>{leg.mode === "flight" ? "Vuelo" : "Tramo terrestre"} · {leg.duration_minutes ?? "--"} min · {shortTime(leg.departure_at)} - {shortTime(leg.arrival_at)}</p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
