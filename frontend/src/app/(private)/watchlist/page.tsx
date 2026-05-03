"use client";

import { useRouter } from "next/navigation";

import { useFtueHint } from "@/lib/ftue";
import { AddWatchModal } from "@/modules/watchlist/components/AddWatchModal";
import { AirportPickerModal } from "@/modules/watchlist/components/AirportPickerModal";
import { ComparePanels } from "@/modules/watchlist/components/ComparePanels";
import { HistoryIntegratedPanel } from "@/modules/watchlist/components/HistoryIntegratedPanel";
import { SmartWatchListPanel } from "@/modules/watchlist/components/SmartWatchListPanel";
import { monthLabel } from "@/modules/watchlist/dateUtils";
import { useWatchlistController } from "@/modules/watchlist/useWatchlistController";

const LINE_COLORS = ["#D95D39", "#2E6E62", "#B45309", "#0F766E", "#7C2D12", "#1D4ED8"];

const CHART_WIDTH = 920;
const CHART_HEIGHT = 360;
const CHART_PAD = { left: 54, right: 18, top: 18, bottom: 38 };

export default function WatchlistPage() {
  const router = useRouter();

  const watchlistHint = useFtueHint("watchlist");

  const { view, actions, derived, hover, selectWatch } = useWatchlistController({
    chartBaseHeight: CHART_HEIGHT,
    chartWidth: CHART_WIDTH,
    chartPad: CHART_PAD,
    lineColors: LINE_COLORS,
  });

  return (
    <main className="shell watchlist-page" id="main-content">
      <div className="page-header watchlist-header">
        <div className="watchlist-header-left">
          <button className="btn-ghost" type="button" onClick={() => router.push("/dashboard")}>
            Back
          </button>
        </div>
        <div className="page-title">
          <h1>Flight Watchlist</h1>
          <p>Control center to monitor, filter, analyze, and compare without changing screens.</p>
        </div>
        <div className="page-actions watchlist-header-right">
          <button className="btn-primary" type="button" onClick={() => actions.setShowAdd(true)}>
            Add flight
          </button>
        </div>
      </div>

      {watchlistHint.visible ? (
        <section className="notice notice-compact notice-info section-gap" role="status" aria-live="polite">
          <div>
            <strong>Quick start</strong>
            <p>Save flights here to track their changes.</p>
          </div>
          <div className="notice-actions">
            <button type="button" className="btn-ghost btn-compact" onClick={watchlistHint.dismiss}>
              Got it
            </button>
          </div>
        </section>
      ) : null}

      {derived.lastUpdatedGlobal ? (
        <div className="notice notice-info section-gap" role="status" aria-live="polite">
          Last update: {derived.lastUpdatedGlobal}
        </div>
      ) : null}

      {actions.message ? (
        <div
          className={`notice section-gap ${actions.messageType === "success" ? "notice-success" : "notice-error"}`}
          role="status"
          aria-live="polite"
        >
          {actions.message}
        </div>
      ) : null}

      <HistoryIntegratedPanel
        selectedWatch={derived.selectedWatch}
        viewMode={view.viewMode}
        isRefreshingFiltered={actions.isRefreshingFiltered}
        selectedOrigin={view.selectedOrigin}
        selectedDestination={view.selectedDestination}
        selectedDates={view.selectedDates}
        selectedPoint={view.selectedPoint}
        allOrigins={derived.allOrigins}
        allDestinations={derived.allDestinations}
        allTravelDates={derived.allTravelDates}
        pointOptions={derived.pointOptions}
        rangeWindow={view.rangeWindow}
        chartIsCompact={derived.chartIsCompact}
        chartHeight={derived.chartHeight}
        chartModel={derived.chartModel}
        selectedPointData={derived.selectedPointData}
        hoverPoint={hover.hoverPoint}
        summary={derived.summary}
        visibleMonth={derived.visibleMonth}
        monthTitle={monthLabel(derived.visibleMonth)}
        monthCells={derived.monthCells}
        calendarEvents={derived.calendarEvents}
        calendarRange={derived.calendarRange}
        calendarCurrency={derived.calendarCurrency}
        chartWidth={CHART_WIDTH}
        chartPad={CHART_PAD}
        onToggleViewMode={view.toggleViewMode}
        onApplyFilters={actions.refreshFiltered}
        onOriginChange={view.onOriginChange}
        onDestinationChange={view.onDestinationChange}
        onDatesChange={view.onDatesChange}
        onPointChange={view.setSelectedPoint}
        onRangeChange={view.setRangeWindow}
        onToggleRangeWindow={view.toggleRangeWindow}
        onResetZoom={view.resetZoom}
        onChartMouseMove={hover.handleChartMove}
        onChartMouseLeave={hover.clearHover}
        onPrevMonth={view.prevMonth}
        onNextMonth={view.nextMonth}
      />

      <SmartWatchListPanel
        items={actions.items}
        smartListItems={derived.smartListItems}
        watchMeta={derived.watchMeta}
        historyRows={actions.historyRows}
        lastUpdatedGlobal={derived.lastUpdatedGlobal}
        watchSearch={view.watchSearch}
        watchSort={view.watchSort}
        hasSearchFilter={derived.hasSearchFilter}
        selectedWatchId={view.selectedWatchId}
        refreshingWatchId={actions.refreshingWatchId}
        onSearchChange={view.setWatchSearch}
        onSortChange={view.setWatchSort}
        onClearSearch={() => view.setWatchSearch("")}
        onSelectWatch={selectWatch}
        onRefreshWatch={actions.refresh}
        onPauseWatch={(watchId) => actions.updateWatchStatus(watchId, "paused")}
        onResumeWatch={(watchId) => actions.updateWatchStatus(watchId, "active")}
        onDeleteWatch={actions.deleteWatch}
        onBulkPause={(ids) => actions.bulkUpdateStatus(ids, "paused")}
        onBulkResume={(ids) => actions.bulkUpdateStatus(ids, "active")}
        onBulkDelete={actions.bulkDelete}
        onOpenAddWatch={() => actions.setShowAdd(true)}
      />

      <ComparePanels
        compareCards={derived.compareCards}
        compareOptions={derived.compareOptions}
        compareSelection={derived.compareSelection}
        compareBadges={derived.compareBadges}
        compareIds={view.compareIds}
        compareNotice={view.compareNotice}
        onToggleCompare={view.toggleCompare}
      />

      <AddWatchModal
        isOpen={actions.showAdd}
        travelDate={actions.travelDate}
        origin={actions.origin}
        destination={actions.destination}
        targetPrice={actions.targetPrice}
        onClose={() => actions.setShowAdd(false)}
        onSubmit={actions.onSubmit}
        onTravelDateChange={actions.setTravelDate}
        onOriginChange={actions.setOrigin}
        onDestinationChange={actions.setDestination}
        onTargetPriceChange={actions.setTargetPrice}
        onOpenPicker={actions.openPicker}
      />

      <AirportPickerModal
        activePicker={actions.activePicker}
        selectedCountry={actions.selectedCountry}
        compatibleOrigins={actions.compatibleOrigins}
        compatibleDestinations={actions.compatibleDestinations}
        onClose={() => actions.setActivePicker(null)}
        onSelectCountry={actions.setSelectedCountry}
        onClearSelection={actions.clearSelection}
        onSelectAirport={actions.selectAirport}
      />
    </main>
  );
}

