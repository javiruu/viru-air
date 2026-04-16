"use client";

import React from "react";
import { useEffect, useMemo, useRef, useState } from "react";

type Props = {
  name: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  localeTag: string;
  variant?: "outbound" | "return";
  min?: string;
  invalid?: boolean;
  onBlur?: () => void;
  defaultOpen?: boolean;
};

type CalendarDay = {
  iso: string;
  date: Date;
  inMonth: boolean;
  isToday: boolean;
  isSelected: boolean;
  isDisabled: boolean;
};

function parseIsoDate(value: string | undefined): Date | null {
  if (!value) return null;
  const parts = value.split("-").map((item) => Number(item));
  if (parts.length !== 3 || parts.some((item) => !Number.isFinite(item))) return null;
  return new Date(parts[0], parts[1] - 1, parts[2], 12, 0, 0, 0);
}

function formatIsoDate(value: Date): string {
  const year = value.getFullYear();
  const month = `${value.getMonth() + 1}`.padStart(2, "0");
  const day = `${value.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function startOfMonth(value: Date): Date {
  return new Date(value.getFullYear(), value.getMonth(), 1, 12, 0, 0, 0);
}

function addMonths(value: Date, amount: number): Date {
  return new Date(value.getFullYear(), value.getMonth() + amount, 1, 12, 0, 0, 0);
}

function addDays(value: Date, amount: number): Date {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate() + amount, 12, 0, 0, 0);
}

function sameDay(left: Date | null, right: Date | null): boolean {
  if (!left || !right) return false;
  return (
    left.getFullYear() === right.getFullYear()
    && left.getMonth() === right.getMonth()
    && left.getDate() === right.getDate()
  );
}

function buildCalendarDays(viewMonth: Date, selected: Date | null, minDate: Date | null): CalendarDay[] {
  const monthStart = startOfMonth(viewMonth);
  const dayOffset = (monthStart.getDay() + 6) % 7;
  const gridStart = addDays(monthStart, -dayOffset);
  const today = new Date();
  const todayDate = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 12, 0, 0, 0);

  return Array.from({ length: 42 }).map((_, index) => {
    const date = addDays(gridStart, index);
    return {
      iso: formatIsoDate(date),
      date,
      inMonth: date.getMonth() === viewMonth.getMonth(),
      isToday: sameDay(date, todayDate),
      isSelected: sameDay(date, selected),
      isDisabled: Boolean(minDate && date < minDate),
    };
  });
}

export function QuickSearchDatePicker(props: Props) {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const [open, setOpen] = useState(Boolean(props.defaultOpen));
  const handleBlur = props.onBlur;
  const locale = props.localeTag.toLowerCase().startsWith("es")
    ? {
      openCalendar: "Abrir calendario",
      closeCalendar: "Cerrar calendario",
      previousMonth: "Mes anterior",
      nextMonth: "Mes siguiente",
      chooseDate: "Elige una fecha para continuar",
      selectedDate: "Fecha seleccionada",
      selectOutbound: "Selecciona salida",
      selectReturn: "Anade vuelta",
      outboundReady: "Salida elegida",
      returnReady: "Vuelta elegida",
    }
    : {
      openCalendar: "Open calendar",
      closeCalendar: "Close calendar",
      previousMonth: "Previous month",
      nextMonth: "Next month",
      chooseDate: "Choose a date to continue",
      selectedDate: "Selected date",
      selectOutbound: "Select outbound",
      selectReturn: "Add return",
      outboundReady: "Outbound selected",
      returnReady: "Return selected",
    };

  const selectedDate = useMemo(() => parseIsoDate(props.value), [props.value]);
  const minDate = useMemo(() => parseIsoDate(props.min), [props.min]);
  const [viewMonth, setViewMonth] = useState<Date>(() => {
    return startOfMonth(selectedDate || minDate || new Date());
  });

  useEffect(() => {
    if (!open) return;
    const anchorDate = selectedDate || minDate || new Date();
    setViewMonth(startOfMonth(anchorDate));
  }, [open, selectedDate, minDate]);

  useEffect(() => {
    if (!open) return;
    const handlePointerDown = (event: MouseEvent) => {
      const root = rootRef.current;
      if (!root || root.contains(event.target as Node)) return;
      setOpen(false);
      handleBlur?.();
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setOpen(false);
      handleBlur?.();
    };
    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [handleBlur, open]);

  const monthLabel = useMemo(() => {
    return new Intl.DateTimeFormat(props.localeTag, { month: "long", year: "numeric" }).format(viewMonth);
  }, [props.localeTag, viewMonth]);

  const weekdayLabels = useMemo(() => {
    const baseMonday = new Date(2024, 0, 1, 12, 0, 0, 0);
    const formatter = new Intl.DateTimeFormat(props.localeTag, { weekday: "short" });
    return Array.from({ length: 7 }).map((_, index) => {
      const label = formatter.format(addDays(baseMonday, index)).replace(".", "");
      return label.slice(0, 2).toUpperCase();
    });
  }, [props.localeTag]);

  const dayLabelFormatter = useMemo(() => {
    return new Intl.DateTimeFormat(props.localeTag, {
      weekday: "short",
      day: "numeric",
      month: "short",
    });
  }, [props.localeTag]);

  const selectedLabel = selectedDate
    ? new Intl.DateTimeFormat(props.localeTag, {
      day: "numeric",
      month: "short",
    }).format(selectedDate)
    : props.placeholder;
  const selectedMeta = selectedDate
    ? new Intl.DateTimeFormat(props.localeTag, {
      weekday: "long",
      day: "numeric",
      month: "short",
      year: "numeric",
    }).format(selectedDate)
    : props.variant === "return"
      ? locale.selectReturn
      : locale.selectOutbound;
  const selectedStateLabel = selectedDate
    ? (props.variant === "return" ? locale.returnReady : locale.outboundReady)
    : props.label;

  const calendarDays = useMemo(() => {
    return buildCalendarDays(viewMonth, selectedDate, minDate);
  }, [viewMonth, selectedDate, minDate]);

  return (
    <div
      className={`qs-date-picker${open ? " is-open" : ""}${props.invalid ? " is-invalid" : ""}`}
      data-ui="qs-date-picker-v2"
      ref={rootRef}
    >
      <input type="hidden" name={props.name} value={props.value} />
      <button
        type="button"
        className={`qs-input qs-date-trigger${props.value ? " has-value" : ""}`}
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-label={`${open ? locale.closeCalendar : locale.openCalendar}: ${props.label}`}
        onClick={() => setOpen((current) => !current)}
        onBlur={() => {
          if (open) return;
          handleBlur?.();
        }}
      >
        <span className="qs-date-trigger__content">
          <span className="qs-date-trigger__eyebrow">{selectedStateLabel}</span>
          <span className="qs-date-trigger__value">{selectedLabel}</span>
          <span className="qs-date-trigger__meta">{selectedMeta}</span>
        </span>
        <span className="qs-date-trigger__actions" aria-hidden="true">
          <span className="qs-date-inline-icon">
            <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
              <rect x="3" y="4" width="18" height="17" rx="3" fill="none" stroke="currentColor" strokeWidth="1.6" />
              <path
                d="M8 2v4M16 2v4M3 9h18"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
              />
            </svg>
          </span>
          <span className={`qs-date-trigger__caret${open ? " is-open" : ""}`}>
            <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
              <path d="m6.5 9 5.5 6 5.5-6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>
        </span>
      </button>
      {open ? (
        <div className="qs-date-popover" role="dialog" aria-label={props.label}>
          <div className="qs-date-popover__header">
            <div>
              <span className="qs-date-popover__eyebrow">{props.label}</span>
              <strong>{monthLabel}</strong>
            </div>
            <div className="qs-date-popover__nav">
              <button
                type="button"
                className="qs-date-nav"
                aria-label={locale.previousMonth}
                onClick={() => setViewMonth((current) => addMonths(current, -1))}
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="m14.5 6-6 6 6 6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
              <button
                type="button"
                className="qs-date-nav"
                aria-label={locale.nextMonth}
                onClick={() => setViewMonth((current) => addMonths(current, 1))}
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="m9.5 6 6 6-6 6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </div>
          </div>
          <div className="qs-date-popover__weekdays" aria-hidden="true">
            {weekdayLabels.map((item) => (
              <span key={`${props.name}-${item}`}>{item}</span>
            ))}
          </div>
          <div className="qs-date-popover__grid">
            {calendarDays.map((day) => (
              <button
                key={`${props.name}-${day.iso}`}
                type="button"
                className={[
                  "qs-date-day",
                  day.inMonth ? "" : "is-outside",
                  day.isToday ? "is-today" : "",
                  day.isSelected ? "is-selected" : "",
                  day.isDisabled ? "is-disabled" : "",
                ].filter(Boolean).join(" ")}
                disabled={day.isDisabled}
                aria-pressed={day.isSelected}
                aria-label={dayLabelFormatter.format(day.date)}
                onClick={() => {
                  props.onChange(day.iso);
                  setOpen(false);
                  handleBlur?.();
                }}
              >
                <span className="qs-date-day__number">{day.date.getDate()}</span>
              </button>
            ))}
          </div>
          <div className="qs-date-popover__footer">
            <span className="qs-date-popover__footer-label">
              {selectedDate ? locale.selectedDate : locale.chooseDate}
            </span>
            <strong>{selectedDate ? selectedLabel : props.placeholder}</strong>
          </div>
        </div>
      ) : null}
    </div>
  );
}
