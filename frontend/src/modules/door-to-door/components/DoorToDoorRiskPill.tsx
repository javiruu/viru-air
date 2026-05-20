import React from "react";
import type { DoorToDoorRiskLevel } from "@/modules/door-to-door/types";

const RISK_LABEL: Record<DoorToDoorRiskLevel, string> = {
  low: "riesgo bajo",
  medium: "riesgo medio",
  high: "riesgo alto",
  unknown: "riesgo sin confirmar",
};

export function DoorToDoorRiskPill({ risk }: { risk: DoorToDoorRiskLevel }) {
  const tone = risk === "low" ? "success" : risk === "medium" || risk === "unknown" ? "warning" : "error";
  return <span className={`status-pill ${tone} d2d-risk-pill`}>{RISK_LABEL[risk]}</span>;
}
