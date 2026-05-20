import React from "react";
import type { DoorToDoorFlight, DoorToDoorOption } from "@/modules/door-to-door/types";

export function DoorToDoorRouteVisual({ option, flight }: { option: DoorToDoorOption | null; flight?: DoorToDoorFlight | null }) {
  const labels = option?.legs.map((leg) => leg.from).concat(option.legs.at(-1)?.to || []) ?? ["Origen", flight?.origin_airport || "AGP", flight?.destination_airport || "TSF", "Destino"];
  const compactLabels = labels.filter(Boolean).slice(0, 5);
  return (
    <section className="panel d2d-route-visual" aria-label="Radar abstracto de ruta puerta a puerta">
      <div className="d2d-radar-sweep" aria-hidden="true" />
      <div className="d2d-route-orbit" aria-hidden="true" />
      <div className="d2d-route-line">
        {compactLabels.map((label, index) => (
          <div key={`${label}-${index}`} className="d2d-route-stop">
            <span>{index + 1}</span>
            <strong>{label}</strong>
          </div>
        ))}
      </div>
      <div className="d2d-flight-strip">
        <span>{flight?.origin_airport || "---"}</span>
        <i aria-hidden="true" />
        <span>{flight?.destination_airport || "---"}</span>
      </div>
    </section>
  );
}
