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
  const { t, localeTag } = useI18n();

  const signal = useMemo(() => {
    if (rates.length === 0) return null;

    // Group rates by stay parameters
    const groups = new Map<string, { providers: Set<string>; amounts: number[]; check_in: string; check_out: string; guests: number; currency: string }>();
    for (const rate of rates) {
      const key = `${rate.check_in}|${rate.check_out}|${rate.guests}|${rate.currency}`;
      if (!groups.has(key)) {
        groups.set(key, {
          providers: new Set(),
          amounts: [],
          check_in: rate.check_in,
          check_out: rate.check_out,
          guests: rate.guests,
          currency: rate.currency,
        });
      }
      const group = groups.get(key)!;
      group.providers.add(rate.provider);
      group.amounts.push(rate.amount);
    }

    // Use the most recent stay group
    const entries = Array.from(groups.values());
    entries.sort((a, b) => new Date(b.check_in).getTime() - new Date(a.check_in).getTime());
    const group = entries[0];
    const providerCount = group.providers.size;

    if (providerCount < 2 || group.amounts.length < 2) {
      return { status: "info" as const, label: t("hotels.parity.limited"), providerCount, detail: null };
    }

    const sorted = [...group.amounts].sort((a, b) => a - b);
    const lowest = sorted[0];
    const highest = sorted[sorted.length - 1];
    const average = Math.round((group.amounts.reduce((sum, v) => sum + v, 0) / group.amounts.length) * 100) / 100;
    const spreadAmount = Math.round((highest - lowest) * 100) / 100;
    const spreadPercent = Math.round(((highest - lowest) / lowest) * 1000) / 10;

    if (spreadPercent >= 20) {
      return { status: "error" as const, label: t("hotels.parity.breach"), providerCount, detail: { lowest, highest, average, spreadAmount, spreadPercent, currency: group.currency } };
    }
    if (spreadPercent >= 10) {
      return { status: "warning" as const, label: t("hotels.parity.tensioned"), providerCount, detail: { lowest, highest, average, spreadAmount, spreadPercent, currency: group.currency } };
    }
    return { status: "success" as const, label: t("hotels.parity.stable"), providerCount, detail: { lowest, highest, average, spreadAmount, spreadPercent, currency: group.currency } };
  }, [rates, t]);

  if (!signal) {
    return (
      <section className="panel panel-soft hotel-parity-signal">
        <div className="panel-header">
          <h2 className="panel-title">{t("hotels.parity.title")}</h2>
          <span className="status-pill info">{t("hotels.parity.limited")}</span>
        </div>
        <p className="panel-note section-gap-sm">{t("hotels.parity.noRates")}</p>
      </section>
    );
  }

  return (
    <section className="panel panel-soft hotel-parity-signal">
      <div className="panel-header">
        <h2 className="panel-title">{t("hotels.parity.title")}</h2>
        <span className={`status-pill ${signal.status}`}>{signal.label}</span>
      </div>
      <div className="section-gap-sm">
        <p className="panel-note">{t("hotels.parity.providerCount", { count: signal.providerCount })}</p>
        {signal.detail ? (
          <div className="hotel-parity-metrics section-gap-sm">
            <div className="hotel-parity-metric">
              <span>{t("hotels.parity.lowest")}</span>
              <strong>
                {new Intl.NumberFormat(localeTag, { style: "currency", currency: signal.detail.currency, maximumFractionDigits: 0 }).format(signal.detail.lowest)}
              </strong>
            </div>
            <div className="hotel-parity-metric">
              <span>{t("hotels.parity.highest")}</span>
              <strong>
                {new Intl.NumberFormat(localeTag, { style: "currency", currency: signal.detail.currency, maximumFractionDigits: 0 }).format(signal.detail.highest)}
              </strong>
            </div>
            <div className="hotel-parity-metric">
              <span>{t("hotels.parity.spread")}</span>
              <strong>{signal.detail.spreadPercent}%</strong>
            </div>
          </div>
        ) : (
          <p className="panel-note section-gap-sm">{t("hotels.parity.singleProvider")}</p>
        )}
      </div>
    </section>
  );
}

