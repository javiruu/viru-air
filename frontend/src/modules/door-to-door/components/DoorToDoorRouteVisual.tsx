import React from "react";

import { Car, Plane, TrainFront } from "lucide-react";

import { useI18n } from "@/i18n";
import type { DoorToDoorFlight, DoorToDoorLeg, DoorToDoorOption } from "@/modules/door-to-door/types";

function resolveModeIcon(mode: DoorToDoorLeg["mode"]) {
  if (mode === "flight") return <Plane size={15} aria-hidden="true" />;
  if (mode === "car" || mode === "taxi" || mode === "rideshare" || mode === "shuttle") {
    return <Car size={15} aria-hidden="true" />;
  }
  return <TrainFront size={15} aria-hidden="true" />;
}

function resolveModeLabel(mode: DoorToDoorLeg["mode"], t: ReturnType<typeof useI18n>["t"]) {
  if (mode === "flight") return t("doorToDoor.routeVisual.flightSegment");
  if (mode === "bus") return t("doorToDoor.routeVisual.groundBus");
  if (mode === "train") return t("doorToDoor.routeVisual.groundTrain");
  if (mode === "car" || mode === "taxi") return t("doorToDoor.routeVisual.groundCar");
  if (mode === "rideshare") return t("doorToDoor.routeVisual.groundRideshare");
  return t("doorToDoor.routeVisual.groundOut");
}

export function DoorToDoorRouteVisual({
  option,
  flight,
}: {
  option: DoorToDoorOption | null;
  flight?: DoorToDoorFlight | null;
}) {
  const { t } = useI18n();

  if (!option || option.legs.length === 0) {
    return (
      <section className="d2d-route-visual" aria-label={t("doorToDoor.routeVisual.aria")}>
        <p className="panel-note">{t("doorToDoor.routeVisual.empty")}</p>
      </section>
    );
  }

  const legs = option.legs;

  // Filter out ground legs whose .from duplicates the previous flight leg's .to.
  // The arrival airport is already shown inside the flight node;
  // the final destination node at the end of the trace handles showing the endpoint.
  const visibleNodes = legs.reduce<{ leg: typeof legs[number]; index: number }[]>(
    (acc, leg, idx) => {
      const prev = acc[acc.length - 1];
      const prevLeg = prev?.leg;
      if (
        prevLeg?.type === "flight" &&
        leg.type === "ground" &&
        leg.from === prevLeg.to
      ) {
        // Skip entirely — flight node already showed the arrival airport,
        // and the final destination node will show the real endpoint.
        return acc;
      }
      acc.push({ leg, index: idx });
      return acc;
    },
    []
  );

  return (
    <section className="d2d-route-visual" aria-label={t("doorToDoor.routeVisual.aria")}>
      <ol className="d2d-route-trace" role="list">
        {visibleNodes.map(({ leg, index }, visualIdx) => {
          const isFlight = leg.type === "flight";
          // Use the original leg index for staggered delay
          const staggerIdx = index;
          return (
            <li
              key={`${leg.type}-${leg.mode}-${staggerIdx}`}
              className={`d2d-route-segment ${isFlight ? "is-flight" : "is-ground"}`}
              style={{ animationDelay: `${visualIdx * 150}ms` }}
            >
              {/* Connector line from previous node */}
              {visualIdx > 0 ? (
                <span className="d2d-route-connector" aria-hidden="true">
                  <span className="d2d-route-connector-line" />
                  <span className="d2d-route-connector-icon">
                    {resolveModeIcon(leg.mode)}
                  </span>
                </span>
              ) : null}

              {/* Segment node */}
              <div className={`d2d-route-node ${isFlight ? "is-flight-node" : "is-ground-node"}`}>
                <span className="d2d-route-iata">
                  {isFlight ? (
                    <>
                      <strong>{leg.from}</strong>
                      <Plane size={14} aria-hidden="true" className="d2d-route-plane-icon" />
                      <strong>{leg.to}</strong>
                    </>
                  ) : (
                    <strong>{leg.from}</strong>
                  )}
                </span>
              </div>
            </li>
          );
        })}

        {/* Final destination node */}
        <li
          className="d2d-route-segment"
          style={{ animationDelay: `${visibleNodes.length * 150}ms` }}
        >
          <span className="d2d-route-connector" aria-hidden="true">
            <span className="d2d-route-connector-line" />
          </span>
          <div className="d2d-route-node is-arrival-node">
            <span className="d2d-route-iata">
              <strong>{legs[legs.length - 1]?.to || t("doorToDoor.routeVisual.destination")}</strong>
            </span>
          </div>
        </li>
      </ol>

      {/* Mode labels */}
      <div className="d2d-route-labels" aria-hidden="true">
        {legs.map((leg, index) => (
          <span
            key={`label-${index}`}
            className={`d2d-route-label ${leg.type === "flight" ? "is-flight-label" : "is-ground-label"}`}
            style={{ animationDelay: `${index * 150 + 200}ms` }}
          >
            {resolveModeLabel(leg.mode, t)}
          </span>
        ))}
      </div>

      {/* Flight strip with times */}
      {flight ? (
        <div className="d2d-route-flight-strip" aria-label={t("doorToDoor.routeVisual.flightInfo")}>
          <span className="d2d-route-flight-strip-iata">{flight.origin_airport}</span>
          <span className="d2d-route-flight-strip-line" aria-hidden="true">
            <span className="d2d-route-flight-strip-dash" />
            <Plane size={12} aria-hidden="true" />
            <span className="d2d-route-flight-strip-dash" />
          </span>
          <span className="d2d-route-flight-strip-iata">{flight.destination_airport}</span>
        </div>
      ) : null}
    </section>
  );
}
