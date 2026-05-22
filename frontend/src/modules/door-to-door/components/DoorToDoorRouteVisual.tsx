import React from "react";

import { useI18n } from "@/i18n";
import type { DoorToDoorFlight, DoorToDoorOption } from "@/modules/door-to-door/types";

export function DoorToDoorRouteVisual({ option, flight }: { option: DoorToDoorOption | null; flight?: DoorToDoorFlight | null }) {
  const { t } = useI18n();
  const outbound = option?.legs.find((leg) => leg.type === "ground");
  const inbound = option?.legs.filter((leg) => leg.type === "ground").at(-1);

  const stops = [
    outbound?.from || t("doorToDoor.routeVisual.origin"),
    flight?.origin_airport || "AGP",
    flight?.destination_airport || "TSF",
    inbound?.to || t("doorToDoor.routeVisual.destination"),
  ];

  const segments = [
    { label: t("doorToDoor.routeVisual.groundOut"), mode: outbound?.mode || "ground" },
    { label: t("doorToDoor.routeVisual.flightSegment"), mode: "flight" },
    { label: t("doorToDoor.routeVisual.groundIn"), mode: inbound?.mode || "ground" },
  ];

  return (
    <section className="panel d2d-route-visual" aria-label={t("doorToDoor.routeVisual.aria")}>
      <div className="d2d-route-strip">
        {stops.map((stop, index) => (
          <React.Fragment key={`${stop}-${index}`}>
            <div className="d2d-route-stop">
              <span>{index + 1}</span>
              <strong>{stop}</strong>
            </div>
            {index < stops.length - 1 ? (
              <div className={`d2d-route-segment d2d-route-segment-${segments[index]?.mode || "ground"}`}>
                <i aria-hidden="true" />
                <small>{segments[index]?.label}</small>
              </div>
            ) : null}
          </React.Fragment>
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
