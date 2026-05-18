import { useMemo, useState } from "react";

import { useI18n } from "@/i18n";
import { formatCurrency, formatSignedCurrency } from "@/modules/shared/format";
import { getWatchStatusMeta } from "@/modules/shared/statusCatalog";
import { monthLabel } from "@/modules/watchlist/dateUtils";
import { safeDateTime } from "@/modules/watchlist/presentation";
import { getFreshnessPresentation } from "@/modules/watchlist/summary";
import type { CalendarSelectorFlight } from "@/modules/watchlist/types";

type ListSort = "freshness" | "price_asc" | "price_desc" | "delta";

type WatchItem = {
  id: string;
  origin_iata: string;
  destination_iata: string;
  travel_date_local: string;
  target_price?: number | null;
  status: string;
};

type WatchMetaEntry = {
  latest: {
    capturedAt: string;
    price: number;
    currency: string;
  } | null;
  previous: {
    price: number;
    currency: string;
  } | null;
  min: number | null;
  max: number | null;
};

type SmartWatchListPanelProps = {
  items: WatchItem[];
  smartListItems: WatchItem[];
  watchMeta: Map<string, WatchMetaEntry>;
  lastUpdatedGlobal: string;
  watchSearch: string;
  watchSort: ListSort;
  hasSearchFilter: boolean;
  selectedWatchId: string;
  refreshingWatchId: string | null;
  onSearchChange: (value: string) => void;
  onSortChange: (value: ListSort) => void;
  onClearSearch: () => void;
  onSelectWatch: (watch: WatchItem) => void;
  onRefreshWatch: (watchId: string) => void;
  onPauseWatch: (watchId: string) => void;
  onResumeWatch: (watchId: string) => void;
  onDeleteWatch: (watchId: string) => void;
  onBulkPause: (watchIds: string[]) => void;
  onBulkResume: (watchIds: string[]) => void;
  onBulkDelete: (watchIds: string[]) => void;
  onBulkRefresh: (watchIds: string[]) => void;
  isRefreshingBulk: boolean;
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
  watchSearch,
  watchSort,
  hasSearchFilter,
  selectedWatchId,
  refreshingWatchId,
  onSearchChange,
  onSortChange,
  onClearSearch,
  onSelectWatch,
  onRefreshWatch,
  onPauseWatch,
  onResumeWatch,
  onDeleteWatch,
  onBulkPause,
  onBulkResume,
  onBulkDelete,
  onBulkRefresh,
  isRefreshingBulk,
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
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const hasSelection = selectedIds.length > 0;
  const selectionCount = selectedIds.length;
  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);
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
  const activeCount = useMemo(() => items.filter((item) => item.status !== "paused").length, [items]);
  const pausedCount = useMemo(() => items.filter((item) => item.status === "paused").length, [items]);
  const showListMode = !isCalendarSelectorOpen;

  return (
    <section className="panel panel-soft section-gap">
      <div className="panel-header">
        <div className="watch-smart-header-copy">
          <h2 className="panel-title">{t("watchlist.smartList.heading")}</h2>
          <div className="watch-smart-counts muted" role="status" aria-live="polite">
            <span className="watch-smart-count-pill">{t("watchlist.smartList.activeCount", { count: activeCount })}</span>
            <span className="watch-smart-count-pill">{t("watchlist.smartList.pausedCount", { count: pausedCount })}</span>
            <span className="watch-smart-count-pill">{t("watchlist.smartList.totalCount", { count: items.length })}</span>
            {lastUpdatedGlobal ? <span>{t("watchlist.lastUpdateInline", { value: lastUpdatedGlobal })}</span> : null}
          </div>
          {items.length > 0 ? (
            <span className="watch-smart-meta">
              {t("watchlist.smartList.showingCount", { shown: smartListItems.length, total: items.length })}
            </span>
          ) : null}
        </div>
        <div className="watch-smart-tools">
          <label className="watch-smart-search" htmlFor="watch-smart-search">
            {t("watchlist.smartList.search")}
            <input
              id="watch-smart-search"
              name="watch_smart_search"
              autoComplete="off"
              value={watchSearch}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder={t("watchlist.smartList.searchPlaceholder")}
            />
          </label>
          <label className="watch-smart-sort" htmlFor="watch-smart-sort">
            {t("watchlist.smartList.sort")}
            <select
              id="watch-smart-sort"
              name="watch_smart_sort"
              autoComplete="off"
              value={watchSort}
              onChange={(event) => onSortChange(event.target.value as ListSort)}
            >
              <option value="freshness">{t("watchlist.smartList.sortFreshness")}</option>
              <option value="price_asc">{t("watchlist.smartList.sortPriceAsc")}</option>
              <option value="price_desc">{t("watchlist.smartList.sortPriceDesc")}</option>
              <option value="delta">{t("watchlist.smartList.sortDelta")}</option>
            </select>
          </label>
          <button
            type="button"
            className="btn-ghost btn-compact watch-smart-reset"
            onClick={onClearSearch}
            disabled={!hasSearchFilter}
          >
            {t("watchlist.smartList.clearSearch")}
          </button>
          {hasSelection ? (
            <div className="alert-actions watch-bulk-toolbar" role="toolbar" aria-label={t("watchlist.bulk.toolbarAriaLabel")} data-testid="watchlist-bulk-toolbar">
              <span className="watch-smart-meta">{t("watchlist.bulk.selectedCount", { count: selectionCount })}</span>
              <button type="button" className="btn-secondary btn-compact" onClick={() => onBulkRefresh(selectedIds)} disabled={isRefreshingBulk}>
                {isRefreshingBulk ? t("watchlist.bulk.refreshing") : t("watchlist.bulk.refreshSelected")}
              </button>
              <button type="button" className="btn-ghost btn-compact" onClick={() => onBulkPause(selectedIds)}>{t("watchlist.bulk.pause")}</button>
              <button type="button" className="btn-ghost btn-compact" onClick={() => onBulkResume(selectedIds)}>{t("watchlist.bulk.resume")}</button>
              <button type="button" className="btn-ghost btn-compact" onClick={() => onBulkDelete(selectedIds)}>{t("watchlist.bulk.delete")}</button>
            </div>
          ) : null}
          <button
            type="button"
            className={`btn-secondary btn-layered ${isCalendarSelectorOpen ? "is-active" : ""}`}
            onClick={onToggleCalendarSelector}
            aria-expanded={isCalendarSelectorOpen}
            aria-controls="watchlist-calendar-selector"
            disabled={calendarSelectorFlightsByDay.size === 0}
          >
            {t("watchlist.history.viewCalendar")}
          </button>
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
          <p>{t("watchlist.smartList.searchEmpty")}</p>
          <button type="button" className="btn-ghost btn-compact" onClick={onClearSearch}>
            {t("watchlist.smartList.searchEmptyCta")}
          </button>
        </div>
      ) : null}
      {showListMode
        ? smartListItems.map((watch) => {
        const watchStatus = getWatchStatusMeta(watch.status, t);
        const meta = watchMeta.get(watch.id);
        const trend = !meta?.latest || !meta?.previous
          ? "flat"
          : meta.latest.price > meta.previous.price
            ? "up"
            : meta.latest.price < meta.previous.price
              ? "down"
              : "flat";
        const deltaLabel = !meta?.latest || !meta?.previous
          ? t("watchlist.smartList.noTrend")
          : formatSignedCurrency(meta.latest.price - meta.previous.price, meta.latest.currency, localeTag);
        const routeHealthLabel = trend === "up" ? t("watchlist.smartList.trendUp") : trend === "down" ? t("watchlist.smartList.trendDown") : t("watchlist.smartList.trendStable");

        const freshness = getFreshnessPresentation({
          t,
          locale: localeTag,
          lastUpdatedAt: meta?.latest?.capturedAt,
          freshnessState: meta?.latest ? "observing" : null,
        });
        const priceDropAmount = trend === "down" && meta?.latest && meta?.previous
          ? meta.previous.price - meta.latest.price
          : null;
        const priceDropPercent =
          priceDropAmount != null && meta?.previous && meta.previous.price > 0
            ? Math.round((priceDropAmount / meta.previous.price) * 100)
            : null;
        const hasMeaningfulDrop = priceDropAmount != null && priceDropPercent != null && priceDropPercent > 0;
        const isBestPrice =
          meta?.latest && meta?.min != null && meta.latest.price <= meta.min && meta?.max != null && meta.max > meta.min;

        return (
          <article
            key={watch.id}
            className={`list-row watch-row ${selectedWatchId === watch.id ? "watch-selected" : ""}`}
            onClick={() => onSelectWatch(watch)}
            role="button"
            tabIndex={0}
            aria-pressed={selectedWatchId === watch.id}
            aria-label={t("watchlist.smartList.selectRowAria", {
              origin: watch.origin_iata,
              destination: watch.destination_iata,
              date: watch.travel_date_local,
            })}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onSelectWatch(watch);
              }
            }}
          >
            <div className="watch-details">
              <div className="watch-route">
                <input
                  type="checkbox"
                  className="watch-bulk-checkbox"
                  checked={selectedSet.has(watch.id)}
                  onChange={(event) => {
                    event.stopPropagation();
                    setSelectedIds((prev) =>
                      event.target.checked ? Array.from(new Set([...prev, watch.id])) : prev.filter((id) => id !== watch.id),
                    );
                  }}
                  aria-label={t("watchlist.smartList.selectCheckboxAria", {
                    origin: watch.origin_iata,
                    destination: watch.destination_iata,
                  })}
                />
                <strong>{watch.origin_iata}{" → "}{watch.destination_iata}</strong>
                <span className="watch-date">{watch.travel_date_local}</span>
                <span className={`status-pill ${watchStatus.tone}`}>{watchStatus.label}</span>
                <strong className="watch-inline-price">
                  {meta?.latest ? formatCurrency(meta.latest.price, meta.latest.currency, localeTag) : "--"}
                </strong>
              </div>
              <div className="watch-meta">
                <span className={`status-pill ${trend === "up" ? "error" : trend === "down" ? "success" : "warning"}`}>
                  {routeHealthLabel}
                </span>
                <span className="watch-meta-chip">{t("watchlist.detail.latestSnapshot")} {safeDateTime(meta?.latest?.capturedAt, localeTag)}</span>
                <span className="watch-meta-chip watch-meta-chip--freshness">{t("watchlist.detail.freshness")} {freshness.fullText}</span>
                <span className="watch-note">{t("watchlist.smartList.priceDisclaimer")}</span>
              </div>
            </div>
            <div className="watch-price-area">
              <div className="watch-price">
                <span className="watch-price-caption">{t("watchlist.smartList.currentPrice")}</span>
                <span className={`trend-chip trend-${trend}`}>
                  <span className="trend-icon" aria-hidden="true">
                    <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                      <path
                        d="M6 15l6-6 6 6"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </span>
                  {deltaLabel}
                </span>
              </div>
              {hasMeaningfulDrop || isBestPrice ? (
                <div className="watch-price-badges">
                  {hasMeaningfulDrop ? (
                    <span className="price-drop-badge">
                      <svg viewBox="0 0 16 16" className="price-drop-icon" aria-hidden="true">
                        <path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                      {formatCurrency(priceDropAmount!, meta?.latest?.currency ?? "EUR", localeTag)} ({priceDropPercent}%)
                    </span>
                  ) : null}
                  {isBestPrice ? (
                    <span className="best-price-badge">{t("watchlist.compare.bestPriceBadge")}</span>
                  ) : null}
                </div>
              ) : null}
              <div className="watch-row-actions">
                <button
                  className="btn-secondary"
                  type="button"
                  disabled={refreshingWatchId === watch.id}
                  aria-busy={refreshingWatchId === watch.id}
                  onClick={(event) => {
                    event.stopPropagation();
                    onRefreshWatch(watch.id);
                  }}
                >
                  {refreshingWatchId === watch.id ? t("watchlist.smartList.updating") : t("watchlist.smartList.refresh")}
                </button>
                <div className="alert-actions">
                  {watch.status === "paused" ? (
                    <button className="btn-ghost btn-compact" type="button" onClick={(e) => { e.stopPropagation(); onResumeWatch(watch.id); }}>
                      {t("watchlist.smartList.resume")}
                    </button>
                  ) : (
                    <button className="btn-ghost btn-compact" type="button" onClick={(e) => { e.stopPropagation(); onPauseWatch(watch.id); }}>
                      {t("watchlist.smartList.pause")}
                    </button>
                  )}
                  <button className="btn-danger btn-compact" type="button" onClick={(e) => { e.stopPropagation(); onDeleteWatch(watch.id); }}>
                    {t("watchlist.smartList.delete")}
                  </button>
                </div>
              </div>
            </div>
          </article>
        );
          })
        : null}
    </section>
  );
}





