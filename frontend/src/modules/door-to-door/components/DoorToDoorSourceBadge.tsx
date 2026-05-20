import React from "react";
import type { DoorToDoorConfidence } from "@/modules/door-to-door/types";

const LABELS: Record<DoorToDoorConfidence, string> = {
  live: "Datos en vivo",
  cached: "Cacheado",
  estimated: "Estimado",
  deeplink: "Abrir reserva",
  unavailable: "No disponible",
};

export function DoorToDoorSourceBadge({ confidence, label }: { confidence: DoorToDoorConfidence; label?: string }) {
  const tone = confidence === "live" ? "success" : confidence === "unavailable" ? "error" : "warning";
  return <span className={`status-pill ${tone} d2d-badge`}>{label || LABELS[confidence]}</span>;
}
