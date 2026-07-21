import type {
  LiveFlightLeg,
  LiveFlightMilestone,
  LiveFlightPosition,
  LiveFlightTracking,
} from "@/modules/watchlist/liveFlightTypes";

export function selectCurrentLiveLeg(tracking: LiveFlightTracking | null): LiveFlightLeg | null {
  if (!tracking?.legs.length) return null;
  const activeStatuses = new Set(["active", "diverted"]);
  return (
    tracking.legs.find(
      (leg) =>
        leg.operational?.freshness === "fresh" && activeStatuses.has(leg.operational.status),
    ) ??
    tracking.legs.find((leg) => leg.operational && activeStatuses.has(leg.operational.status)) ??
    tracking.legs.find((leg) => leg.operational?.status === "scheduled") ??
    tracking.legs.find((leg) => leg.operational?.status === "unknown") ??
    [...tracking.legs].reverse().find((leg) => leg.operational) ??
    tracking.legs[0] ??
    null
  );
}

export function selectPrimaryLivePosition(
  tracking: LiveFlightTracking | null,
): LiveFlightPosition | null {
  return selectCurrentLiveLeg(tracking)?.operational?.position ?? null;
}

export function selectPrimaryFlightLabel(tracking: LiveFlightTracking | null): string | null {
  const leg = selectCurrentLiveLeg(tracking);
  if (!leg) return null;
  return leg.identity.flight_number ?? `${leg.identity.origin_iata} → ${leg.identity.destination_iata}`;
}

export function milestoneTimestamp(milestone: LiveFlightMilestone): string | null {
  return milestone.actual_at ?? milestone.estimated_at ?? milestone.scheduled_at;
}

export function milestoneTimeSource(
  milestone: LiveFlightMilestone,
): "actual" | "estimated" | "scheduled" {
  if (milestone.actual_at) return "actual";
  if (milestone.estimated_at) return "estimated";
  return "scheduled";
}

export function formatLiveTime(value: string | null, locale: string): string {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--";
  return new Intl.DateTimeFormat(locale, {
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function liveCoverageTone(
  tracking: LiveFlightTracking | null,
): "success" | "warning" | "error" | "info" {
  if (!tracking) return "info";
  if (tracking.coverage === "live" || tracking.coverage === "completed") return "success";
  if (tracking.coverage === "temporarily_unavailable") return "warning";
  if (tracking.coverage === "cached") return "warning";
  return "info";
}
