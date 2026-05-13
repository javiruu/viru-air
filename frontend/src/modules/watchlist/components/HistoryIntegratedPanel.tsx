import type { CSSProperties, MouseEvent as ReactMouseEvent } from "react";

import { formatCurrency } from "@/modules/shared/format";
import { formatDateTime } from "@/modules/watchlist/presentation";

type ViewMode = "chart" | "calendar";
type RangeWindow = "all" | "7" | "14" | "30" | "90";

type SelectedWatch = {
  origin_iata: string;
  destination_iata: string;
  travel_date_local: string;
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

type Summary = {
  avg: number;
  min: number;
  max: number;
  total: number;
  currency: string;
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
  isRefreshingFiltered: boolean;
  selectedOrigin: string;
  selectedDestination: string;
  selectedDates: string[];
  selectedPoint: string;
  allOrigins: string[];
  allDestinations: string[];
  allTravelDates: string[];
  pointOptions: PointOption[];
  rangeWindow: RangeWindow;
  chartIsCompact: boolean;
  chartHeight: number;
  chartModel: ChartSerie[] | null;
  selectedPointData: SelectedPointData;
  hoverPoint: HoverPoint;
  summary: Summary;
  visibleMonth: string;
  monthTitle: string;
  monthCells: Array<string | null>;
  calendarEvents: Record<string, CalendarEvent>;
  calendarRange: CalendarRange;
  calendarCurrency: string;
  chartWidth: number;
  chartPad: { left: number; right: number; top: number; bottom: number };
  onToggleViewMode: () => void;
  onApplyFilters: () => void;
  onOriginChange: (value: string) => void;
  onDestinationChange: (value: string) => void;
  onDatesChange: (values: string[]) => void;
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
  isRefreshingFiltered,
  selectedOrigin,
  selectedDestination,
  selectedDates,
  selectedPoint,
  allOrigins,
  allDestinations,
  allTravelDates,
  pointOptions,
  rangeWindow,
  chartIsCompact,
  chartHeight,
  chartModel,
  selectedPointData,
  hoverPoint,
  summary,
  visibleMonth,
  monthTitle,
  monthCells,
  calendarEvents,
  calendarRange,
  calendarCurrency,
  chartWidth,
  chartPad,
  onToggleViewMode,
  onApplyFilters,
  onOriginChange,
  onDestinationChange,
  onDatesChange,
  onPointChange,
  onRangeChange,
  onToggleRangeWindow,
  onResetZoom,
  onChartMouseMove,
  onChartMouseLeave,
  onPrevMonth,
  onNextMonth,
}: HistoryIntegratedPanelProps) {
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
            Histórico integrado
          </h2>
          <p className="muted">
            {selectedWatch
              ? `Analizando ${selectedWatch.origin_iata} → ${selectedWatch.destination_iata} (${selectedWatch.travel_date_local})`
              : "Selecciona un vuelo para enfocar el análisis."}
          </p>
        </div>
      </div>

      <div className="history-filterbar">
        <div className="history-filterbar-header">
          <div className="history-filterbar-title">
            <strong>Filtros</strong>
            <span className="muted">Ajusta origen, destino, fechas y punto para ver detalle.</span>
          </div>
          <div className="history-filterbar-actions">
            <button className="btn-secondary btn-layered" onClick={onToggleViewMode}>
              {viewMode === "chart" ? "Ver calendario" : "Ver gráfico"}
            </button>
            <button className="btn-primary btn-layered" type="button" disabled={isRefreshingFiltered} onClick={onApplyFilters}>
              {isRefreshingFiltered ? "Actualizando..." : "Aplicar filtros"}
            </button>
          </div>
        </div>

        <div className="history-filters">
          <div className="history-route-group" aria-label="Filtros de ruta">
            <label className="history-filter history-origin">
              <span className="history-label">
                <span className="history-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                    <path
                      d="M3 11l18-6-6 18-2.2-7.2L3 11z"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.6"
                      strokeLinejoin="round"
                      strokeLinecap="round"
                    />
                    <path
                      d="M11 13l7-7"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.6"
                      strokeLinecap="round"
                    />
                  </svg>
                </span>
                Origen
              </span>
              <select className="history-input" name="history_origin" autoComplete="off" value={selectedOrigin} onChange={(e) => onOriginChange(e.target.value)}>
                <option value="">-- origen --</option>
                {allOrigins.map((origin) => <option key={origin} value={origin}>{origin}</option>)}
              </select>
            </label>

            <label className="history-filter history-destination">
              <span className="history-label">
                <span className="history-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                    <path
                      d="M12 21s7-7.4 7-12a7 7 0 1 0-14 0c0 4.6 7 12 7 12z"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.6"
                      strokeLinejoin="round"
                    />
                    <circle cx="12" cy="9" r="2.6" fill="none" stroke="currentColor" strokeWidth="1.6" />
                  </svg>
                </span>
                Destino
              </span>
              <select
                className="history-input"
                name="history_destination"
                autoComplete="off"
                value={selectedDestination}
                onChange={(e) => onDestinationChange(e.target.value)}
                disabled={!selectedOrigin}
              >
                <option value="">-- destino --</option>
                {allDestinations.map((destination) => <option key={destination} value={destination}>{destination}</option>)}
              </select>
            </label>
          </div>

          <div className="history-temporal-group" aria-label="Filtros temporales">
            <label className="history-filter history-date">
              <span className="history-label">
                <span className="history-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                    <rect x="3" y="4" width="18" height="17" rx="3" fill="none" stroke="currentColor" strokeWidth="1.6" />
                    <path
                      d="M8 2v4M16 2v4M3 9h18"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.6"
                      strokeLinecap="round"
                    />
                  </svg>
                </span>
                Fechas de vuelo
              </span>
              <select
                multiple
                name="history_dates"
                autoComplete="off"
                value={selectedDates}
                disabled={!selectedOrigin || !selectedDestination}
                onChange={(e) => {
                  const values = Array.from(e.target.selectedOptions).map((option) => option.value);
                  onDatesChange(values);
                }}
                className="history-input history-scroll history-multi"
              >
                {allTravelDates.map((travelDate) => <option key={travelDate} value={travelDate}>{travelDate}</option>)}
              </select>
            </label>

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
                Punto (fecha de consulta)
              </span>
              <select
                className="history-input"
                name="history_point"
                autoComplete="off"
                value={selectedPoint}
                disabled={selectedDates.length !== 1 || pointOptions.length === 0}
                onChange={(e) => onPointChange(e.target.value)}
              >
                <option value="">Selecciona un punto para ver detalle</option>
                {pointOptions.map((point) => <option key={point.value} value={point.value}>{point.label}</option>)}
              </select>
              <span className="history-helper">
                {selectedDates.length !== 1
                  ? "Selecciona una sola fecha para habilitar."
                  : pointOptions.length === 0
                    ? "No hay puntos para la fecha seleccionada."
                    : "Selecciona un punto para activar el detalle."}
              </span>
            </label>
          </div>
        </div>
      </div>

      <div className="history-range history-range-toolbar">
        <div className="history-range-left">
          <strong>Rango</strong>
          <p className="muted">Ajusta el rango temporal del gráfico.</p>
        </div>
        <div className="history-range-control">
          <label className="history-range-field">
            <span className="history-range-label">Rango</span>
            <select
              className="history-input"
              name="history_range"
              autoComplete="off"
              value={rangeWindow}
              onChange={(e) => onRangeChange(e.target.value as RangeWindow)}
            >
              <option value="7">Últimos 7 días</option>
              <option value="14">Últimos 14 días</option>
              <option value="30">Últimos 30 días</option>
              <option value="90">Últimos 90 días</option>
              <option value="all">Todo el histórico</option>
            </select>
          </label>
          <div className="history-range-actions">
            <button
              className={`btn-ghost btn-layered ${rangeWindow === "all" ? "" : "is-active"}`}
              type="button"
              aria-pressed={rangeWindow !== "all"}
              onClick={onToggleRangeWindow}
            >
              Vista acotada
            </button>
            <button className="btn-ghost btn-layered" type="button" onClick={onResetZoom}>
              Reset zoom
            </button>
          </div>
        </div>
      </div>

      {viewMode === "chart" ? (
        <div
          key={`chart-${selectedOrigin}-${selectedDestination}-${selectedDates.join(",")}-${selectedPoint}`}
          className={`panel history-stage history-chart history-scroll history-chart-panel${chartIsCompact ? " history-chart--compact" : ""}`}
        >
          <div className="history-detail">
            {selectedPointData ? (
              <div className="history-detail-card">
                <div>
                  <span className="history-detail-label">Punto seleccionado</span>
                  <strong>{formatCurrency(selectedPointData.price, selectedPointData.currency)}</strong>
                </div>
                <div className="history-detail-meta">
                  <span>{formatDateTime(selectedPointData.capturedAt)}</span>
                  <span>{selectedPointData.date}</span>
                  {selectedPointData.departureTime ? <span>Salida {selectedPointData.departureTime}</span> : null}
                </div>
              </div>
            ) : (
              <div className="history-detail-empty">
                Selecciona un punto para ver detalle.
              </div>
            )}
          </div>
          {chartModel && chartModel.length > 0 ? (
            <svg
              className="history-svg"
              viewBox={`0 0 ${chartWidth} ${chartHeight}`}
              width="100%"
              role="img"
              aria-label="Gráfico de histórico de precios"
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
              {chartModel.map((serie) => (
                <g key={serie.date}>
                  <polyline fill="none" stroke={serie.color} strokeWidth="2.4" points={serie.path} />
                  {serie.points.map((point) => (
                    <circle
                      key={`${serie.date}-${point.capturedAt}`}
                      cx={point.x}
                      cy={point.y}
                      r={selectedPoint === point.capturedAt ? 6.2 : 4}
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
              <p>Selecciona filtros con datos históricos para ver el gráfico.</p>
            </div>
          )}
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
              {hoverPoint.departureTime ? <span>Salida {hoverPoint.departureTime}</span> : null}
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
          {summary ? (
            <div className="history-summary history-summary--kpis">
              <div className="history-kpi">
                <span>Media</span>
                <strong>{formatCurrency(summary.avg, summary.currency)}</strong>
              </div>
              <div className="history-kpi">
                <span>Mínimo</span>
                <strong>{formatCurrency(summary.min, summary.currency)}</strong>
              </div>
              <div className="history-kpi">
                <span>Máximo</span>
                <strong>{formatCurrency(summary.max, summary.currency)}</strong>
              </div>
              <div className="history-kpi">
                <span>N puntos</span>
                <strong>{summary.total}</strong>
              </div>
            </div>
          ) : null}
          <details className="history-disclaimer">
            <summary>¿Qué significa este precio?</summary>
            <p>Precio orientativo: base 1 adulto, sin extras de equipaje ni servicios.</p>
          </details>
        </div>
      ) : (
        <div key={`calendar-${visibleMonth}`} className="panel history-stage history-calendar history-calendar-panel">
          {visibleMonth ? (
            <>
              <div className="history-calendar-nav">
                <button className="btn-ghost" onClick={onPrevMonth}>Mes anterior</button>
                <strong className="month-title">{monthTitle}</strong>
                <button className="btn-ghost" onClick={onNextMonth}>Mes siguiente</button>
              </div>
              <div className="history-calendar-grid">
                {["L", "M", "X", "J", "V", "S", "D"].map((weekday, index) => (
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
                              {event.count} puntos
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
                  <span>Más barato</span>
                  <div className="history-heat-bar" />
                  <span>Más caro</span>
                  <span className="muted">
                    {formatCurrency(calendarRange.min, calendarCurrency)} - {formatCurrency(calendarRange.max, calendarCurrency)}
                  </span>
                </div>
              ) : null}
            </>
          ) : (
            <div className="history-ghost history-ghost--calendar">
              <div className="history-ghost-line" />
              <p>No hay datos para calendario.</p>
            </div>
          )}
          <details className="history-disclaimer">
            <summary>¿Qué significa este precio?</summary>
            <p>Precio orientativo: base 1 adulto, sin extras de equipaje ni servicios.</p>
          </details>
        </div>
      )}
    </section>
  );
}
