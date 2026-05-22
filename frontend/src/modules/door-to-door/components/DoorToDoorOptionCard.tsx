import React from "react";

import { useI18n } from "@/i18n";
import type { DoorToDoorOption } from "@/modules/door-to-door/types";
import { DoorToDoorRiskPill } from "@/modules/door-to-door/components/DoorToDoorRiskPill";
import { DoorToDoorSourceBadge } from "@/modules/door-to-door/components/DoorToDoorSourceBadge";

function durationLabel(minutes: number) {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours}h${String(mins).padStart(2, "0")}`;
}

export function DoorToDoorOptionCard({
  option,
  selected,
  chosen,
  compact = false,
  onSelect,
  onChoose,
}: {
  option: DoorToDoorOption;
  selected: boolean;
  chosen: boolean;
  compact?: boolean;
  onSelect: () => void;
  onChoose: () => void;
}) {
  const { t } = useI18n();
  const hasConfirmedPrice = option.total_price_min != null && option.total_price_max != null;
  const isDeeplinkUnpriced = option.source_types.includes("deeplink") && !hasConfirmedPrice;
  const hasGoogleRoutes = option.sources.some((source) => source.provider === "google_routes");
  const strongRecommended = option.is_recommended && hasConfirmedPrice && !isDeeplinkUnpriced;
  const blablacarLeg = option.legs.find((leg) => leg.provider === "blablacar" && leg.booking_url);
  const gooptiLeg = option.legs.find((leg) => leg.provider === "goopti" && leg.booking_url);
  const genericBookingLeg = !blablacarLeg && !gooptiLeg ? option.legs.find((leg) => leg.booking_url) : null;

  function kickerLabel() {
    if (isDeeplinkUnpriced) return t("doorToDoor.option.limited");
    if (strongRecommended) return t("doorToDoor.option.recommended");
    if (option.is_extended || compact) return t("doorToDoor.option.alternative");
    return t("doorToDoor.option.defaultKicker");
  }

  function priceLabel() {
    if (option.total_price_min == null || option.total_price_max == null) return t("doorToDoor.option.noPrice");
    if (option.total_price_min === option.total_price_max) return t("doorToDoor.option.fromPrice", { price: option.total_price_min, currency: option.currency });
    return t("doorToDoor.option.estimatedRange", { min: option.total_price_min, max: option.total_price_max, currency: option.currency });
  }

  return (
    <article className={`d2d-option-card ${selected ? "is-selected" : ""} ${strongRecommended ? "is-recommended" : ""} ${chosen ? "is-chosen" : ""} ${compact ? "is-compact" : ""} ${isDeeplinkUnpriced ? "is-limited" : ""}`}>
      <button type="button" className="d2d-option-main" onClick={onSelect} aria-pressed={selected}>
        <div className="d2d-option-head">
          <div>
            <span className="d2d-option-kicker">{kickerLabel()}</span>
            <h3>{option.label}</h3>
          </div>
          <DoorToDoorRiskPill risk={option.risk_level} />
        </div>
        <strong className="d2d-option-price">{priceLabel()} · {durationLabel(option.total_duration_minutes)}</strong>
        <p>{isDeeplinkUnpriced ? t("doorToDoor.option.routeToProvider") : option.description}</p>
        {isDeeplinkUnpriced ? <p className="d2d-option-trust-note">{t("doorToDoor.option.deeplinkDisclosure")}</p> : null}
        <div className="d2d-option-meta">
          <span>{t("doorToDoor.option.buffer", { minutes: option.airport_buffer_minutes ?? "--" })}</span>
          <span>{t("doorToDoor.option.transfers", { count: option.transfer_count })}</span>
          <span>{t("doorToDoor.option.score", { score: option.score })}</span>
          {option.price_per_person_min != null ? <span>{t("doorToDoor.option.perPerson", { min: option.price_per_person_min, max: option.price_per_person_max ?? option.price_per_person_min, currency: option.currency })}</span> : null}
        </div>
        <div className="d2d-option-sources">
          {hasGoogleRoutes ? <span className="status-pill success d2d-badge">{t("doorToDoor.option.realDuration")}</span> : null}
          {!hasConfirmedPrice ? <span className="status-pill warning d2d-badge">{t("doorToDoor.option.noPrice")}</span> : null}
          {option.sources.slice(0, 2).map((source) => (
            <DoorToDoorSourceBadge key={`${option.id}-${source.provider}`} confidence={source.confidence} label={source.source_type === "mock" ? t("doorToDoor.source.mock") : undefined} />
          ))}
          {option.source_types.includes("scraper") ? <DoorToDoorSourceBadge confidence="cached" label={t("doorToDoor.source.scraper")} /> : null}
        </div>
      </button>
      <div className="d2d-option-actions">
        {blablacarLeg ? (
          <a className="btn-secondary btn-compact" href={blablacarLeg.booking_url || "#"} target="_blank" rel="noreferrer">{t("doorToDoor.option.openBlaBlaCar")}</a>
        ) : gooptiLeg ? (
          <a className="btn-secondary btn-compact" href={gooptiLeg.booking_url || "#"} target="_blank" rel="noreferrer">{t("doorToDoor.option.openGoOpti")}</a>
        ) : genericBookingLeg ? (
          <a className="btn-secondary btn-compact" href={genericBookingLeg.booking_url || "#"} target="_blank" rel="noreferrer">{t("doorToDoor.option.openBooking")}</a>
        ) : null}
        <button type="button" className="btn-ghost btn-compact" onClick={onChoose}>{chosen ? t("doorToDoor.option.chosen") : t("doorToDoor.option.markChosen")}</button>
      </div>
    </article>
  );
}
