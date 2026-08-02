import React, { memo, useEffect, useState } from "react";

import { CommunityPriceSignal } from "@/modules/community-routes/CommunityPriceSignal";
import { communityRouteKey } from "@/modules/community-routes/communityRoutesApi";
import { useCommunityRouteInsights } from "@/modules/community-routes/useCommunityRouteInsights";
import type { SearchResult } from "@/modules/quick-search/types";
import {
  getOfficialRyanairFlightDeepLink,
  getOfficialRyanairRouteDeepLink,
  isGenericHttpLink,
  isOfficialWizzAirDeepLink,
} from "@/modules/quick-search/api/quickSearchDeepLinks";
import { QuickSearchProviderBadge } from "@/modules/quick-search/components/QuickSearchProviderBadge";
import { resolveQuickSearchProviderPresentation } from "@/modules/quick-search/providerPresentation";
import { getAirportMeta } from "@/modules/shared/airports";
import type { QuickSearchCopyKey } from "@/modules/shared/quickSearchCopy";
import { FareComparisonPanel } from "@/modules/shared/FareComparisonPanel";
import {
  calculateComparableFare,
  createEmptyFareComparisonProfile,
  type FareComparisonProfile,
} from "@/modules/shared/fareComparison";

type Props = {
  visibleResults: SearchResult[];
  compactView: boolean;
  expandedRows: Record<string, boolean>;
  openRowMenuId: string | null;
  deeplinkUrl: string;
  origin: string;
  destination: string;
  radiusKm: number;
  departAfter: string;
  departBefore: string;
  localeTag: string;
  travelers?: number;
  fareProfile?: FareComparisonProfile;
  onFareProfileChange?: (profile: FareComparisonProfile) => void;
  weatherOrigin?: unknown;
  weatherDestination?: unknown;
  getCopyPayload: (result: SearchResult) => string;
  rowMenuTriggerRefs: React.MutableRefObject<Record<string, HTMLButtonElement | null>>;
  t: (key: QuickSearchCopyKey) => string;
  formatMoney: (value: number, currency?: string) => string;
  formatScore: (value: number) => string;
  formatMinutes: (value?: number | null) => string;
  resultKey: (result: SearchResult, fallback: number) => string;
  canRefreshPrice: (result: SearchResult) => boolean;
  refreshingResultId: string | null;
  refreshPrice: (result: SearchResult) => void;
  isInWatchlist: (result: SearchResult) => boolean;
  getWatchlistHref?: (result: SearchResult) => string;
  addToWatchlist: (result: SearchResult, fareProfile: FareComparisonProfile) => void;
  viewInWatchlist: (result: SearchResult) => void;
  setExpandedRows: React.Dispatch<React.SetStateAction<Record<string, boolean>>>;
  setSelectedResultId: React.Dispatch<React.SetStateAction<string | null>>;
  setOpenRowMenuId: React.Dispatch<React.SetStateAction<string | null>>;
  setCopyModalPayload: React.Dispatch<React.SetStateAction<string>>;
  setCopyModalOpen: React.Dispatch<React.SetStateAction<boolean>>;
  closeRowMenu: (targetId?: string | null) => void;
  onTrackOpenRyanair: () => void;
  onTrackRowOverflow: (rowId: string) => void;
  onTrackCopyParams: (rowId: string) => void;
};

function getRouteAirportLabel(iata: string): { city: string; code: string; hasCity: boolean } {
  const code = iata.trim().toUpperCase();
  const city = getAirportMeta(code)?.city.trim() || code;
  return { city, code, hasCity: city !== code };
}

function renderRouteAirport(label: { city: string; code: string; hasCity: boolean }) {
  return (
    <span className="qs-result-route-airport">
      <span>{label.city}</span>
      {label.hasCity ? <span className="qs-result-route-code">({label.code})</span> : null}
    </span>
  );
}

function formatLegClock(value: string | null | undefined, localeTag: string): string | null {
  if (!value) return null;
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) return null;
  return timestamp.toLocaleTimeString(localeTag, { hour: "2-digit", minute: "2-digit" });
}

function getFiniteMinutes(value: number | null | undefined): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function getResultDurationMinutes(result: SearchResult): number | null {
  return getFiniteMinutes(result.duration_total_min) ?? getFiniteMinutes(result.duration_total);
}

function addMinutesToClock(clock: string | null | undefined, minutes: number | null): string | null {
  if (!clock || minutes === null) return null;
  const match = clock.trim().match(/^(\d{1,2}):(\d{2})$/);
  if (!match) return null;
  const hours = Number(match[1]);
  const clockMinutes = Number(match[2]);
  if (!Number.isInteger(hours) || !Number.isInteger(clockMinutes) || hours > 23 || clockMinutes > 59) return null;
  const totalMinutes = (hours * 60 + clockMinutes + minutes) % (24 * 60);
  const arrivalMinutes = totalMinutes < 0 ? totalMinutes + 24 * 60 : totalMinutes;
  const arrivalHours = Math.floor(arrivalMinutes / 60);
  return `${String(arrivalHours).padStart(2, "0")}:${String(arrivalMinutes % 60).padStart(2, "0")}`;
}

function getLegDurationMinutes(depTs: string | null | undefined, arrTs: string | null | undefined): number | null {
  if (!depTs || !arrTs) return null;
  const depTime = new Date(depTs).getTime();
  const arrTime = new Date(arrTs).getTime();
  if (Number.isNaN(depTime) || Number.isNaN(arrTime) || arrTime < depTime) return null;
  return Math.round((arrTime - depTime) / 60000);
}

function QuickSearchResultsListInner(props: Props) {
  const travelers = props.travelers ?? 1;
  const [internalFareProfile, setInternalFareProfile] = useState(() => createEmptyFareComparisonProfile(travelers));
  const fareProfile = props.fareProfile ?? internalFareProfile;
  const setFareProfile = props.onFareProfileChange ?? setInternalFareProfile;
  useEffect(() => {
    if (fareProfile.travelers !== travelers) {
      setFareProfile({ ...fareProfile, travelers });
    }
  }, [fareProfile, setFareProfile, travelers]);
  const locale = props.localeTag.toLowerCase().startsWith("es") ? "es" : "en";
  const communityInsights = useCommunityRouteInsights(
    props.visibleResults.map((result) => ({
      origin_iata: result.origin,
      destination_iata: result.destination,
    })),
  );

  return (
    <>
      {props.visibleResults.length > 0 ? (
        <>
          <FareComparisonPanel
            profile={fareProfile}
            locale={locale}
            onChange={setFareProfile}
          />
          <div className={`qs-results-list ${props.compactView ? "compact" : ""}`}>
          {props.visibleResults.map((r, idx) => {
            const rowId = props.resultKey(r, idx);
            const provider = resolveQuickSearchProviderPresentation(r.source, props.t("sourceUnknown"));
            const ryanairResultLink = getOfficialRyanairFlightDeepLink(r.deeplink_url);
            const ryanairFallbackLink = getOfficialRyanairRouteDeepLink(
              props.deeplinkUrl,
              r.origin,
              r.destination,
              r.travel_date,
            );
            const rowLink = provider.id === "ryanair"
              ? (ryanairResultLink || ryanairFallbackLink)
              : provider.id === "wizzair"
                ? (isOfficialWizzAirDeepLink(r.deeplink_url) ? r.deeplink_url : "")
                : (isGenericHttpLink(r.deeplink_url) ? r.deeplink_url ?? "" : "");
            const expanded = Boolean(props.expandedRows[rowId]);
            const detailsId = `details-${rowId}`;
            const aiReason = typeof r.ai_preferred_reason === "string" ? r.ai_preferred_reason.trim() : "";
            const rawSourceLabel = typeof r.source === "string" ? r.source.trim() : "";
            const canRefreshPrice = props.canRefreshPrice(r);
            const isRefreshingPrice = props.refreshingResultId === rowId;
            const originLabel = getRouteAirportLabel(r.origin);
            const destinationLabel = getRouteAirportLabel(r.destination);
            const firstLeg = r.legs?.[0];
            const lastLeg = r.legs?.length ? r.legs[r.legs.length - 1] : undefined;
            const totalDurationMinutes = getResultDurationMinutes(r);
            const departureClock = r.departure_time_local || formatLegClock(firstLeg?.dep_ts, props.localeTag);
            const arrivalClock = formatLegClock(lastLeg?.arr_ts, props.localeTag) ?? addMinutesToClock(departureClock, totalDurationMinutes);
            const flightTimeLabel = totalDurationMinutes !== null ? props.formatMinutes(totalDurationMinutes) : null;
            const watchlistHref = props.getWatchlistHref?.(r) || "/watchlist";
            const recommendationTooltipId = `recommendation-${rowId}`;
            const fare = calculateComparableFare(
              r.price_total ?? r.price,
              r.currency,
              fareProfile,
              r.source,
              r.legs?.map((leg) => leg.carrier_code) ?? [],
              r.legs?.length || 1,
            );
            const hasSelectedExtras = fareProfile.extras.some((extra) => extra.selected);
            const comparablePrice = !hasSelectedExtras
              ? props.formatMoney(fare.base_total, r.currency)
              : fare.comparable_max_total === null
                ? `${props.t("fromLabel")} ${props.formatMoney(fare.comparable_min_total, r.currency)}`
                : fare.comparable_min_total === fare.comparable_max_total
                  ? props.formatMoney(fare.comparable_min_total, r.currency)
                  : `${props.formatMoney(fare.comparable_min_total, r.currency)}–${props.formatMoney(fare.comparable_max_total, r.currency)}`;
            const recommendationLabel = aiReason
              ? `${props.t("aiPreferredReasonLabel")}: ${aiReason}`
              : props.t("aiPreferredAria");
            const recommendationMark = r.ai_preferred ? (
              <span
                className="qs-result-recommendation"
                tabIndex={0}
                aria-label={props.t("aiPreferredAria")}
                aria-describedby={recommendationTooltipId}
              >
                <svg className="qs-result-recommendation-star" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="m12 2.9 2.72 5.5 6.07.88-4.4 4.28 1.04 6.05L12 16.75l-5.43 2.86 1.04-6.05-4.4-4.28 6.07-.88L12 2.9Z" />
                </svg>
                <span className="qs-result-recommendation-tooltip" id={recommendationTooltipId} role="tooltip">
                  {recommendationLabel}
                </span>
              </span>
            ) : null;
            return (
              <article
                key={rowId}
                className={`qs-result-row ${expanded ? "expanded" : ""} ${props.compactView ? "qs-result-row-compact" : ""} ${r.ai_preferred ? "qs-result-row-ai" : ""}`}
              >
                <div className="qs-result-main">
                  {props.compactView ? (
                    <>
                      <div className="qs-result-route">
                        <strong>
                          {renderRouteAirport(originLabel)}
                          <span className="qs-result-route-arrow">{" → "}</span>
                          {renderRouteAirport(destinationLabel)}
                        </strong>
                        {recommendationMark}
                      </div>
                      <div className="qs-result-meta qs-result-meta-compact">
                        <span>{r.travel_date}</span>
                        <span>{props.t("weatherDepart")} {departureClock || "--"}</span>
                        {arrivalClock ? <span>{props.t("weatherArrive")} {arrivalClock}</span> : null}
                      </div>
                      <div className="qs-result-provider">
                        <QuickSearchProviderBadge source={r.source} unknownLabel={props.t("sourceUnknown")} variant="logo" />
                      </div>
                    </>
                  ) : (
                    <>
                      <span className="qs-result-kicker">{props.t("resultsColRoute")}</span>
                      <div className="qs-result-route">
                        <strong>
                          {renderRouteAirport(originLabel)}
                          <span className="qs-result-route-arrow">{" → "}</span>
                          {renderRouteAirport(destinationLabel)}
                        </strong>
                      </div>
                      {recommendationMark}
                      <div className="qs-result-meta">
                        <span>{r.travel_date}</span>
                        {departureClock ? <span><strong>{props.t("weatherDepart")}:</strong> {departureClock}</span> : null}
                        {arrivalClock ? <span><strong>{props.t("weatherArrive")}:</strong> {arrivalClock}</span> : null}
                      </div>
                      <div className="qs-result-provider">
                        <QuickSearchProviderBadge source={r.source} unknownLabel={props.t("sourceUnknown")} variant="logo" />
                      </div>
                    </>
                  )}
                </div>
                <CommunityPriceSignal
                  insight={communityInsights.get(communityRouteKey({
                    origin_iata: r.origin,
                    destination_iata: r.destination,
                  }))}
                  localeTag={props.localeTag}
                />
                <div className="qs-result-actions">
                  <div className="qs-result-price">
                    {!props.compactView ? <span className="qs-result-kicker">{props.t("resultsColPrice")}</span> : null}
                    <strong>{comparablePrice}</strong>
                    {hasSelectedExtras ? (
                      <span className={fare.is_complete ? "qs-result-comparable-note" : "qs-result-comparable-note qs-result-comparable-note--missing"}>
                        {fare.is_complete
                          ? fare.extras_max_total === null
                            ? `${props.t("extrasFromLabel")} ${props.formatMoney(fare.extras_min_total, r.currency)} · ${fare.airline_label ?? props.t("unknownAirline")}`
                            : `Base ${props.formatMoney(fare.base_total, r.currency)} + extras ${props.formatMoney(fare.extras_min_total, r.currency)}–${props.formatMoney(fare.extras_max_total, r.currency)}`
                          : `${fare.unavailable_kinds.length} ${props.t("unavailableKindsNoPublicFare")}`}
                        {fare.source_url ? (
                          <a href={fare.source_url} target="_blank" rel="noreferrer">
                            {props.t("officialSource")}
                          </a>
                        ) : null}
                      </span>
                    ) : null}
                    {!props.compactView && r.ranking_score ? <span>{props.t("score")} {props.formatScore(r.ranking_score)}</span> : null}
                  </div>
                  <div className="qs-result-buttons">
                    {props.isInWatchlist(r) ? (
                      <a className="btn-ghost qs-row-saved" href={watchlistHref} onClick={() => props.viewInWatchlist(r)}>
                        <span className="qs-row-saved-indicator" aria-hidden="true" />
                        {props.t("viewWatchlist")}
                      </a>
                    ) : (
                      <button className="btn-secondary qs-row-save" type="button" onClick={() => props.addToWatchlist(r, fareProfile)}>
                        {props.t("save")}
                      </button>
                    )}
                    <div className="qs-result-flight-actions">
                      {flightTimeLabel ? (
                        <span className="qs-result-flight-time">
                          {props.t("flightTime")}: <strong>{flightTimeLabel}</strong>
                        </span>
                      ) : null}
                      {!props.compactView && rowLink ? (
                        <a
                          className="btn-ghost qs-row-open-ryanair"
                          href={rowLink}
                          target="_blank"
                          rel="noreferrer"
                          onClick={props.onTrackOpenRyanair}
                        >
                          {props.t("deepLink")}
                        </a>
                      ) : null}
                      <div className="qs-row-menu-wrap">
                        <button
                          type="button"
                          className="btn-ghost qs-row-menu-trigger"
                          aria-haspopup="menu"
                          aria-expanded={props.openRowMenuId === rowId}
                          aria-controls={`row-menu-${rowId}`}
                          aria-label={props.t("rowActionsMoreAria")}
                          ref={(node) => {
                            props.rowMenuTriggerRefs.current[rowId] = node;
                          }}
                          onClick={() => {
                            props.setOpenRowMenuId((prev) => {
                              const next = prev === rowId ? null : rowId;
                              if (next === rowId) props.onTrackRowOverflow(rowId);
                              return next;
                            });
                          }}
                        >
                          <svg className="qs-inline-icon" viewBox="0 0 24 24" aria-hidden="true">
                            <circle cx="6" cy="12" r="1.7" fill="currentColor" />
                            <circle cx="12" cy="12" r="1.7" fill="currentColor" />
                            <circle cx="18" cy="12" r="1.7" fill="currentColor" />
                          </svg>
                        </button>
                        {props.openRowMenuId === rowId ? (
                          <div
                            id={`row-menu-${rowId}`}
                            className="qs-row-menu"
                            role="menu"
                            aria-label={props.t("rowActionsMenuAria")}
                            onKeyDown={(event) => {
                              if (event.key === "Escape") {
                                event.preventDefault();
                                props.closeRowMenu(rowId);
                              }
                            }}
                          >
                          {!props.compactView ? (
                            <button
                              type="button"
                              role="menuitem"
                              className="qs-row-menu-item"
                              aria-expanded={expanded}
                              aria-controls={detailsId}
                              onClick={() => {
                                props.setExpandedRows((prev) => ({ ...prev, [rowId]: !prev[rowId] }));
                                props.setSelectedResultId(rowId);
                                props.setOpenRowMenuId(null);
                              }}
                            >
                              {expanded ? props.t("detailsHide") : props.t("detailsToggle")}
                            </button>
                          ) : null}
                          <button
                            type="button"
                            role="menuitem"
                            className="qs-row-menu-item"
                            onClick={() => {
                              props.onTrackCopyParams(rowId);
                              props.setCopyModalPayload(props.getCopyPayload(r));
                              props.setCopyModalOpen(true);
                              props.setOpenRowMenuId(null);
                            }}
                          >
                            {props.t("deepLinkAlt")}
                          </button>
                          {canRefreshPrice ? (
                            <button
                              type="button"
                              role="menuitem"
                              className="qs-row-menu-item"
                              disabled={isRefreshingPrice}
                              aria-busy={isRefreshingPrice}
                              onClick={() => {
                                props.refreshPrice(r);
                                props.setOpenRowMenuId(null);
                              }}
                            >
                              {isRefreshingPrice ? props.t("refreshPriceLoading") : props.t("refreshPrice")}
                            </button>
                          ) : null}
                          {rowLink ? (
                            <a
                              role="menuitem"
                              className="qs-row-menu-item"
                              href={rowLink}
                              target="_blank"
                              rel="noreferrer"
                              onClick={() => {
                                props.onTrackOpenRyanair();
                                props.setOpenRowMenuId(null);
                              }}
                            >
                              {props.t("deepLink")}
                            </a>
                          ) : null}
                          </div>
                        ) : null}
                      </div>
                    </div>
                  </div>
                </div>
                {!props.compactView && expanded ? (
                  <div className="qs-result-details" id={detailsId}>
                    <div>
                      <strong>{props.t("detailsAlt")}</strong>
                      <p>{r.distance_km_ground ? `${r.distance_km_ground} km` : "--"} - {props.t("summaryRadius")} {props.radiusKm} km</p>
                    </div>
                    <div>
                      <strong>{props.t("detailsWindow")}</strong>
                      <p>{props.departAfter} - {props.departBefore}</p>
                    </div>
                    <div>
                      <strong>{props.t("detailsScore")}</strong>
                      <p>{props.t("scoreHint")} - {r.ranking_score ? props.formatScore(r.ranking_score) : "--"}</p>
                    </div>
                    <div>
                      <strong>{props.t("source")}</strong>
                      <div className="qs-result-source-block">
                        <p className="qs-result-source-name">{provider.label}</p>
                        {rawSourceLabel && rawSourceLabel !== provider.label ? (
                          <p className="qs-result-source-raw">{rawSourceLabel}</p>
                        ) : null}
                      </div>
                    </div>
                    {r.legs && r.legs.length > 0 ? (
                      <div className="qs-legs">
                        <strong>{props.t("detailsLegs")}</strong>
                        {r.legs.map((leg, legIdx) => {
                          const legDepartureClock = formatLegClock(leg.dep_ts, props.localeTag);
                          const legArrivalClock = formatLegClock(leg.arr_ts, props.localeTag);
                          const legDurationMinutes = getLegDurationMinutes(leg.dep_ts, leg.arr_ts);
                          const legFlightTimeLabel = legDurationMinutes !== null ? props.formatMinutes(legDurationMinutes) : null;
                          return (
                            <div key={`${rowId}-leg-${legIdx}`} className="qs-leg-row">
                              <span>{leg.origin_iata} {" → "} {leg.destination_iata}</span>
                              <span>{props.t("weatherDepart")} {legDepartureClock || "--"}</span>
                              <span>
                                {props.t("weatherArrive")} {legArrivalClock || "--"}
                                {legFlightTimeLabel ? ` · ${props.t("flightTime")} ${legFlightTimeLabel}` : ""}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </article>
            );
          })}
          </div>
        </>
      ) : null}

    </>
  );
}

export const QuickSearchResultsList = memo(QuickSearchResultsListInner);
