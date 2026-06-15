import React, { memo } from "react";

import { SearchResult } from "@/modules/quick-search/types";

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
  t: (key: any) => string;
  formatMoney: (value: number, currency?: string) => string;
  formatScore: (value: number) => string;
  formatMinutes: (value?: number | null) => string;
  resultKey: (result: SearchResult, fallback: number) => string;
  getResultTags: (result: SearchResult, mode: "normal" | "compact" | "expanded") => Array<{ key: string; label: string; tone: string }>;
  canRefreshPrice: (result: SearchResult) => boolean;
  refreshingResultId: string | null;
  refreshPrice: (result: SearchResult) => void;
  addToWatchlist: (result: SearchResult) => void;
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

function isOfficialRyanairFlightDeepLink(value: string | null | undefined): boolean {
  if (!value) return false;
  try {
    const parsed = new URL(value, "https://www.ryanair.com");
    const host = parsed.hostname.toLowerCase();
    const isRyanairHost = host === "ryanair.com" || host.endsWith(".ryanair.com");
    const isFlightSelectPath = parsed.pathname.toLowerCase().includes("/trip/flights/select");
    const queryMap = new Map<string, string>();
    for (const [key, raw] of parsed.searchParams.entries()) {
      queryMap.set(key.toLowerCase(), raw);
    }
    const pick = (...keys: string[]) => {
      for (const key of keys) {
        const value = queryMap.get(key.toLowerCase());
        if (value) return value;
      }
      return "";
    };
    const origin = pick("originIata", "origin_iata", "tpOriginIata");
    const destination = pick("destinationIata", "destination_iata", "tpDestinationIata");
    const dateOut = pick("dateOut", "date_out", "tpStartDate");
    const hasRouteParams = Boolean(origin && destination);
    const hasDateOut = Boolean(dateOut);
    return isRyanairHost && isFlightSelectPath && hasRouteParams && hasDateOut;
  } catch {
    return false;
  }
}

function QuickSearchResultsListInner(props: Props) {
  return (
    <>
      {props.visibleResults.length > 0 ? (
        <div className={`qs-results-list ${props.compactView ? "compact" : ""}`}>
          {props.visibleResults.map((r, idx) => {
            const rowId = props.resultKey(r, idx);
            const rowLink = isOfficialRyanairFlightDeepLink(r.deeplink_url)
              ? r.deeplink_url
              : isOfficialRyanairFlightDeepLink(props.deeplinkUrl)
                ? props.deeplinkUrl
                : "";
            const expanded = Boolean(props.expandedRows[rowId]);
            const detailsId = `details-${rowId}`;
            const compactTags = props.getResultTags(r, "compact");
            const departureCompact = r.departure_time_local || "--";
            const rowDurationLabel = r.duration_total_min ? `${r.duration_total_min} min` : "--";
            const aiReason = typeof r.ai_preferred_reason === "string" ? r.ai_preferred_reason.trim() : "";
            const canRefreshPrice = props.canRefreshPrice(r);
            const isRefreshingPrice = props.refreshingResultId === rowId;
            return (
              <article
                key={rowId}
                className={`qs-result-row ${expanded ? "expanded" : ""} ${props.compactView ? "qs-result-row-compact" : ""} ${r.ai_preferred ? "qs-result-row-ai" : ""}`}
              >
                <div className="qs-result-main">
                  {props.compactView ? (
                    <>
                      <div className="qs-result-route">
                        <strong>{r.origin}{" → "}{r.destination}</strong>
                        {(r.origin !== props.origin || r.destination !== props.destination) ? <span className="chip">{props.t("alternative")}</span> : null}
                      </div>
                      <div className="qs-result-meta qs-result-meta-compact">
                        <span>{departureCompact}</span>
                      </div>
                      <div className="qs-result-badges">
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
                        <strong>{r.origin}{" → "}{r.destination}</strong>
                        {(r.origin !== props.origin || r.destination !== props.destination) ? <span className="chip">{props.t("alternative")}</span> : null}
                      </div>
                      <div className="qs-result-meta">
                        <span>{r.travel_date}</span>
                        {r.departure_time_local ? <span>{" - "}{r.departure_time_local}</span> : null}
                        {r.distance_km_ground ? <span>{" - "}{r.distance_km_ground} km</span> : null}
                      </div>
                      <div className="qs-result-stats">
                        <span><strong>{props.t("resultsColDuration")}:</strong> {rowDurationLabel}</span>
                      </div>
                      <div className="qs-result-badges">
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
                    <button className="btn-secondary qs-row-save" type="button" onClick={() => props.addToWatchlist(r)}>
                      {props.t("save")}
                    </button>
                    {canRefreshPrice ? (
                      <button
                        className="btn-ghost qs-row-refresh"
                        type="button"
                        disabled={isRefreshingPrice}
                        aria-busy={isRefreshingPrice}
                        onClick={() => props.refreshPrice(r)}
                      >
                        {isRefreshingPrice ? props.t("refreshPriceLoading") : props.t("refreshPrice")}
                      </button>
                    ) : null}
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
                      {r.duration_total_min !== null && r.duration_total_min !== undefined ? (
                        <span className="qs-tag qs-tag-fresh">{props.t("resultsColDuration")}: {r.duration_total_min} min</span>
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
                      <p>{(r.source || "").trim() || props.t("sourceUnknown")}</p>
                    </div>
                    {r.legs && r.legs.length > 0 ? (
                      <div className="qs-legs">
                        <strong>{props.t("detailsLegs")}</strong>
                        {r.legs.map((leg, legIdx) => (
                          <div key={`${rowId}-leg-${legIdx}`} className="qs-leg-row">
                            <span>{leg.origin_iata} {" → "} {leg.destination_iata}</span>
                            <span>{new Date(leg.dep_ts).toLocaleTimeString(props.localeTag, { hour: "2-digit", minute: "2-digit" })}</span>
                            <span>{new Date(leg.arr_ts).toLocaleTimeString(props.localeTag, { hour: "2-digit", minute: "2-digit" })}</span>
                          </div>
                        ))}
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
