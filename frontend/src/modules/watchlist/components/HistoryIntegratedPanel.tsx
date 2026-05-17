import type { CSSProperties, MouseEvent as ReactMouseEvent } from "react";

import { useI18n } from "@/i18n";
import { formatCurrency } from "@/modules/shared/format";
import { formatDateTime } from "@/modules/watchlist/presentation";

type ViewMode = "chart" | "calendar";
type RangeWindow = "all" | "7" | "14" | "30" | "90";

type SelectedWatch = {
  origin_iata: string;
  destination_iata: string;
  travel_date_local: string;
  status: string;
} | null;

type PointOption = {
  value: string;
  label: string;
};

type ChartPoint = {
  capturedAt: string;
  price: number;
  currency: string;
  departureTime: string | null;
  x: number;
  y: number;
};

type ChartSerie = {
  date: string;
  color: string;
  path: string;
  points: ChartPoint[];
};

type SelectedPointData = {
  capturedAt: string;
  date: string;
  price: number;
  currency: string;
  departureTime: string | null;
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
  pointOptions: PointOption[];
  rangeWindow: RangeWindow;
  chartIsCompact: boolean;
  chartHeight: number;
  chartModel: ChartSerie[] | null;
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
  onToggleViewMode: () => void;
  onApplyFilters: () => void;
  onPointChange: (value: string) => void;
  onRangeChange: (value: RangeWindow) => void;
  onToggleRangeWindow: () => void;
  onResetZoom: () => void;
  onChartMouseMove: (event: ReactMouseEvent<SVGSVGElement>) => void;
  onChartMouseLeave: () => void;
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
  pointOptions,
  rangeWindow,
  chartIsCompact,
  chartHeight,
  chartModel,
  selectedPointData,    hoverPoint,
    visibleMonth,
  monthTitle,
  monthCells,
  calendarEvents,
  calendarRange,
  calendarCurrency,
  calendarHasUsefulData,
  chartWidth,
  chartPad,
  onToggleViewMode,
  onApplyFilters,
  onPointChange,
  onRangeChange,
  onToggleRangeWindow,
  onResetZoom,
  onChartMouseMove,
  onChartMouseLeave,
  onPrevMonth,
  onNextMonth,
}: HistoryIntegratedPanelProps) {
  const { t } = useI18n();
  const hasSelectedWatch = Boolean(selectedWatch);
  const hasChartData = Boolean(chartModel && chartModel.length > 0);
  const chartPointCount = chartModel?.reduce((acc, serie) => acc + serie.points.length, 0) ?? 0;
  const hasCalendarData = Boolean(visibleMonth);

  const calendarMidpoint = calendarRange ? calendarRange.min + (calendarRange.max - calendarRange.min) / 2 : null;
  const weekdays = t("watchlist.history.weekdays")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
  const selectedRouteValue = selectedWatch
    ? `${selectedWatch.origin_iata} → ${selectedWatch.destination_iata} · ${selectedWatch.travel_date_local}`
    : t("watchlist.history.selectFlightPlaceholder");
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
            {calendarHasUsefulData ? (
              <button className="btn-secondary btn-layered" type="button" onClick={onToggleViewMode}>
                {viewMode === "chart" ? t("watchlist.history.viewCalendar") : t("watchlist.history.viewChart")}
              </button>
            ) : null}
            <button className="btn-compact history-filter-apply" type="button" disabled={isRefreshingFiltered || !hasSelectedWatch} onClick={onApplyFilters}>
              {isRefreshingFiltered ? t("watchlist.history.refreshing") : t("watchlist.history.applyFilters")}
            </button>
          </div>
        </div>

        <div className="filter-grid history-filters">
          <div className="history-filter history-route-summary">
            <span className="history-label">{t("watchlist.history.selectedRouteLabel")}</span>
            <div className="history-input" aria-live="polite">
              {selectedRouteValue}
            </div>
          </div>

          <label className="history-filter history-point">
            <span className="history-label">
              <span className="history-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                  <path
                    d="M4 17h16M5 14l4-4 3 3 6-6"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.6"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </span>
              {t("watchlist.history.pointLabel")}
            </span>
            <select
              className="history-input"
              name="history_point"
              autoComplete="off"
              value={selectedPoint}
              disabled={!hasSelectedWatch || selectedDates.length !== 1 || pointOptions.length === 0}
              onChange={(e) => onPointChange(e.target.value)}
            >
              <option value="">{t("watchlist.history.pointPlaceholder")}</option>
              {pointOptions.map((point) => <option key={point.value} value={point.value}>{point.label}</option>)}
            </select>
            <span className="history-helper">
              {!hasSelectedWatch
                ? t("watchlist.history.pointHelperSelectRoute")
                : selectedDates.length !== 1
                  ? t("watchlist.history.pointHelperSelectOneDate")
                  : pointOptions.length === 0
                    ? t("watchlist.history.pointHelperNoPoints")
                    : t("watchlist.history.pointHelperReady")}
            </span>
          </label>
          <div className="history-filter history-range-inline">
            <span className="history-label">{t("watchlist.history.rangeTitle")}</span>
            <div className="history-range-control">
              <label className="history-range-field">
                <select
                  className="history-input"
                  name="history_range"
                  aria-label={t("watchlist.history.rangeLabel")}
                  autoComplete="off"
                  value={rangeWindow}
                  onChange={(e) => onRangeChange(e.target.value as RangeWindow)}
                >
                  <option value="7">{t("watchlist.history.range7")}</option>
                  <option value="14">{t("watchlist.history.range14")}</option>
                  <option value="30">{t("watchlist.history.range30")}</option>
                  <option value="90">{t("watchlist.history.range90")}</option>
                  <option value="all">{t("watchlist.history.rangeAll")}</option>
                </select>
              </label>
              <div className="history-range-actions">
                <button
                  className={`btn-ghost btn-layered ${rangeWindow === "all" ? "" : "is-active"}`}
                  type="button"
                  aria-pressed={rangeWindow !== "all"}
                  onClick={onToggleRangeWindow}
                >
                  {rangeWindow === "all" ? t("watchlist.history.compactView") : t("watchlist.history.rangeAll")}
                </button>
                <button className="btn-ghost btn-layered" type="button" onClick={onResetZoom}>
                  {t("watchlist.history.resetZoom")}
                </button>
              </div>
            </div>
          </div>
        </div>
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
                  <strong>{formatCurrency(selectedPointData.price, selectedPointData.currency)}</strong>
                </div>
                <div className="history-detail-meta">
                  <span>{formatDateTime(selectedPointData.capturedAt)}</span>
                  <span>{selectedPointData.date}</span>
                  {selectedPointData.departureTime ? <span>{t("watchlist.history.departureAt", { value: selectedPointData.departureTime })}</span> : null}
                </div>
              </div>
            ) : (
              <div className="history-detail-empty">
                {t("watchlist.history.selectPointHelp")}
              </div>
            )}
          </div>
          <div className="history-primary">
          {hasChartData ? (
            <svg
              className="history-svg"
              viewBox={`0 0 ${chartWidth} ${chartHeight}`}
              width="100%"
              role="img"
              aria-label={t("watchlist.history.chartAriaLabel")}
              onMouseMove={onChartMouseMove}
              onMouseLeave={onChartMouseLeave}
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
                  <polyline fill="none" stroke={serie.color} strokeWidth={chartPointCount < 4 ? 3.4 : 2.8} points={serie.path} />
                  {serie.points.map((point) => (
                    <circle
                      key={`${serie.date}-${point.capturedAt}`}
                      cx={point.x}
                      cy={point.y}
                      r={selectedPoint === point.capturedAt ? 6.4 : chartPointCount < 4 ? 5 : 4.3}
                      fill={serie.color}
                      stroke={selectedPoint === point.capturedAt ? "var(--color-text-primary)" : "var(--color-surface)"}
                      strokeWidth={selectedPoint === point.capturedAt ? 2 : 1}
                    >
                      <title>{`${serie.date} - ${formatDateTime(point.capturedAt)} - ${formatCurrency(point.price, point.currency)}`}</title>
                    </circle>
                  ))}
                </g>
              ))}
            </svg>
          ) : (
            <div className="history-ghost">
              <div className="history-ghost-line" />
              <p>{t("watchlist.history.chartEmpty")}</p>
            </div>
          )}
          </div>
          {hoverPoint ? (
            <div
              className="history-tooltip"
              style={{
                left: `${(hoverPoint.x / chartWidth) * 100}%`,
                top: `${(hoverPoint.y / chartHeight) * 100}%`,
              }}
            >
              <span className="history-tooltip-tag">{hoverPoint.date}</span>
              <strong>{formatCurrency(hoverPoint.price, hoverPoint.currency)}</strong>
              <span>{formatDateTime(hoverPoint.capturedAt)}</span>
              {hoverPoint.departureTime ? <span>{t("watchlist.history.departureAt", { value: hoverPoint.departureTime })}</span> : null}
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
          <details className="history-disclaimer">
            <summary>{t("watchlist.history.priceMeaningTitle")}</summary>
            <p>{t("watchlist.history.priceMeaningBody")}</p>
          </details>
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
                              {formatCurrency(event.min, calendarCurrency)}-{formatCurrency(event.max, calendarCurrency)}
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
                  <span>{t("watchlist.history.cheapest")}</span>
                  <div className="history-heat-bar" />
                  <span>{t("watchlist.history.mostExpensive")}</span>
                  <div className="history-heat-scale">
                    <span className="history-heat-scale-item">
                      <strong>{t("watchlist.history.legendLow")}</strong>
                      <span className="tabular-nums">{formatCurrency(calendarRange.min, calendarCurrency)}</span>
                    </span>
                    {calendarMidpoint != null ? (
                      <span className="history-heat-scale-item">
                        <strong>{t("watchlist.history.legendMid")}</strong>
                        <span className="tabular-nums">{formatCurrency(calendarMidpoint, calendarCurrency)}</span>
                      </span>
                    ) : null}
                    <span className="history-heat-scale-item">
                      <strong>{t("watchlist.history.legendHigh")}</strong>
                      <span className="tabular-nums">{formatCurrency(calendarRange.max, calendarCurrency)}</span>
                    </span>
                  </div>
                  <p className="muted history-heat-explainer">{t("watchlist.history.heatLegendExplainer")}</p>
                </div>
              ) : null}
            </>
          ) : (
            <div className="history-compact-note history-compact-note--calendar">
              <strong>{t("watchlist.history.calendarUnavailableTitle")}</strong>
              <p>{t("watchlist.history.calendarUnavailableBody")}</p>
            </div>
          )}
          <p className="history-microcopy muted">{t("watchlist.history.trendMicrocopy")}</p>
          <details className="history-disclaimer">
            <summary>{t("watchlist.history.priceMeaningTitle")}</summary>
            <p>{t("watchlist.history.priceMeaningBody")}</p>
          </details>
        </div>
      ) : null}
    </section>
  );
}


