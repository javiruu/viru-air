import React from "react";

import { useI18n } from "@/i18n";
import type { DecisionBadge, DecisionReason, DoorToDoorOption } from "@/modules/door-to-door/types";
import { DoorToDoorRiskPill } from "@/modules/door-to-door/components/DoorToDoorRiskPill";

function durationLabel(minutes: number | null | undefined) {
  if (minutes == null) return null;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours}h${String(mins).padStart(2, "0")}`;
}

export function DoorToDoorOptionCard({
  option,
  chosen,
  isRecommended = false,
  compact = false,
  reasons = [],
  quickBadges = [],
  trustInline = false,
  onChoose,
}: {
  option: DoorToDoorOption;
  chosen: boolean;
  isRecommended?: boolean;
  compact?: boolean;
  reasons?: DecisionReason[];
  quickBadges?: DecisionBadge[];
  trustInline?: boolean;
  onChoose: () => void;
}) {
  const { t } = useI18n();
  const isRealResult = option.status === "real_result";
  const isRealDeeplink = option.status === "real_deeplink";
  const isEstimate = option.status === "estimate_only";
  const hasDuration = option.total_duration_minutes != null;
  const hasPrice = option.total_price_min != null && option.total_price_max != null;
  const hasGoogleRoutes = option.sources.some((source) => source.provider === "google_routes");

  function statusBadge() {
    if (isRealResult) return <span className="status-pill success d2d-badge">{t("doorToDoor.option.realResult")}</span>;
    if (isRealDeeplink) return <span className="status-pill info d2d-badge">{t("doorToDoor.option.realDeeplink")}</span>;
    return <span className="status-pill warning d2d-badge">{t("doorToDoor.option.estimateOnly")}</span>;
  }

  function priceLabel() {
    if (option.total_price_min == null || option.total_price_max == null) return t("doorToDoor.option.noPrice");
    if (option.total_price_min === option.total_price_max) return t("doorToDoor.option.fromPrice", { price: option.total_price_min, currency: option.currency });
    return t("doorToDoor.option.estimatedRange", { min: option.total_price_min, max: option.total_price_max, currency: option.currency });
  }

  const durStr = durationLabel(option.total_duration_minutes);

  return (
    <article className={`d2d-option-card ${isRealResult ? "is-real" : ""} ${isRealDeeplink ? "is-deeplink" : ""} ${isEstimate ? "is-estimate" : ""} ${chosen ? "is-chosen" : ""} ${isRecommended ? "is-recommended" : ""} ${compact ? "is-compact" : ""}`}>
      {isRecommended ? (
        <span className="d2d-recommended-star" aria-label={t("doorToDoor.option.recommended")}>★</span>
      ) : null}
      <div className="d2d-option-main">
        <div className="d2d-option-head">
          <div>
            {statusBadge()}
            <h3>{option.label}</h3>
          </div>
          <DoorToDoorRiskPill risk={option.risk_level} />
        </div>

        <p>{option.description}</p>

        {trustInline ? (
          <p className="d2d-option-trust-note">{t("doorToDoor.option.confirmOutside")}</p>
        ) : option.trust_copy ? (
          <p className="d2d-option-trust-note">{option.trust_copy}</p>
        ) : null}

        {quickBadges.length > 0 ? (
          <div className="d2d-option-quick-badges" aria-label={t("doorToDoor.option.quickBadges")}>
            {quickBadges.map((badge) => (
              <span key={`${option.id}-${badge.kind}`} className="status-pill state-info d2d-badge">
                {t(`doorToDoor.option.badges.${badge.label}`)}
              </span>
            ))}
          </div>
        ) : null}

        {reasons.length > 0 ? (
          <section className="d2d-decision-reasons" aria-label={t("doorToDoor.option.whyThisRouteTitle")}>
            <strong>{t("doorToDoor.option.whyThisRouteTitle")}</strong>
            <ul>
              {reasons.map((reason) => (
                <li key={`${option.id}-${reason.kind}`}>{t(`doorToDoor.option.reasons.${reason.label}`)}</li>
              ))}
            </ul>
          </section>
        ) : null}

        <div className="d2d-option-meta">
          {hasGoogleRoutes ? <span className="status-pill info d2d-badge">{t("doorToDoor.option.realDuration")}</span> : null}
          {hasDuration ? <span>{t("doorToDoor.option.buffer", { minutes: option.airport_buffer_minutes ?? "--" })}</span> : null}
          <span>{t("doorToDoor.option.transfers", { count: option.transfer_count })}</span>
          {option.score != null ? <span>{t("doorToDoor.option.score", { score: option.score })}</span> : null}
          {hasPrice ? (
            <strong className="d2d-option-price">
              {priceLabel()}
              {durStr ? ` · ${durStr}` : ""}
            </strong>
          ) : (
            <span className="d2d-option-price-unconfirmed">
              {isRealDeeplink ? t("doorToDoor.option.externalPriceNote") : t("doorToDoor.option.noPrice")}
              {durStr ? ` · ${durStr}` : ""}
            </span>
          )}
        </div>

        {/* Source summary */}
        <div className="d2d-option-sources">
          {option.sources.slice(0, 2).map((source) => {
            const sourceLabel =
              source.source_type === "maps" ? t("doorToDoor.source.maps") :
              source.source_type === "deeplink" ? t("doorToDoor.source.deeplink") :
              source.source_type === "open_data" ? t("doorToDoor.source.openData") :
              source.source_type === "estimate" ? t("doorToDoor.source.estimate") :
              source.source_type === "mock" ? t("doorToDoor.source.mock") :
              source.source_type;
            const tone = source.source_type === "maps" ? "info" : source.source_type === "open_data" ? "success" : source.source_type === "deeplink" ? "info" : "warning";
            return <span key={`${option.id}-${source.provider}`} className={`status-pill ${tone} d2d-badge`}>{sourceLabel}</span>;
          })}
        </div>
      </div>

      {/* Actions */}
      <div className="d2d-option-actions">
        {option.deep_link ? (
          <a className="btn-secondary btn-compact" href={option.deep_link.url} target="_blank" rel="noreferrer">
            {option.deep_link.label}
          </a>
        ) : option.sources.some((s) => s.booking_url) ? (
          <a className="btn-secondary btn-compact" href={option.sources.find((s) => s.booking_url)!.booking_url!} target="_blank" rel="noreferrer">
            {t("doorToDoor.option.openBooking")}
          </a>
        ) : null}
        {!isEstimate ? (
          <button type="button" className="btn-ghost btn-compact" onClick={onChoose}>
            {chosen ? t("doorToDoor.option.chosen") : t("doorToDoor.option.markChosen")}
          </button>
        ) : null}
      </div>
    </article>
  );
}
