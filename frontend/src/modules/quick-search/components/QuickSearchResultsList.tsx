import React, { memo } from "react";

import type { SearchResult } from "@/modules/quick-search/types";
import { getOfficialRyanairFlightDeepLink, isGenericHttpLink, isOfficialWizzAirDeepLink } from "@/modules/quick-search/api/quickSearchDeepLinks";
import { QuickSearchProviderBadge } from "@/modules/quick-search/components/QuickSearchProviderBadge";
import { resolveQuickSearchProviderPresentation } from "@/modules/quick-search/providerPresentation";
import { getAirportMeta } from "@/modules/shared/airports";
import type { QuickSearchCopyKey } from "@/modules/shared/quickSearchCopy";

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
  weatherOrigin?: unknown;
  weatherDestination?: unknown;
  getCopyPayload: (result: SearchResult) => string;
  rowMenuTriggerRefs: React.MutableRefObject<Record<string, HTMLButtonElement | null>>;
  t: (key: QuickSearchCopyKey) => string;
  formatMoney: (value: number, currency?: string) => string;
  formatScore: (value: number) => string;
  formatMinutes: (value?: number | null) => string;
  resultKey: (result: SearchResult, fallback: number) => string;
  getResultTags: (result: SearchResult, mode: "normal" | "compact" | "expanded") => Array<{ key: string; label: string; tone: string }>;
  canRefreshPrice: (result: SearchResult) => boolean;
  refreshingResultId: string | null;
  refreshPrice: (result: SearchResult) => void;
  isInWatchlist: (result: SearchResult) => boolean;
  addToWatchlist: (result: SearchResult) => void;
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
  return (
    <>
      {props.visibleResults.length > 0 ? (
        <div className={`qs-results-list ${props.compactView ? "compact" : ""}`}>
          {props.visibleResults.map((r, idx) => {
            const rowId = props.resultKey(r, idx);
            const provider = resolveQuickSearchProviderPresentation(r.source, props.t("sourceUnknown"));
            const ryanairResultLink = getOfficialRyanairFlightDeepLink(r.deeplink_url);
            const ryanairFallbackLink = getOfficialRyanairFlightDeepLink(props.deeplinkUrl);
            const rowLink = provider.id === "ryanair"
              ? (ryanairResultLink || ryanairFallbackLink)
              : provider.id === "wizzair"
                ? (isOfficialWizzAirDeepLink(r.deeplink_url) ? r.deeplink_url : "")
                : (isGenericHttpLink(r.deeplink_url) ? r.deeplink_url ?? "" : "");
            const expanded = Boolean(props.expandedRows[rowId]);
            const detailsId = `details-${rowId}`;
            const compactTags = props.getResultTags(r, "compact");
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
                        {(r.origin !== props.origin || r.destination !== props.destination) ? <span className="chip">{props.t("alternative")}</span> : null}
                      </div>
                      <div className="qs-result-meta qs-result-meta-compact">
                        <span>{props.t("weatherDepart")} {departureClock || "--"}</span>
                        {arrivalClock ? <span>{props.t("weatherArrive")} {arrivalClock}</span> : null}
                        {flightTimeLabel ? <span>{props.t("flightTime")} {flightTimeLabel}</span> : null}
                      </div>
                      <div className="qs-result-badges">
                        <QuickSearchProviderBadge source={r.source} unknownLabel={props.t("sourceUnknown")} />
                        {compactTags.map((tag) => (
                          <span
                            key={`${rowId}-${tag.key}`}
                            className={`qs-tag qs-tag-${tag.tone}`}
                            aria-label={tag.key === "ai-preferred" ? props.t("aiPreferredAria") : undefined}
                          >
                            {tag.label}
                          </span>
                        ))}
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
                        {(r.origin !== props.origin || r.destination !== props.destination) ? <span className="chip">{props.t("alternative")}</span> : null}
                      </div>
                      <div className="qs-result-meta">
                        <span>{r.travel_date}</span>
                        {departureClock ? <span><strong>{props.t("weatherDepart")}:</strong> {departureClock}</span> : null}
                        {arrivalClock ? <span><strong>{props.t("weatherArrive")}:</strong> {arrivalClock}</span> : null}
                        {flightTimeLabel ? <span><strong>{props.t("flightTime")}:</strong> {flightTimeLabel}</span> : null}
                        {r.distance_km_ground ? <span>{" - "}{r.distance_km_ground} km</span> : null}
                      </div>
                      <div className="qs-result-badges">
                        <QuickSearchProviderBadge source={r.source} unknownLabel={props.t("sourceUnknown")} />
                        {props.getResultTags(r, "normal").map((tag) => (
                          <span
                            key={`${rowId}-${tag.key}`}
                            className={`qs-tag qs-tag-${tag.tone}`}
                            aria-label={tag.key === "ai-preferred" ? props.t("aiPreferredAria") : undefined}
                          >
                            {tag.label}
                          </span>
                        ))}
                      </div>
                      {r.ai_preferred && aiReason ? (
                        <p className="qs-result-ai-reason">
                          <strong>{props.t("aiPreferredReasonLabel")}:</strong> {aiReason}
                        </p>
                      ) : null}
                    </>
                  )}
                </div>
                <div className="qs-result-actions">
                  <div className="qs-result-price">
                    {!props.compactView ? <span className="qs-result-kicker">{props.t("resultsColPrice")}</span> : null}
                    <strong>{props.formatMoney(r.price_total ?? r.price, r.currency)}</strong>
                    {!props.compactView && r.ranking_score ? <span>{props.t("score")} {props.formatScore(r.ranking_score)}</span> : null}
                  </div>
                  <div className="qs-result-buttons">
                    {props.isInWatchlist(r) ? (
                      <button className="btn-ghost qs-row-saved" type="button" onClick={() => props.viewInWatchlist(r)}>
                        {props.t("viewWatchlist")}
                      </button>
                    ) : (
                      <button className="btn-secondary qs-row-save" type="button" onClick={() => props.addToWatchlist(r)}>
                        {props.t("save")}
                      </button>
                    )}
                    {!props.compactView ? (
                      <button
                        type="button"
                        className="btn-ghost qs-result-details-link"
                        aria-expanded={expanded}
                        aria-controls={detailsId}
                        onClick={() => {
                          props.setExpandedRows((prev) => ({ ...prev, [rowId]: !prev[rowId] }));
                          props.setSelectedResultId(rowId);
                        }}
                      >
                        {expanded ? props.t("detailsHide") : props.t("detailsToggle")}
                      </button>
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
                {!props.compactView && expanded ? (
                  <div className="qs-result-details" id={detailsId}>
                    <div className="qs-result-detail-tags">
                      {props.getResultTags(r, "expanded").map((tag) => (
                        <span
                          key={`${detailsId}-${tag.key}`}
                          className={`qs-tag qs-tag-${tag.tone}`}
                          aria-label={tag.key === "ai-preferred" ? props.t("aiPreferredAria") : undefined}
                        >
                          {tag.label}
                        </span>
                      ))}
                      {r.minutes_buffer !== null && r.minutes_buffer !== undefined ? (
                        <span className="qs-tag qs-tag-fresh">{props.t("detailsBuffer")} {r.minutes_buffer} min</span>
                      ) : null}
                    </div>
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
                    {r.ai_preferred && aiReason ? (
                      <div>
                        <strong>{props.t("aiPreferredReasonLabel")}</strong>
                        <p>{aiReason}</p>
                      </div>
                    ) : null}
                    <div>
                      <strong>{props.t("source")}</strong>
                      <div className="qs-result-source-block">
                        <QuickSearchProviderBadge source={r.source} unknownLabel={props.t("sourceUnknown")} />
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
      ) : null}

    </>
  );
}

export const QuickSearchResultsList = memo(QuickSearchResultsListInner);
