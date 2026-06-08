"use client";

import React, { useEffect, useRef } from "react";
import { X } from "lucide-react";

import { useI18n } from "@/i18n";
import { DoorToDoorFilters } from "@/modules/door-to-door/components/DoorToDoorFilters";
import { DEFAULT_PREFERENCES } from "@/modules/door-to-door/constants";
import type { DoorToDoorPreferences } from "@/modules/door-to-door/types";

export function DoorToDoorFilterPanel({
  open,
  onClose,
  preferences,
  onChange,
}: {
  open: boolean;
  onClose: () => void;
  preferences: DoorToDoorPreferences;
  onChange: (next: DoorToDoorPreferences) => void;
}) {
  const { t } = useI18n();
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) {
      const prevFocus = document.activeElement as HTMLElement | null;
      document.body.style.overflow = "hidden";
      panelRef.current?.focus();
      return () => {
        document.body.style.overflow = "";
        prevFocus?.focus();
      };
    }
    document.body.style.overflow = "";
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <>
      <div className="d2d-filter-overlay" onClick={onClose} aria-hidden="true" />
      <aside
        ref={panelRef}
        className="d2d-filter-slideout"
        role="dialog"
        aria-modal="true"
        aria-label={t("doorToDoor.filters.title")}
        tabIndex={-1}
      >
        <div className="d2d-filter-slideout-header">
          <h2>{t("doorToDoor.filters.title")}</h2>
          <button
            className="btn-ghost btn-compact"
            type="button"
            onClick={onClose}
            aria-label={t("shared.actions.close")}
          >
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        <div className="d2d-filter-slideout-body">
          {/* Quick presets */}
          <div className="d2d-filter-presets">
            <span className="d2d-filter-presets-label">{t("doorToDoor.filters.presets")}</span>
            <div className="d2d-filter-preset-buttons">
              <button
                type="button"
                className="btn-secondary btn-compact"
                onClick={() => onChange({ ...DEFAULT_PREFERENCES, sort_by: "cheapest" })}
              >
                {t("doorToDoor.filters.presetCheap")}
              </button>
              <button
                type="button"
                className="btn-secondary btn-compact"
                onClick={() => onChange({ ...DEFAULT_PREFERENCES, sort_by: "fastest" })}
              >
                {t("doorToDoor.filters.presetFast")}
              </button>
              <button
                type="button"
                className="btn-secondary btn-compact"
                onClick={() => onChange({ ...DEFAULT_PREFERENCES, sort_by: "fewest_changes", min_airport_buffer_minutes: 180 })}
              >
                {t("doorToDoor.filters.presetSafe")}
              </button>
            </div>
          </div>

          <DoorToDoorFilters preferences={preferences} onChange={onChange} embedded />
        </div>
      </aside>
    </>
  );
}
