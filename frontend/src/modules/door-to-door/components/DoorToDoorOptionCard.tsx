import React from "react";

import { ExternalLink } from "lucide-react";
import { useI18n } from "@/i18n";
import type { DecisionBadge, DecisionReason, DoorToDoorAction, DoorToDoorOption } from "@/modules/door-to-door/types";

function durationLabel(minutes: number | null | undefined) {
  if (minutes == null) return null;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours}h${String(mins).padStart(2, "0")}`;
}

function hasConfirmedPrice(min: number | null | undefined, max: number | null | undefined) {
  return min != null && max != null && min > 0 && max > 0;
}

function resolveExternalUrl(url: string | null | undefined) {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:" ? url : null;
  } catch {
    return null;
  }
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
  const isFull = option.completeness === "full";
  const isPartialActionable = option.completeness === "partial_actionable";
  const isExploratory = option.completeness === "exploratory";
  const hasDuration = option.total_duration_minutes != null;
  const hasPrice = hasConfirmedPrice(option.total_price_min, option.total_price_max);
  const hasGoogleRoutes = option.sources.some((source) => source.provider === "google_routes");
  const hasGtfsSchedule = option.legs.some((leg) => leg.type === "ground" && leg.source_type === "open_data" && leg.provider === "gtfs_transit" && leg.departure_at != null && leg.arrival_at != null);
  const isTightBuffer = option.airport_buffer_minutes != null && option.airport_buffer_minutes < 90;
  const legActions = option.legs
    .flatMap((leg) => (leg.actions ?? []).filter((a) => a.kind !== "directions"))
    .map((action) => ({ action, href: resolveExternalUrl(action.url) }))
    .filter((entry) => entry.href)
    .slice(0, 4);
  const transparencyNote =
    isRealDeeplink
      ? t("doorToDoor.sections.limitedComparisonBody")
      : isEstimate || isExploratory
        ? t("doorToDoor.sections.estimateExplanation")
        : isPartialActionable
          ? t("doorToDoor.sections.partialCoverageBody")
          : null;
  const primarySource = option.sources.find((source) => source.booking_url) ?? option.sources[0] ?? null;
  const primaryActionHref = option.deep_link
    ? resolveExternalUrl(option.deep_link.url)
    : resolveExternalUrl(primarySource?.booking_url);

  function actionLabel(action: DoorToDoorAction) {
    if (action.provider === "blablacar") return t("doorToDoor.option.openBlaBlaCar");
    if (action.provider === "goopti") return t("doorToDoor.option.openGoOpti");
    if (action.provider === "gtfs") return t("doorToDoor.sections.openPublicTransport");
    return t("doorToDoor.option.viewRouteInMaps");
  }

  function primaryActionLabel() {
    if (!option.deep_link) return t("doorToDoor.option.openBooking");
    if (primarySource?.provider?.includes("blablacar")) return t("doorToDoor.option.openBlaBlaCar");
    if (primarySource?.provider?.includes("goopti")) return t("doorToDoor.option.openGoOpti");
    if (option.deep_link.kind === "directions") return t("doorToDoor.option.viewRouteInMaps");
    return t("doorToDoor.option.openBooking");
  }

  function statusBadge() {
    if (isRealResult) return <span className="status-pill success d2d-badge">{t("doorToDoor.option.realResult")}</span>;
    if (isRealDeeplink) return <span className="status-pill info d2d-badge">{t("doorToDoor.option.realDeeplink")}</span>;
    return <span className="status-pill warning d2d-badge">{t("doorToDoor.option.estimateOnly")}</span>;
  }

  function completenessBadge() {
    if (isFull) return <span className="status-pill success d2d-badge">{t("doorToDoor.option.completenessFull")}</span>;
    if (isPartialActionable) return <span className="status-pill info d2d-badge">{t("doorToDoor.option.completenessPartial")}</span>;
    return <span className="status-pill warning d2d-badge">{t("doorToDoor.option.completenessExploratory")}</span>;
  }

  function priceLabel() {
    if (!hasConfirmedPrice(option.total_price_min, option.total_price_max)) return t("doorToDoor.option.noPrice");
    const minPrice = option.total_price_min!;
    const maxPrice = option.total_price_max!;
    if (minPrice === maxPrice) return t("doorToDoor.option.fromPrice", { price: minPrice, currency: option.currency });
    return t("doorToDoor.option.estimatedRange", { min: minPrice, max: maxPrice, currency: option.currency });
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
            {completenessBadge()}
            <h3>{option.label}</h3>
          </div>
        </div>

        <p>{option.description}</p>

        {trustInline ? (
          <p className="d2d-option-trust-note">{t("doorToDoor.option.confirmOutside")}</p>
        ) : option.trust_copy ? (
          <p className="d2d-option-trust-note">{option.trust_copy}</p>
        ) : null}

        {transparencyNote ? <p className="panel-note">{transparencyNote}</p> : null}

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
          {hasGtfsSchedule ? <span className="status-pill success d2d-badge">{t("doorToDoor.option.openDataSchedule")}</span> : null}
          {hasDuration ? (
            <span>
              {t("doorToDoor.option.buffer", { minutes: option.airport_buffer_minutes != null ? option.airport_buffer_minutes : t("doorToDoor.option.bufferUnconfirmed") })}
              {!compact && isTightBuffer ? <span className="status-pill warning d2d-badge" style={{ marginLeft: 6 }}>{t("doorToDoor.option.bufferRiskLabel")}</span> : null}
            </span>
          ) : null}
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
        {/* Per-segment external actions */}
        {!compact && legActions.length > 0 ? (
          <div className="d2d-option-segment-actions">
            <span className="panel-note">{t("doorToDoor.option.segmentActions")}</span>
            {legActions.map(({ action, href }) => (
              <a key={action.id} className="btn-secondary btn-compact" href={href!} target="_blank" rel="noreferrer">
                <ExternalLink size={12} aria-hidden="true" /> {actionLabel(action)}
              </a>
            ))}
          </div>
        ) : null}

      </div>

      {/* Actions */}
      <div className="d2d-option-actions">
        {primaryActionHref ? (
          <a className="btn-secondary btn-compact" href={primaryActionHref} target="_blank" rel="noreferrer">
            {primaryActionLabel()}
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
