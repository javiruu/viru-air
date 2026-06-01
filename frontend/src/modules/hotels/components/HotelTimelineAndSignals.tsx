"use client";

import { useMemo } from "react";

import { useI18n } from "@/i18n";

import type { HotelRateOut } from "../types";

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

export function HotelProviderStatusPill({ rates }: { rates: HotelRateOut[] }) {
  const { t } = useI18n();
  const hasRates = rates.length > 0;
  return <span className={`status-pill ${hasRates ? "success" : "warning"}`}>{hasRates ? t("hotels.provider.active") : t("hotels.provider.noSignal")}</span>;
}

export function HotelParitySignal({ rates }: { rates: HotelRateOut[] }) {
  const { t } = useI18n();
  const uniqueProviders = new Set(rates.map((rate) => rate.provider)).size;
  const tone = uniqueProviders >= 2 ? "success" : "info";
  const label = uniqueProviders >= 2 ? t("hotels.parity.stable") : t("hotels.parity.limited");

  return (
    <section className="panel panel-soft hotel-parity-signal">
      <div className="panel-header">
        <h2 className="panel-title">{t("hotels.parity.title")}</h2>
        <span className={`status-pill ${tone}`}>{label}</span>
      </div>
      <p className="panel-note section-gap-sm">{t("hotels.parity.placeholder")}</p>
    </section>
  );
}

