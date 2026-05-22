import React from "react";

import { useI18n } from "@/i18n";
import type { DoorToDoorRiskLevel } from "@/modules/door-to-door/types";

export function DoorToDoorRiskPill({ risk }: { risk: DoorToDoorRiskLevel }) {
  const { t } = useI18n();
  const tone = risk === "low" ? "success" : risk === "medium" || risk === "unknown" ? "warning" : "error";
  return <span className={`status-pill ${tone} d2d-risk-pill`}>{t(`doorToDoor.risk.${risk}`)}</span>;
}