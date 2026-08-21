import { useMemo, useState } from "react";

import { useI18n } from "@/i18n";
import { communityRouteKey } from "@/modules/community-routes/communityRoutesApi";
import { useCommunityRouteInsights } from "@/modules/community-routes/useCommunityRouteInsights";
import { formatCurrency } from "@/modules/shared/format";
import { getAirportMeta } from "@/modules/shared/airports";
import {
  WatchRow,
  type WatchMetaEntry,
} from "@/modules/watchlist/components/WatchRow";
import { monthLabel } from "@/modules/watchlist/dateUtils";
import { safeDateTime } from "@/modules/watchlist/presentation";
import type { CalendarSelectorFlight, Watch } from "@/modules/watchlist/types";

type ListSort = "freshness" | "price_asc" | "price_desc" | "delta";
const WATCHLIST_PAGE_SIZE = 3;

function getPageNumbers(current: number, total: number) {
  const pages: (number | string)[] = [];
  if (total <= 7) {
    for (let i = 1; i <= total; i++) pages.push(i);
  } else {
    pages.push(1);
    if (current > 3) pages.push("...");
    const start = Math.max(2, current - 1);
    const end = Math.min(total - 1, current + 1);
    for (let i = start; i <= end; i++) pages.push(i);
    if (current < total - 2) pages.push("...");
    pages.push(total);
  }
  return pages;
}

type SmartWatchListPanelProps = {
  items: Watch[];
  smartListItems: Watch[];
  watchMeta: Map<string, WatchMetaEntry>;
  lastUpdatedGlobal: string;
  watchRouteOrigin: string;
  watchRouteDestination: string;
  watchRouteOrigins: string[];
  watchRouteDestinations: string[];
  watchSort: ListSort;
  hasRouteFilter: boolean;
  selectedWatchId: string;
  onRouteOriginChange: (value: string) => void;
  onRouteDestinationChange: (value: string) => void;
  onSortChange: (value: ListSort) => void;
  onClearRouteFilters: () => void;
  onSelectWatch: (watch: Watch) => void;
  onCommunityAction: (watch: Watch, trigger: HTMLButtonElement) => void;
  onPauseWatch: (watchId: string) => void;
  onResumeWatch: (watchId: string) => void;
  onDeleteWatch: (watchId: string) => void;
  isLoading: boolean;
  listErrorMessage: string;
  onRetryLoad: () => void;
  onOpenAddWatch: () => void;
  isCalendarSelectorOpen: boolean;
  calendarSelectorDay: string;
  calendarSelectorMonth: string;
  calendarSelectorMonthCells: string[];
  calendarSelectorEvents: Record<string, { min: number; max: number; count: number }>;
  calendarSelectorFlightsByDay: Map<string, CalendarSelectorFlight[]>;
  onToggleCalendarSelector: () => void;
  onCloseCalendarSelector: () => void;
  onCalendarSelectorDayChange: (day: string) => void;
  onSelectWatchById: (watchId: string) => void;
  onCalendarPrevMonth: () => void;
  onCalendarNextMonth: () => void;
};

export function SmartWatchListPanel({
  items,
  smartListItems,
  watchMeta,
  lastUpdatedGlobal,
  watchRouteOrigin,
  watchRouteDestination,
  watchRouteOrigins,
  watchRouteDestinations,
  watchSort,
  hasRouteFilter,
  selectedWatchId,
  onRouteOriginChange,
  onRouteDestinationChange,
  onSortChange,
  onClearRouteFilters,
  onSelectWatch,
  onCommunityAction,
  onPauseWatch,
  onResumeWatch,
  onDeleteWatch,
  isLoading,
  listErrorMessage,
  onRetryLoad,
  onOpenAddWatch,
  isCalendarSelectorOpen,
  calendarSelectorDay,
  calendarSelectorMonth,
  calendarSelectorMonthCells,
  calendarSelectorEvents,
  calendarSelectorFlightsByDay,
  onToggleCalendarSelector,
  onCloseCalendarSelector,
  onCalendarSelectorDayChange,
  onSelectWatchById,
  onCalendarPrevMonth,
  onCalendarNextMonth,
}: SmartWatchListPanelProps) {
  const { t, localeTag } = useI18n();
  const [currentPage, setCurrentPage] = useState(1);
  const communityInsights = useCommunityRouteInsights(
    items.map((item) => ({
      origin_iata: item.origin_iata,
      destination_iata: item.destination_iata,
    })),
  );
  const calendarWeekdays = useMemo(
    () =>
      t("watchlist.history.weekdays")
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean),
    [t],
  );
  const calendarDayFlights = useMemo(
    () => (calendarSelectorDay ? calendarSelectorFlightsByDay.get(calendarSelectorDay) ?? [] : []),
    [calendarSelectorDay, calendarSelectorFlightsByDay],
  );
  const activeCount = useMemo(() => items.filter((item) => item.status === "active").length, [items]);
  const pausedCount = useMemo(() => items.filter((item) => item.status === "paused").length, [items]);
  const showListMode = !isCalendarSelectorOpen;
  const totalPages = Math.max(1, Math.ceil(smartListItems.length / WATCHLIST_PAGE_SIZE));
  const boundedPage = Math.min(currentPage, totalPages);
  const pagedListItems = useMemo(() => {
    const start = (boundedPage - 1) * WATCHLIST_PAGE_SIZE;
    return smartListItems.slice(start, start + WATCHLIST_PAGE_SIZE);
  }, [boundedPage, smartListItems]);
  const shownStart = smartListItems.length === 0 ? 0 : (boundedPage - 1) * WATCHLIST_PAGE_SIZE + 1;
  const shownEnd = Math.min(boundedPage * WATCHLIST_PAGE_SIZE, smartListItems.length);
  const goToPage = (page: number) => {
    const next = Math.max(1, Math.min(page, totalPages));
    setCurrentPage(next);
  };
  const airportLabel = (iata: string) => {
    const airport = getAirportMeta(iata);
    return airport ? `${iata} · ${airport.city}` : iata;
  };

  return (
    <section className="panel panel-soft section-gap watch-smart-panel">
      <div className="panel-header watch-smart-panel-header">
        <div className="watch-smart-header-copy">
          <h2 className="panel-title">{t("watchlist.smartList.heading")}</h2>
          <div className="watch-smart-counts muted" role="status" aria-live="polite">
            <span className="watch-smart-count-pill tabular-nums">{t("watchlist.smartList.activeCount", { count: activeCount })}</span>
            <span className="watch-smart-count-pill tabular-nums">{t("watchlist.smartList.pausedCount", { count: pausedCount })}</span>
            <span className="watch-smart-count-pill tabular-nums">{t("watchlist.smartList.totalCount", { count: items.length })}</span>
            {lastUpdatedGlobal ? <span className="tabular-nums">{t("watchlist.lastUpdateInline", { value: lastUpdatedGlobal })}</span> : null}
          </div>
          {items.length > 0 ? (
            <span className="watch-smart-meta tabular-nums">
              {t("watchlist.smartList.showingCount", { shown: smartListItems.length, total: items.length })}
            </span>
          ) : null}
        </div>
        <div className="watch-smart-tools" aria-label={t("watchlist.smartList.routeToolsAria")}>
          <div className="watch-smart-tool-group watch-smart-tool-group--route-tools">
            <div className="watch-smart-route-picker">
              <label className="watch-smart-route-field" data-side="origin" htmlFor="watch-smart-route-origin">
                <span>{t("watchlist.smartList.origin")}</span>
                <select
                  id="watch-smart-route-origin"
                  name="watch_smart_route_origin"
                  value={watchRouteOrigin}
                  onChange={(event) => {
                    setCurrentPage(1);
                    onRouteOriginChange(event.target.value);
                  }}
                >
                  <option value="">{t("watchlist.smartList.allOrigins")}</option>
                  {watchRouteOrigins.map((origin) => <option key={origin} value={origin}>{airportLabel(origin)}</option>)}
                </select>
              </label>
              <span className="watch-smart-route-arrow" aria-hidden="true">→</span>
              <label className="watch-smart-route-field" data-side="destination" htmlFor="watch-smart-route-destination">
                <span>{t("watchlist.smartList.destination")}</span>
                <select
                  id="watch-smart-route-destination"
                  name="watch_smart_route_destination"
                  value={watchRouteDestination}
                  onChange={(event) => {
                    setCurrentPage(1);
                    onRouteDestinationChange(event.target.value);
                  }}
                >
                  <option value="">{t("watchlist.smartList.allDestinations")}</option>
                  {watchRouteDestinations.map((destination) => <option key={destination} value={destination}>{airportLabel(destination)}</option>)}
                </select>
              </label>
            </div>
            <span className="watch-smart-tools-divider" aria-hidden="true" />
            <label className="watch-smart-sort" htmlFor="watch-smart-sort">
              <span>{t("watchlist.smartList.sort")}</span>
              <select
                id="watch-smart-sort"
                name="watch_smart_sort"
                autoComplete="off"
                value={watchSort}
                onChange={(event) => {
                  setCurrentPage(1);
                  onSortChange(event.target.value as ListSort);
                }}
              >
                <option value="freshness">{t("watchlist.smartList.sortFreshness")}</option>
                <option value="price_asc">{t("watchlist.smartList.sortPriceAsc")}</option>
                <option value="price_desc">{t("watchlist.smartList.sortPriceDesc")}</option>
                <option value="delta">{t("watchlist.smartList.sortDelta")}</option>
              </select>
            </label>
            <button
              type="button"
              className={`btn-ghost btn-compact watch-smart-calendar-toggle ${isCalendarSelectorOpen ? "is-active" : ""}`}
              onClick={onToggleCalendarSelector}
              aria-expanded={isCalendarSelectorOpen}
              aria-controls="watchlist-calendar-selector"
              disabled={calendarSelectorFlightsByDay.size === 0}
            >
              {t("watchlist.history.viewCalendar")}
            </button>
            {hasRouteFilter ? (
              <button
                type="button"
                className="btn-ghost btn-compact watch-smart-reset"
                onClick={() => {
                  setCurrentPage(1);
                  onClearRouteFilters();
                }}
              >
                {t("watchlist.smartList.clearRouteFilters")}
              </button>
            ) : null}
          </div>
        </div>
      </div>
      {isCalendarSelectorOpen ? (
        <div className="history-calendar-panel section-gap-sm" id="watchlist-calendar-selector">
          <div className="history-calendar-nav">
            <button className="btn-ghost btn-compact" type="button" onClick={onCalendarPrevMonth}>
              {t("watchlist.history.prevMonth")}
            </button>
            <strong className="month-title">{monthLabel(calendarSelectorMonth, localeTag)}</strong>
            <button className="btn-ghost btn-compact" type="button" onClick={onCalendarNextMonth}>
              {t("watchlist.history.nextMonth")}
            </button>
          </div>
          <div className="history-calendar-grid history-primary">
            {(calendarWeekdays.length === 7 ? calendarWeekdays : ["L", "M", "X", "J", "V", "S", "D"]).map((weekday, index) => (
              <div key={`watchlist-selector-weekday-${index}`} className="history-weekday">{weekday}</div>
            ))}
            {calendarSelectorMonthCells.map((day, idx) => {
              const event = day ? calendarSelectorEvents[day] : undefined;
              const isSelectedDay = day === calendarSelectorDay;
              const dayFlights = day ? calendarSelectorFlightsByDay.get(day) ?? [] : [];
              const firstDayFlight = dayFlights[0];
              const dayTitle = !day || !event
                ? undefined
                : firstDayFlight
                  ? `${firstDayFlight.origin} -> ${firstDayFlight.destination} · ${firstDayFlight.travelDate}${dayFlights.length > 1 ? ` · +${dayFlights.length - 1}` : ""}`
                  : t("watchlist.history.calendarFlightsCount", { count: event.count });
              return (
                <button
                  key={`${day || "empty"}-${idx}`}
                  type="button"
                  className={`history-day ${day ? "has-day" : "empty"} ${event ? "has-event" : ""} ${isSelectedDay ? "is-selected" : ""}`}
                  disabled={!day || !event}
                  title={dayTitle}
                  onClick={() => {
                    if (!day || !event) return;
                    const flights = dayFlights;
                    if (flights.length <= 1) {
                      const single = flights[0];
                      if (single) onSelectWatchById(single.watchId);
                      return;
                    }
                    onCalendarSelectorDayChange(day);
                  }}
                >
                  {day ? (
                    <>
                      <div className="history-day-number">{day.slice(-2)}</div>
                      {event ? <div className="history-day-meta">{t("watchlist.history.calendarFlightsCount", { count: event.count })}</div> : null}
                    </>
                  ) : null}
                </button>
              );
            })}
          </div>
          {calendarSelectorDay && calendarDayFlights.length > 1 ? (
            <div className="history-compact-note history-compact-note--calendar" role="dialog" aria-label={t("watchlist.history.dayFlightsTitle", { day: calendarSelectorDay })}>
              <strong>{t("watchlist.history.dayFlightsTitle", { day: calendarSelectorDay })}</strong>
              <div className="watch-bulk-toolbar">
                {calendarDayFlights.map((flight) => (
                  <button key={flight.watchId} type="button" className="btn-ghost btn-compact" onClick={() => onSelectWatchById(flight.watchId)}>
                    {flight.origin}{" -> "}{flight.destination} · {flight.travelDate} · {flight.latestPrice == null ? "--" : formatCurrency(flight.latestPrice, flight.latestCurrency, localeTag)}
                    {flight.latestCapturedAt ? ` (${safeDateTime(flight.latestCapturedAt, localeTag)})` : ""}
                  </button>
                ))}
              </div>
              <button type="button" className="btn-ghost btn-compact" onClick={onCloseCalendarSelector}>
                {t("watchlist.history.closeCalendarSelector")}
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
      {showListMode && isLoading && items.length === 0 ? (
        <div className="watchlist-skeleton-list" role="status" aria-live="polite" aria-label={t("watchlist.smartList.loadingAria")}>
          {[0, 1, 2].map((index) => (
            <article key={index} className="watch-row watch-row-skeleton" aria-hidden="true">
              <div className="watch-details">
                <div className="watch-route">
                  <span className="skeleton skeleton-pill watch-skeleton-checkbox" />
                  <span className="skeleton skeleton-line watch-skeleton-route" />
                  <span className="skeleton skeleton-pill watch-skeleton-date" />
                  <span className="skeleton skeleton-pill watch-skeleton-pill" />
                  <span className="skeleton skeleton-pill watch-skeleton-pill" />
                </div>
                <div className="watch-meta">
                  <span className="skeleton skeleton-pill watch-skeleton-meta" />
                  <span className="skeleton skeleton-pill watch-skeleton-meta" />
                  <span className="skeleton skeleton-line watch-skeleton-note" />
                </div>
              </div>
              <div className="watch-price-area">
                <div className="watch-price">
                  <span className="skeleton skeleton-line watch-skeleton-caption" />
                  <span className="skeleton skeleton-line watch-skeleton-price" />
                  <span className="skeleton skeleton-pill watch-skeleton-delta" />
                </div>
                <span className="skeleton skeleton-block watch-skeleton-spark" />
                <span className="skeleton skeleton-pill watch-skeleton-button" />
              </div>
            </article>
          ))}
        </div>
      ) : null}
      {listErrorMessage ? (
        <div className={`notice notice-compact section-gap-sm ${items.length === 0 ? "notice-error" : "notice-info"}`} role="alert" aria-live="assertive">
          <span>{listErrorMessage}</span>
          <button type="button" className="btn-ghost btn-compact" onClick={onRetryLoad}>
            {t("watchlist.smartList.retryLoad")}
          </button>
        </div>
      ) : null}
      {items.length === 0 && !isLoading ? (
        <div className="empty-guide">
          <p className="panel-note">{t("watchlist.smartList.emptyTitle")}</p>
          <div className="empty-steps">
            <div>
              <strong>{t("watchlist.smartList.emptyStep1Title")}</strong>
              <span>{t("watchlist.smartList.emptyStep1Body")}</span>
            </div>
            <div>
              <strong>{t("watchlist.smartList.emptyStep2Title")}</strong>
              <span>{t("watchlist.smartList.emptyStep2Body")}</span>
            </div>
            <div>
              <strong>{t("watchlist.smartList.emptyStep3Title")}</strong>
              <span>{t("watchlist.smartList.emptyStep3Body")}</span>
            </div>
          </div>
          <button className="btn-primary" type="button" onClick={onOpenAddWatch}>
            {t("watchlist.smartList.emptyCta")}
          </button>
        </div>
      ) : null}
      {showListMode && items.length > 0 && smartListItems.length === 0 ? (
        <div className="watch-empty-search" role="status" aria-live="polite">
          <p>{t("watchlist.smartList.routeFiltersEmpty")}</p>
          <button type="button" className="btn-ghost btn-compact" onClick={onClearRouteFilters}>
            {t("watchlist.smartList.routeFiltersEmptyCta")}
          </button>
        </div>
      ) : null}
      {showListMode
        ? pagedListItems.map((watch) => {
            return (
            <WatchRow
              key={watch.id}
              watch={watch}
              meta={watchMeta.get(watch.id)}
              communityInsight={communityInsights.get(communityRouteKey({
                origin_iata: watch.origin_iata,
                destination_iata: watch.destination_iata,
              }))}
              isSelected={selectedWatchId === watch.id}
              onSelect={onSelectWatch}
              onOpenCommunity={onCommunityAction}
              onPause={onPauseWatch}
              onResume={onResumeWatch}
              onDelete={onDeleteWatch}
            />
          );
          })
        : null}
      {showListMode && smartListItems.length > 0 ? (
        <div className="qs-pagination animate-fade-in" role="navigation" aria-label="Watchlist pagination">
          <div className="qs-pagination-stats">
            {t("watchlist.smartList.showingCount", { shown: shownEnd, total: smartListItems.length })} · {shownStart}-{shownEnd}
          </div>
          <div className="qs-pagination-nav">
            <button
              className="qs-pagination-btn qs-pagination-btn-arrow"
              onClick={() => goToPage(boundedPage - 1)}
              disabled={boundedPage === 1}
              aria-label="Pagina anterior"
            >
              <span className="qs-pagination-arrow">←</span>
              <span className="qs-pagination-btn-text">Anterior</span>
            </button>
            <div className="qs-pagination-pages">
              {getPageNumbers(boundedPage, totalPages).map((num, idx) => {
                if (num === "...") {
                  return (
                    <span key={`watchlist-ellipsis-${idx}`} className="qs-pagination-ellipsis" aria-hidden="true">
                      ...
                    </span>
                  );
                }
                const isSelected = num === boundedPage;
                return (
                  <button
                    key={`watchlist-page-${num}`}
                    className={`qs-pagination-btn ${isSelected ? "active" : ""}`}
                    onClick={() => goToPage(Number(num))}
                    aria-current={isSelected ? "page" : undefined}
                    aria-label={`Ir a la pagina ${num}`}
                  >
                    {num}
                  </button>
                );
              })}
            </div>
            <button
              className="qs-pagination-btn qs-pagination-btn-arrow"
              onClick={() => goToPage(boundedPage + 1)}
              disabled={boundedPage === totalPages}
              aria-label="Pagina siguiente"
            >
              <span className="qs-pagination-btn-text">Siguiente</span>
              <span className="qs-pagination-arrow">→</span>
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}





