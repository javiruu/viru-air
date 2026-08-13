"use client";

import { useI18n } from "@/i18n";

import type { HotelTrackingCandidate } from "../types";

type HotelTrackingConfirmationDialogProps = {
  readonly candidate: HotelTrackingCandidate | null;
  readonly submitting: boolean;
  readonly onClose: () => void;
  readonly onConfirm: () => void;
};

function formatStayDate(value: string, localeTag: string): string {
  return new Intl.DateTimeFormat(localeTag, { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(
    new Date(`${value}T00:00:00Z`),
  );
}

function formatObservedAt(value: string, localeTag: string): string {
  return new Intl.DateTimeFormat(localeTag, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }).format(
    new Date(value),
  );
}

function calculateNights(checkIn: string, checkOut: string): number {
  return Math.max(0, Math.round((Date.parse(`${checkOut}T00:00:00Z`) - Date.parse(`${checkIn}T00:00:00Z`)) / 86_400_000));
}

export function HotelTrackingConfirmationDialog({
  candidate,
  submitting,
  onClose,
  onConfirm,
}: HotelTrackingConfirmationDialogProps) {
  const { t, localeTag } = useI18n();

  if (candidate === null) return null;

  const { hotel, rate } = candidate;
  const nights = calculateNights(rate.check_in, rate.check_out);
  const fallbackDetail = t("hotels.trackingConfirmation.unavailableDetail");

  return (
    <div
      className="modal-overlay"
      onClick={() => {
        if (!submitting) onClose();
      }}
    >
      <section
        className="modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="hotel-tracking-confirmation-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="modal-header">
          <div>
            <h2 id="hotel-tracking-confirmation-title">{t("hotels.trackingConfirmation.title")}</h2>
            <p className="panel-note">{t("hotels.trackingConfirmation.subtitle")}</p>
          </div>
          <button
            type="button"
            className="modal-close"
            aria-label={t("hotels.trackingConfirmation.close")}
            disabled={submitting}
            onClick={onClose}
          >
            ×
          </button>
        </div>

        <div className="section-gap-sm">
          <p><strong>{t("hotels.trackingConfirmation.hotel")}:</strong> {hotel.canonical_name}, {hotel.city}</p>
          <p>
            <strong>{t("hotels.trackingConfirmation.stay")}:</strong>{" "}
            {formatStayDate(rate.check_in, localeTag)} – {formatStayDate(rate.check_out, localeTag)} ({t("hotels.trackingConfirmation.nights", { count: nights })}, {t("hotels.trackingConfirmation.guests", { count: rate.guests })})
          </p>
          <p><strong>{t("hotels.trackingConfirmation.room")}:</strong> {rate.room_label ?? fallbackDetail}</p>
          <p><strong>{t("hotels.trackingConfirmation.mealPlan")}:</strong> {rate.meal_plan ?? fallbackDetail}</p>
          <p><strong>{t("hotels.trackingConfirmation.cancellation")}:</strong> {rate.cancellation_policy ?? fallbackDetail}</p>
          <p><strong>{t("hotels.trackingConfirmation.provider")}:</strong> {rate.provider}</p>
          <p>
            <strong>{t("hotels.trackingConfirmation.observedPrice")}:</strong>{" "}
            {new Intl.NumberFormat(localeTag, { style: "currency", currency: rate.currency, maximumFractionDigits: 0 }).format(rate.amount)}
          </p>
          <p><strong>{t("hotels.trackingConfirmation.observedAt")}:</strong> {formatObservedAt(rate.collected_at, localeTag)}</p>
        </div>

        <div className="cta-row section-gap-sm">
          <button type="button" className="btn-secondary" disabled={submitting} onClick={onClose}>
            {t("hotels.trackingConfirmation.cancel")}
          </button>
          <button type="button" className="btn-primary" autoFocus disabled={submitting} onClick={onConfirm}>
            {submitting ? t("shared.states.loading") : t("hotels.trackingConfirmation.confirm")}
          </button>
        </div>
      </section>
    </div>
  );
}
