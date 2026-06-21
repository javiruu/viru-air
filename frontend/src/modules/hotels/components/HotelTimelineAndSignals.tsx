"use client";

import { useMemo } from "react";

import { useI18n } from "@/i18n";

import { assessHotelSignal } from "../signalAssessment";
import type { HotelParityOut, HotelRateOut } from "../types";

function formatMoney(value: number, currency: string, localeTag: string): string {
  return new Intl.NumberFormat(localeTag, { style: "currency", currency, maximumFractionDigits: 0 }).format(value);
}

function formatDate(value: string, localeTag: string): string {
  return new Intl.DateTimeFormat(localeTag, { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

export function HotelPriceTimeline({ rates }: { rates: HotelRateOut[] }) {
  const { t, localeTag } = useI18n();
  const sorted = useMemo(() => [...rates].sort((a, b) => new Date(b.collected_at).getTime() - new Date(a.collected_at).getTime()), [rates]);

  return (
    <section className="panel panel-soft hotel-timeline">
      <div className="panel-header">
        <h2 className="panel-title">{t("hotels.timeline.title")}</h2>
        <span className="status-pill info">{t("hotels.timeline.lastCapture")}</span>
      </div>
      {sorted.length === 0 ? <p className="panel-note section-gap-sm">{t("hotels.timeline.empty")}</p> : null}
      <div className="section-gap-sm hotel-timeline-list">
        {sorted.map((rate) => (
          <article key={rate.id} className="list-row hotel-rate-row">
            <div>
              <strong>{rate.provider}</strong>
              <p className="panel-note">{formatDate(rate.collected_at, localeTag)}</p>
            </div>
            <div className="hotel-rate-right">
              <strong>{formatMoney(rate.amount, rate.currency, localeTag)}</strong>
              <p className="panel-note">{rate.room_label || t("hotels.timeline.standardRoom")}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export function HotelProviderStatusPill({
  rates,
  signal,
}: {
  rates: HotelRateOut[];
  signal?: HotelParityOut | null;
}) {
  const { t } = useI18n();
  const assessment = assessHotelSignal(rates, signal ?? null);
  return <span className={`status-pill ${assessment.status}`}>{t(assessment.providerLabelKey)}</span>;
}

function resolveParityLabel(signal: HotelParityOut, t: ReturnType<typeof useI18n>["t"]): string {
  if (signal.label === "stable") return t("hotels.parity.stable");
  if (signal.label === "tensioned") return t("hotels.parity.tensioned");
  if (signal.label === "breach") return t("hotels.parity.breach");
  return t("hotels.parity.limited");
}

export function HotelParitySignal({
  signals,
  rates,
  loading,
  error,
}: {
  signals: HotelParityOut[];
  rates: HotelRateOut[];
  loading: boolean;
  error: string | null;
}) {
  const { t, localeTag } = useI18n();
  const signal = signals[0] ?? null;
  const assessment = assessHotelSignal(rates, signal);

  if (loading) {
    return (
      <section className="panel panel-soft hotel-parity-signal">
        <div className="panel-header">
          <h2 className="panel-title">{t("hotels.parity.title")}</h2>
          <span className="status-pill info">{t("shared.states.loading")}</span>
        </div>
        <p className="panel-note section-gap-sm">{t("hotels.parity.loading")}</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="panel panel-soft hotel-parity-signal">
        <div className="panel-header">
          <h2 className="panel-title">{t("hotels.parity.title")}</h2>
          <span className="status-pill error">{t("hotels.parity.errorBadge")}</span>
        </div>
        <p className="panel-note section-gap-sm">{error}</p>
      </section>
    );
  }

  if (!signal) {
    return (
      <section className="panel panel-soft hotel-parity-signal">
        <div className="panel-header">
          <h2 className="panel-title">{t("hotels.parity.title")}</h2>
          <span className={`status-pill ${assessment.status}`}>{t(assessment.parityBadgeKey)}</span>
        </div>
        <p className="panel-note section-gap-sm">{t(assessment.detailKey)}</p>
      </section>
    );
  }

  const translatedLabel = resolveParityLabel(signal, t);
  const canScore = assessment.level === "scored";

  return (
    <section className="panel panel-soft hotel-parity-signal">
      <div className="panel-header">
        <h2 className="panel-title">{t("hotels.parity.title")}</h2>
        <span className={`status-pill ${canScore ? signal.status : assessment.status}`}>
          {canScore ? translatedLabel : t(assessment.parityBadgeKey)}
        </span>
      </div>
      <div className="section-gap-sm">
        <p className="panel-note">{t("hotels.parity.providerCount", { count: signal.provider_count })}</p>
        {canScore && signal.lowest_price !== null && signal.highest_price !== null && signal.spread_percent !== null ? (
          <div className="hotel-parity-metrics section-gap-sm">
            <div className="hotel-parity-metric">
              <span>{t("hotels.parity.lowest")}</span>
              <strong>
                {new Intl.NumberFormat(localeTag, { style: "currency", currency: signal.currency, maximumFractionDigits: 0 }).format(signal.lowest_price)}
              </strong>
            </div>
            <div className="hotel-parity-metric">
              <span>{t("hotels.parity.highest")}</span>
              <strong>
                {new Intl.NumberFormat(localeTag, { style: "currency", currency: signal.currency, maximumFractionDigits: 0 }).format(signal.highest_price)}
              </strong>
            </div>
            <div className="hotel-parity-metric">
              <span>{t("hotels.parity.spread")}</span>
              <strong>{signal.spread_percent}%</strong>
            </div>
          </div>
        ) : (
          <p className="panel-note section-gap-sm">{t(assessment.detailKey)}</p>
        )}
      </div>
    </section>
  );
}

