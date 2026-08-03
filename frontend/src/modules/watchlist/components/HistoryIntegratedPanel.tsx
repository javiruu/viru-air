import type {
  CSSProperties,
  MouseEvent as ReactMouseEvent,
  PointerEvent as ReactPointerEvent,
} from "react";
import { useEffect, useRef } from "react";

import { useI18n } from "@/i18n";
import { CommunityPriceReferenceBand } from "@/modules/community-routes/CommunityPriceReferenceBand";
import { RelatedCommunityRoutes } from "@/modules/community-routes/RelatedCommunityRoutes";
import type { CommunityPricing } from "@/modules/watchlist/types";
import { formatCurrency } from "@/modules/shared/format";
import type { WatchlistChartSerie } from "@/modules/watchlist/chartModel";
import { formatDateTime } from "@/modules/watchlist/presentation";
import { getFreshnessPresentation } from "@/modules/watchlist/summary";

type ViewMode = "chart" | "calendar";

type SelectedWatch = {
  origin_iata: string;
  destination_iata: string;
  travel_date_local: string;
  status: string;
  community_pricing: CommunityPricing;
} | null;

type SelectedPointData = {
  capturedAt: string;
  date: string;
  price: number;
  currency: string;
  departureTime: string | null;
  sourceKind?: string;
} | null;

type HoverPoint = {
  x: number;
  y: number;
  date: string;
  capturedAt: string;
  price: number;
  currency: string;
  departureTime: string | null;
  color: string;
  sourceKind?: string;
  isStale?: boolean;
} | null;

type CalendarEvent = {
  min: number;
  max: number;
  count: number;
};

type CalendarRange = {
  min: number;
  max: number;
} | null;

type HistoryIntegratedPanelProps = {
  selectedWatch: SelectedWatch;
  viewMode: ViewMode;
  isLoadingHistory: boolean;
  isRefreshingHistory: boolean;
  isRefreshingFiltered: boolean;
  selectedOrigin: string;
  selectedDestination: string;
  selectedDates: string[];
  selectedPoint: string;
  chartIsCompact: boolean;
  chartHeight: number;
  chartModel: WatchlistChartSerie[] | null;
  selectedPointData: SelectedPointData;
  hoverPoint: HoverPoint;
  visibleMonth: string;
  monthTitle: string;
  monthCells: Array<string | null>;
  calendarEvents: Record<string, CalendarEvent>;
  calendarRange: CalendarRange;
  calendarCurrency: string;
  calendarHasUsefulData: boolean;
  chartWidth: number;
  chartPad: { left: number; right: number; top: number; bottom: number };
  chartViewBox: { x: number; y: number; width: number; height: number };
  chartIsZoomed: boolean;
  chartIsDragging: boolean;
  onApplyFilters: () => void;
  onChartMouseMove: (event: ReactMouseEvent<SVGSVGElement>) => void;
  onChartMouseLeave: () => void;
  onChartWheel: (event: WheelEvent) => void;
  onChartPointerDown: (event: ReactPointerEvent<SVGSVGElement>) => void;
  onChartPointerMove: (event: ReactPointerEvent<SVGSVGElement>) => void;
  onChartPointerUp: (event: ReactPointerEvent<SVGSVGElement>) => void;
  onChartPointerCancel: (event: ReactPointerEvent<SVGSVGElement>) => void;
  onChartPointerLeave: (event: ReactPointerEvent<SVGSVGElement>) => void;
  onResetChartZoom: () => void;
  onPrevMonth: () => void;
  onNextMonth: () => void;
};

export function HistoryIntegratedPanel({
  selectedWatch,
  viewMode,
  isLoadingHistory,
  isRefreshingHistory,
  isRefreshingFiltered,
  selectedOrigin,
  selectedDestination,
  selectedDates,
  selectedPoint,
  chartIsCompact,
  chartHeight,
  chartModel,
  selectedPointData,
  hoverPoint,
  visibleMonth,
  monthTitle,
  monthCells,
  calendarEvents,
  calendarRange,
  calendarCurrency,
  calendarHasUsefulData,
  chartWidth,
  chartPad,
  chartViewBox,
  chartIsZoomed,
  chartIsDragging,
  onApplyFilters,
  onChartMouseMove,
  onChartMouseLeave,
  onChartWheel,
  onChartPointerDown,
  onChartPointerMove,
  onChartPointerUp,
  onChartPointerCancel,
  onChartPointerLeave,
  onResetChartZoom,
  onPrevMonth,
  onNextMonth,
}: HistoryIntegratedPanelProps) {
  const { t, localeTag } = useI18n();
  const chartSvgRef = useRef<SVGSVGElement | null>(null);
  const hasSelectedWatch = Boolean(selectedWatch);
  const hasChartData = Boolean(chartModel && chartModel.length > 0);
  const chartPointCount = chartModel?.reduce((acc, serie) => acc + serie.points.length, 0) ?? 0;
  const hasCalendarData = Boolean(visibleMonth);
  const canToggleCalendar = hasCalendarData && calendarHasUsefulData;

  const calendarMidpoint = calendarRange ? calendarRange.min + (calendarRange.max - calendarRange.min) / 2 : null;
  const weekdays = t("watchlist.history.weekdays")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
  const selectedRouteValue = selectedWatch
    ? selectedWatch.travel_date_local
    : t("watchlist.history.selectFlightPlaceholder");
  const rangeTitle = t("watchlist.history.rangeTitle");
  const statusLabel = !selectedWatch
    ? t("watchlist.history.status.noData")
    : selectedWatch.status === "active"
      ? t("watchlist.history.status.active")
      : selectedWatch.status === "paused"
        ? t("watchlist.history.status.paused")
        : t("watchlist.history.status.noData");
  const statusTone = !selectedWatch
    ? "info"
    : selectedWatch.status === "active"
      ? "success"
      : selectedWatch.status === "paused"
        ? "warning"
        : "info";
  const allChartPoints = chartModel?.flatMap((serie) => serie.points) ?? [];
  const latestPoint =
    allChartPoints.length > 0
      ? allChartPoints.reduce((latest, point) =>
          new Date(point.capturedAt).getTime() > new Date(latest.capturedAt).getTime() ? point : latest,
        )
      : null;
  const selectedPointFreshness = selectedPointData
    ? getFreshnessPresentation({
        t,
        locale: localeTag,
        lastUpdatedAt: selectedPointData.capturedAt,
        freshnessState: "observing",
        observationCount: chartPointCount,
      })
    : null;
  const hoveredRatioX = hoverPoint
    ? Math.min(1, Math.max(0, (hoverPoint.x - chartViewBox.x) / chartViewBox.width))
    : 0;
  const hoveredRatioY = hoverPoint
    ? Math.min(1, Math.max(0, (hoverPoint.y - chartViewBox.y) / chartViewBox.height))
    : 0;

  useEffect(() => {
    const svg = chartSvgRef.current;
    if (!svg || !hasChartData || viewMode !== "chart") return;
    const handleWheel = (event: WheelEvent) => {
      onChartWheel(event);
    };
    svg.addEventListener("wheel", handleWheel, { passive: false });
    return () => {
      svg.removeEventListener("wheel", handleWheel);
    };
  }, [hasChartData, onChartWheel, viewMode]);

  return (
    <section className="panel history-panel section-gap">
      <div className="panel-header">
        <div className="history-heading">
          <h2 className="history-title">
            <span className="history-title-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                <path
                  d="M4 19h16M5 16l4-4 3 3 6-6"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.7"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <path
                  d="M16 9h3v3"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.7"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </span>
            {t("watchlist.history.title")}
          </h2>
          <div className="history-context">
            <p className="muted">
              {hasSelectedWatch ? t("watchlist.history.subtitleWithRoute") : t("watchlist.history.subtitleWithoutRoute")}
            </p>
            <div className="history-route-line">
              <span className="history-route-line-text">{selectedRouteValue}</span>
              <span className={`status-pill ${statusTone}`}>{statusLabel}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="history-filterbar history-filterbar--compact">
        <div className="history-filterbar-header">
          <div className="history-filterbar-actions">
            <button type="button" hidden disabled={!canToggleCalendar}>
              {t("watchlist.history.viewCalendar")}
            </button>
            <button className="btn-compact history-filter-apply" type="button" disabled={isRefreshingFiltered || !hasSelectedWatch} onClick={onApplyFilters}>
              {isRefreshingFiltered ? t("watchlist.history.refreshing") : t("watchlist.history.applyFilters")}
            </button>
          </div>
        </div>
        {!canToggleCalendar ? <span className="history-helper">{t("watchlist.history.calendarUnavailableBody")}</span> : null}

      </div>
      {isRefreshingHistory ? (
        <div className="history-refresh-indicator muted" role="status" aria-live="polite">
          {t("watchlist.history.refreshing")}
        </div>
      ) : null}
      {isLoadingHistory ? (
        <div className="history-loading" role="status" aria-live="polite" aria-label={t("watchlist.smartList.loadingAria")}>
          <div className="skeleton skeleton-line history-skeleton-toolbar" />
          <div className="history-layout">
            <div className="history-primary">
              <span className="skeleton skeleton-block history-skeleton-chart" />
            </div>
            <div className="history-support">
              <span className="skeleton skeleton-line history-skeleton-line" />
              <span className="skeleton skeleton-line history-skeleton-line" />
              <span className="skeleton skeleton-line history-skeleton-line" />
            </div>
          </div>

        </div>
      ) : null}

      {!hasSelectedWatch && !isLoadingHistory ? (
        <div className="panel history-stage history-chart history-scroll history-chart-panel">
          <div className="history-ghost">
            <div className="history-ghost-line" />
            <p>{t("watchlist.history.selectedRouteEmpty")}</p>
          </div>
        </div>
      ) : hasSelectedWatch && !isLoadingHistory && viewMode === "chart" ? (
        <div
          key={`chart-${selectedOrigin}-${selectedDestination}-${selectedDates.join(",")}-${selectedPoint}`}
          className={`panel history-stage history-chart history-scroll history-chart-panel history-layout${chartIsCompact ? " history-chart--compact" : ""}`}
        >
          <div className="history-detail history-support">
            {selectedPointData ? (
              <div className="history-detail-card">
                <div>
                <span className="history-detail-label">{t("watchlist.history.selectedPointLabel")}</span>
                  <strong>{formatCurrency(selectedPointData.price, selectedPointData.currency, localeTag)}</strong>
                </div>
                <div className="history-detail-meta">
                  <span>{formatDateTime(selectedPointData.capturedAt, localeTag)}</span>
                  <span>{selectedPointData.date}</span>
                  {selectedPointData.departureTime ? <span>{t("watchlist.history.departureAt", { value: selectedPointData.departureTime })}</span> : null}
                  {selectedPointFreshness ? <span>{selectedPointFreshness.label}</span> : null}
                </div>
                {selectedPointFreshness?.observationNote ? (
                  <p className="panel-note">{selectedPointFreshness.observationNote}</p>
                ) : null}
              </div>
            ) : null}
          </div>
          <div className="history-primary">
          {chartIsZoomed ? (
            <div className="history-zoom-toolbar">
              <button className="btn-ghost btn-compact history-zoom-reset" type="button" onClick={onResetChartZoom}>
                {t("watchlist.history.resetZoom")}
              </button>
            </div>
          ) : null}
          {hasChartData ? (
            <svg
              ref={chartSvgRef}
              className={`history-svg${chartIsZoomed ? " is-zoomed" : ""}${chartIsDragging ? " is-dragging" : ""}`}
              viewBox={`${chartViewBox.x} ${chartViewBox.y} ${chartViewBox.width} ${chartViewBox.height}`}
              width="100%"
              role="img"
              aria-label={t("watchlist.history.chartAriaLabel")}
              onMouseMove={onChartMouseMove}
              onMouseLeave={onChartMouseLeave}
              onPointerDown={onChartPointerDown}
              onPointerMove={onChartPointerMove}
              onPointerUp={onChartPointerUp}
              onPointerCancel={onChartPointerCancel}
              onPointerLeave={(event) => {
                onChartPointerLeave(event);
                onChartMouseLeave();
              }}
            >
              <line
                x1={chartPad.left}
                y1={chartHeight - chartPad.bottom}
                x2={chartWidth - chartPad.right}
                y2={chartHeight - chartPad.bottom}
                stroke="var(--color-border-strong)"
                strokeWidth="1"
              />
              <line
                x1={chartPad.left}
                y1={chartPad.top}
                x2={chartPad.left}
                y2={chartHeight - chartPad.bottom}
                stroke="var(--color-border-strong)"
                strokeWidth="1"
              />
              {[0.25, 0.5, 0.75].map((ratio) => {
                const y = chartPad.top + (chartHeight - chartPad.top - chartPad.bottom) * ratio;
                return (
                  <line
                    key={`grid-${ratio}`}
                    className="history-grid"
                    x1={chartPad.left}
                    y1={y}
                    x2={chartWidth - chartPad.right}
                    y2={y}
                  />
                );
              })}
              {hoverPoint ? (
                <g className="history-hover">
                  <line
                    x1={hoverPoint.x}
                    y1={chartPad.top}
                    x2={hoverPoint.x}
                    y2={chartHeight - chartPad.bottom}
                    stroke={hoverPoint.color}
                    strokeWidth="1.5"
                    strokeDasharray="4 6"
                  />
                  <circle
                    cx={hoverPoint.x}
                    cy={hoverPoint.y}
                    r={7}
                    fill="var(--color-surface)"
                    stroke={hoverPoint.color}
                    strokeWidth="2.2"
                  />
                </g>
              ) : null}
              {chartModel?.map((serie) => (
                <g key={serie.date}>
                  {serie.areaPoints ? <polygon className="history-area" fill={serie.color} points={serie.areaPoints} /> : null}
                  <polyline
                    fill="none"
                    stroke={serie.color}
                    strokeWidth={chartPointCount < 4 ? 3.4 : 2.8}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    points={serie.path}
                  />
                  {serie.points.map((point) => {
                    const isBackfillPoint = point.sourceKind === "historical_backfill";
                    return (
                      <circle
                        key={`${serie.date}-${point.capturedAt}`}
                        className={isBackfillPoint ? "history-point history-point--backfill" : "history-point"}
                        cx={point.x}
                        cy={point.y}
                        r={selectedPoint === point.capturedAt ? 6.4 : chartPointCount < 4 ? 5 : 4.3}
                        fill={isBackfillPoint ? "var(--panel-bg)" : serie.color}
                        stroke={selectedPoint === point.capturedAt ? "var(--color-text-primary)" : serie.color}
                        strokeDasharray={isBackfillPoint ? "3 3" : undefined}
                        strokeWidth={selectedPoint === point.capturedAt ? 2 : isBackfillPoint ? 1.8 : 1}
                      >
                        <title>{`${serie.date} - ${formatDateTime(point.capturedAt, localeTag)} - ${formatCurrency(point.price, point.currency, localeTag)}${isBackfillPoint ? ` - ${t("watchlist.history.backfillTooltip")}` : ""}`}</title>
                      </circle>
                    );
                  })}
                </g>
              ))}
            </svg>
          ) : (
            <div className="history-ghost">
              <CommunityPriceReferenceBand
                aggregate={selectedWatch?.community_pricing.aggregate}
              />
              {selectedWatch ? (
                <RelatedCommunityRoutes
                  origin={selectedWatch.origin_iata}
                  destination={selectedWatch.destination_iata}
                />
              ) : null}
              <div className="history-ghost-line" />
              <p>{t("watchlist.history.chartEmpty")}</p>
            </div>
          )}
          </div>
          {hoverPoint ? (
            <div
              className="history-tooltip"
              style={{
                left: `${hoveredRatioX * 100}%`,
                top: `${hoveredRatioY * 100}%`,
              }}
            >
              <span className="history-tooltip-tag">{hoverPoint.date}</span>
              <strong>{formatCurrency(hoverPoint.price, hoverPoint.currency, localeTag)}</strong>
              <span>{formatDateTime(hoverPoint.capturedAt, localeTag)}</span>
              {hoverPoint.departureTime ? <span>{t("watchlist.history.departureAt", { value: hoverPoint.departureTime })}</span> : null}
              {hoverPoint.sourceKind === "historical_backfill" ? (
                <span className="history-tooltip-note">{t("watchlist.history.backfillTooltip")}</span>
              ) : null}
            </div>
          ) : null}
          <div className="history-legend">
            {chartModel?.map((serie) => (
              <span key={`tag-${serie.date}`} className="legend-chip">
                <span className="legend-dot" style={{ background: serie.color }} />
                {serie.date}
              </span>
            ))}
          </div>
          {chartPointCount > 0 && chartPointCount < 4 ? (
            <div className="history-compact-note" role="status" aria-live="polite">
              <strong>{t("watchlist.history.chartBuildingTitle")}</strong>
              <p>{t("watchlist.history.chartBuildingBody")}</p>
            </div>
          ) : null}
          <p className="history-microcopy muted">{t("watchlist.history.trendMicrocopy")}</p>
        </div>
      ) : hasSelectedWatch && !isLoadingHistory ? (
        <div key={`calendar-${visibleMonth}`} className="panel history-stage history-calendar history-calendar-panel history-layout">
          {hasCalendarData && calendarHasUsefulData ? (
            <>
              <div className="history-calendar-nav">
                <button className="btn-ghost" type="button" onClick={onPrevMonth}>{t("watchlist.history.prevMonth")}</button>
                <strong className="month-title">{monthTitle}</strong>
                <button className="btn-ghost" type="button" onClick={onNextMonth}>{t("watchlist.history.nextMonth")}</button>
              </div>
              <div className="history-calendar-grid history-primary">
                {(weekdays.length === 7 ? weekdays : ["L", "M", "X", "J", "V", "S", "D"]).map((weekday, index) => (
                  <div key={`history-weekday-${index}`} className="history-weekday">{weekday}</div>
                ))}
                {monthCells.map((day, idx) => {
                  const event = day ? calendarEvents[day] : undefined;
                  let heatStyle: CSSProperties | undefined;
                  if (event && calendarRange && calendarRange.max !== calendarRange.min) {
                    const normalized = (event.min - calendarRange.min) / (calendarRange.max - calendarRange.min);
                    const heat = 1 - normalized;
                    const strong = 0.08 + heat * 0.28;
                    const glow = 0.06 + heat * 0.18;
                    heatStyle = {
                      background: `linear-gradient(135deg, rgba(46, 110, 98, ${strong}), rgba(217, 93, 57, ${glow}))`,
                      borderColor: `rgba(46, 110, 98, ${0.22 + heat * 0.4})`,
                      boxShadow: `0 12px 22px rgba(32, 28, 21, ${0.08 + heat * 0.12})`,
                    };
                  }
                  return (
                    <div
                      key={`${day || "empty"}-${idx}`}
                      className={`history-day ${day ? "has-day" : "empty"} ${event ? "has-event" : ""}`}
                      style={heatStyle}
                    >
                      {day ? (
                        <>
                          <div className="history-day-number">{day.slice(-2)}</div>
                          {event ? (
                            <div className="history-day-meta">
                              {t("watchlist.history.pointsCount", { count: event.count })}
                              <br />
                              {formatCurrency(event.min, calendarCurrency, localeTag)}-{formatCurrency(event.max, calendarCurrency, localeTag)}
                            </div>
                          ) : null}
                        </>
                      ) : null}
                    </div>
                  );
                })}
              </div>
              {calendarRange ? (
                <div className="history-heat-legend">
                  <span className="sr-only" aria-label={t("watchlist.history.rangeLabel")}>
                    {rangeTitle}
                  </span>
                  <span>{t("watchlist.history.cheapest")}</span>
                  <div className="history-heat-bar" />
                  <span>{t("watchlist.history.mostExpensive")}</span>
                  <div className="history-heat-scale">
                    <span className="history-heat-scale-item">
                      <strong>{t("watchlist.history.legendLow")}</strong>
                      <span className="tabular-nums">{formatCurrency(calendarRange.min, calendarCurrency, localeTag)}</span>
                    </span>
                    {calendarMidpoint != null ? (
                      <span className="history-heat-scale-item">
                        <strong>{t("watchlist.history.legendMid")}</strong>
                        <span className="tabular-nums">{formatCurrency(calendarMidpoint, calendarCurrency, localeTag)}</span>
                      </span>
                    ) : null}
                    <span className="history-heat-scale-item">
                      <strong>{t("watchlist.history.legendHigh")}</strong>
                      <span className="tabular-nums">{formatCurrency(calendarRange.max, calendarCurrency, localeTag)}</span>
                    </span>
                  </div>
                  <p className="muted history-heat-explainer">{t("watchlist.history.heatLegendExplainer")}</p>
                </div>
              ) : null}
            </>
          ) : (
            <>
              <CommunityPriceReferenceBand
                aggregate={selectedWatch?.community_pricing.aggregate}
              />
              {selectedWatch ? (
                <RelatedCommunityRoutes
                  origin={selectedWatch.origin_iata}
                  destination={selectedWatch.destination_iata}
                />
              ) : null}
              <div className="history-compact-note history-compact-note--calendar">
                <strong>{t("watchlist.history.calendarUnavailableTitle")}</strong>
                <p>{t("watchlist.history.calendarUnavailableBody")}</p>
              </div>
            </>
          )}
          <p className="history-microcopy muted">{t("watchlist.history.trendMicrocopy")}</p>
        </div>
      ) : null}
    </section>
  );
}


