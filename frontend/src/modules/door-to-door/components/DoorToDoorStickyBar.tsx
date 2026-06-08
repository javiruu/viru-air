"use client";

import React, { useEffect, useState } from "react";
import { Clock, DollarSign, Shield } from "lucide-react";

import { useI18n } from "@/i18n";
import type { DoorToDoorOption } from "@/modules/door-to-door/types";

function durationCompact(minutes: number | null | undefined) {
  if (minutes == null) return "--";
  const hours = Math.floor(minutes / 60);
  const mins = String(minutes % 60).padStart(2, "0");
  return `${hours}h${mins}`;
}

export function DoorToDoorStickyBar({
  plan,
  trustTone,
  activeSection,
  onSectionClick,
}: {
  plan: DoorToDoorOption | null;
  trustTone: "success" | "warning";
  activeSection: string;
  onSectionClick: (section: string) => void;
}) {
  const { t } = useI18n();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const sentinel = document.getElementById("d2d-results-sentinel");
    if (!sentinel) return;

    const observer = new IntersectionObserver(
      ([entry]) => setVisible(!entry.isIntersecting),
      { threshold: 0, rootMargin: "-48px 0px 0px 0px" }
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, []);

  if (!plan || !visible) return null;

  const sections = [
    { id: "results", label: t("doorToDoor.sections.realResults") },
    { id: "timeline", label: t("doorToDoor.sections.tripSummary") },
    { id: "compare", label: t("doorToDoor.option.comparatorTitle") },
    { id: "sources", label: t("doorToDoor.sections.sources") },
    { id: "deeplinks", label: t("doorToDoor.sections.realDeeplinks") },
    { id: "maphub", label: t("doorToDoor.sections.coveragePanelTitle") },
    { id: "history", label: t("doorToDoor.sections.history") },
  ];

  return (
    <nav className="d2d-sticky-bar" aria-label={t("doorToDoor.stickyBar.aria")}>
      <div className="d2d-sticky-summary">
        <strong className="d2d-sticky-plan-label">{plan.label}</strong>
        <span className="d2d-sticky-metrics">
          <span>
            <DollarSign size={13} aria-hidden="true" />
            {plan.total_price_min ?? "--"}-{plan.total_price_max ?? "--"} {plan.currency}
          </span>
          <span>
            <Clock size={13} aria-hidden="true" />
            {durationCompact(plan.total_duration_minutes)}
          </span>
          <span className={`d2d-sticky-trust ${trustTone}`}>
            <Shield size={13} aria-hidden="true" />
          </span>
        </span>
      </div>
      <div className="d2d-sticky-nav" role="tablist">
        {sections.map((s) => (
          <button
            key={s.id}
            role="tab"
            aria-selected={activeSection === s.id}
            className={`d2d-sticky-nav-item ${activeSection === s.id ? "is-active" : ""}`}
            onClick={() => onSectionClick(s.id)}
          >
            {s.label}
          </button>
        ))}
      </div>
    </nav>
  );
}
