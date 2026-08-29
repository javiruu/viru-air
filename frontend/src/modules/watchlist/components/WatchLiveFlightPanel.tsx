import Link from "next/link";

import { useI18n } from "@/i18n";
import { BoneyardLoad, LoadReference } from "@/modules/shared/BoneyardLoad";
import {
  formatLiveTime,
  liveCoverageTone,
  milestoneTimeSource,
  milestoneTimestamp,
  selectCurrentLiveLeg,
} from "@/modules/watchlist/liveFlightPresentation";
import type { LiveFlightLeg, LiveFlightTracking } from "@/modules/watchlist/liveFlightTypes";
import { WatchDelayPrediction } from "@/modules/watchlist/components/WatchDelayPrediction";

type WatchLiveFlightPanelProps = {
  tracking: LiveFlightTracking | null;
  isLoading: boolean;
  isRefreshing: boolean;
  hasError: boolean;
  onRefresh: () => void;
  exactFlightHref: string;
};

function coverageLabelKey(tracking: LiveFlightTracking | null): string {
  if (!tracking) return "watchlist.live.coverage.loading";
  return `watchlist.live.coverage.${tracking.coverage}`;
}

function unavailableCopyKey(tracking: LiveFlightTracking): string | null {
  if (tracking.coverage === "identity_missing") return "watchlist.live.states.identityMissing";
  if (tracking.coverage === "not_configured") return "watchlist.live.states.preparing";
  if (tracking.coverage === "no_coverage") return "watchlist.live.states.noCoverage";
  if (tracking.coverage === "temporarily_unavailable") return "watchlist.live.states.temporarilyUnavailable";
  return null;
}

export function WatchLiveFlightPanel({
  tracking,
  isLoading,
  isRefreshing,
  hasError,
  onRefresh,
  exactFlightHref,
}: WatchLiveFlightPanelProps) {
  const { t, localeTag } = useI18n();
  const tone = liveCoverageTone(tracking);
  const unavailableKey = tracking ? unavailableCopyKey(tracking) : null;
  const isIdentityMissing = tracking?.coverage === "identity_missing";
  const displayTone = hasError ? "warning" : tone;
  const primaryLeg = selectCurrentLiveLeg(tracking);
  const displayLegs = primaryLeg
    ? [primaryLeg, ...(tracking?.legs.filter((leg) => leg !== primaryLeg) ?? [])]
    : [];

  function renderLegHeading(leg: LiveFlightLeg) {
    const operational = leg.operational;
    const flightLabel = leg.identity.flight_number ?? `${leg.identity.origin_iata} → ${leg.identity.destination_iata}`;
    return (
      <div className="watch-live-flight-leg-heading">
        <div>
          <strong>{flightLabel}</strong>
          <span>{leg.identity.origin_iata} → {leg.identity.destination_iata}</span>
        </div>
        <span className={`watch-live-flight-status watch-live-flight-status--${operational?.status ?? "unknown"}`}>
          {operational
            ? t(`watchlist.live.status.${operational.status}`)
            : t("watchlist.live.legUnavailableShort")}
        </span>
      </div>
    );
  }

  function renderLegBody(leg: LiveFlightLeg) {
    const operational = leg.operational;
    if (!operational) {
      return <p className="watch-live-flight-leg-unavailable">{t("watchlist.live.legUnavailable")}</p>;
    }
    const numberFormat = new Intl.NumberFormat(localeTag, { maximumFractionDigits: 0 });
    return (
      <>
        <div className="watch-live-flight-milestones">
          <div className="watch-live-flight-milestone">
            <span>{t("watchlist.live.departure")}</span>
            <strong>{formatLiveTime(milestoneTimestamp(operational.departure), localeTag)}</strong>
            <small>{t(`watchlist.live.timeSource.${milestoneTimeSource(operational.departure)}`)}</small>
            <small>
              {t("watchlist.live.terminalGate", {
                terminal: operational.departure.terminal ?? "--",
                gate: operational.departure.gate ?? "--",
              })}
            </small>
            {operational.departure.delay_minutes && operational.departure.delay_minutes > 0 ? (
              <em>{t("watchlist.live.delay", { minutes: operational.departure.delay_minutes })}</em>
            ) : null}
          </div>
          <div className="watch-live-flight-milestone">
            <span>{t("watchlist.live.arrival")}</span>
            <strong>{formatLiveTime(milestoneTimestamp(operational.arrival), localeTag)}</strong>
            <small>{t(`watchlist.live.timeSource.${milestoneTimeSource(operational.arrival)}`)}</small>
            <small>
              {t("watchlist.live.terminalGate", {
                terminal: operational.arrival.terminal ?? "--",
                gate: operational.arrival.gate ?? "--",
              })}
            </small>
            {operational.arrival.delay_minutes && operational.arrival.delay_minutes > 0 ? (
              <em>{t("watchlist.live.delay", { minutes: operational.arrival.delay_minutes })}</em>
            ) : null}
          </div>
        </div>

        <WatchDelayPrediction prediction={leg.delay_prediction ?? null} />

        <footer className="watch-live-flight-meta">
          <span>
            {!hasError && operational.freshness === "fresh"
              ? t("watchlist.live.fresh")
              : t("watchlist.live.stale")}
          </span>
          {operational.position ? <span>{t("watchlist.live.positionOnMap")}</span> : null}
          <span>{t("watchlist.live.providerSource", { provider: operational.provider })}</span>
          <span>{t("watchlist.live.observedAt", { time: formatLiveTime(operational.observed_at, localeTag) })}</span>
          {operational.position?.altitude_m != null ? (
            <span>{t("watchlist.live.altitude", { value: numberFormat.format(operational.position.altitude_m) })}</span>
          ) : null}
          {operational.position?.speed_mps != null ? (
            <span>{t("watchlist.live.speed", { value: numberFormat.format(operational.position.speed_mps * 3.6) })}</span>
          ) : null}
          {operational.position?.heading_deg != null ? (
            <span>{t("watchlist.live.heading", { value: numberFormat.format(operational.position.heading_deg) })}</span>
          ) : null}
          {operational.callsign ? <span>{operational.callsign}</span> : null}
        </footer>
      </>
    );
  }

  return (
    <section className="watch-live-flight" aria-labelledby="watch-live-flight-title">
      <header className="watch-live-flight-header">
        <div>
          <span className="watch-live-flight-kicker">{t("watchlist.live.kicker")}</span>
          <h3 id="watch-live-flight-title">{t("watchlist.live.title")}</h3>
        </div>
        <div className="watch-live-flight-header-actions">
          <span className={`status-pill ${displayTone}`}>
            {isLoading && !tracking
              ? t("watchlist.live.coverage.loading")
              : hasError
                ? t("watchlist.live.coverage.temporarily_unavailable")
                : t(coverageLabelKey(tracking))}
          </span>
          {!isIdentityMissing ? (
            <button
              type="button"
              className="btn-ghost btn-compact watch-live-flight-refresh"
              onClick={onRefresh}
              disabled={isLoading || isRefreshing}
            >
              {isRefreshing ? t("watchlist.live.refreshing") : t("watchlist.live.refresh")}
            </button>
          ) : null}
        </div>
      </header>

      {isLoading && !tracking ? (
        <BoneyardLoad name="watch-live-flight-load" className="watch-live-flight-loading" ariaLabel={t("watchlist.live.coverage.loading")}>
          <LoadReference width="72%" />
          <LoadReference width="48%" />
        </BoneyardLoad>
      ) : null}

      {hasError ? (
        <div className="watch-live-flight-notice" role="status" aria-live="polite">
          <strong>{t("watchlist.live.states.connectionTitle")}</strong>
          <span>{t("watchlist.live.states.connectionBody")}</span>
        </div>
      ) : null}

      {tracking && unavailableKey && tracking.legs.every((leg) => !leg.operational) ? (
        <div className="watch-live-flight-empty" role="status" aria-live="polite">
          <span className="watch-live-flight-route-line" aria-hidden="true" />
          <div>
            <strong>{t(`watchlist.live.stateTitles.${tracking.coverage}`)}</strong>
            <p>{t(unavailableKey)}</p>
            {tracking.coverage === "identity_missing" ? (
              <Link className="btn-primary btn-compact watch-live-flight-search" href={exactFlightHref}>
                {t("watchlist.live.findExactFlight")}
              </Link>
            ) : null}
          </div>
        </div>
      ) : null}

      {displayLegs.length > 0 ? (
        <div className="watch-live-flight-legs">
          {displayLegs.map((leg, index) => {
            if (index === 0) {
              return (
              <article className="watch-live-flight-leg" key={leg.identity.flight_instance_fingerprint}>
                {renderLegHeading(leg)}
                {renderLegBody(leg)}
              </article>
              );
            }
            return (
              <details className="watch-live-flight-leg watch-live-flight-leg--secondary" key={leg.identity.flight_instance_fingerprint}>
                <summary>
                  {renderLegHeading(leg)}
                  <span className="watch-live-flight-leg-disclosure">{t("watchlist.live.legDetails")}</span>
                </summary>
                <div className="watch-live-flight-leg-body">{renderLegBody(leg)}</div>
              </details>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}
