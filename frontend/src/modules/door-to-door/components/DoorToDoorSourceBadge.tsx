import React from "react";

import { useI18n } from "@/i18n";
import type { DoorToDoorConfidence } from "@/modules/door-to-door/types";

export function DoorToDoorSourceBadge({ confidence, label }: { confidence: DoorToDoorConfidence; label?: string }) {
  const { t } = useI18n();
  const tone = confidence === "live" ? "success" : confidence === "unavailable" ? "error" : "warning";
  return <span className={`status-pill ${tone} d2d-badge`}>{label || t(`doorToDoor.source.${confidence}`)}</span>;
}