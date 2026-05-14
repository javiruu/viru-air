"use client";

import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";

import { useI18n } from "@/i18n";
import { useFtueHint } from "@/lib/ftue";
import { AddWatchModal } from "@/modules/watchlist/components/AddWatchModal";
import { AirportPickerModal } from "@/modules/watchlist/components/AirportPickerModal";
import { ComparePanels } from "@/modules/watchlist/components/ComparePanels";
import { HistoryIntegratedPanel } from "@/modules/watchlist/components/HistoryIntegratedPanel";
import { SmartWatchListPanel } from "@/modules/watchlist/components/SmartWatchListPanel";
import { WatchDetailPanel } from "@/modules/watchlist/components/WatchDetailPanel";
import { monthLabel } from "@/modules/watchlist/dateUtils";
import { useWatchlistController } from "@/modules/watchlist/useWatchlistController";

const WatchlistMapDecisionPanel = dynamic(
  () =>
    import("@/modules/watchlist/components/WatchlistMapDecisionPanel").then(
      (module) => module.WatchlistMapDecisionPanel,
    ),
  {
    ssr: false,
    loading: () => <WatchlistMapLoadingPanel />,
  },
);

function WatchlistMapLoadingPanel() {
  const { t } = useI18n();
  return (
    <section className="panel panel-soft watch-map-panel section-gap">
      <div className="panel-header">
        <h2 className="panel-title">{t("watchlist.mapLoadingTitle")}</h2>
      </div>
      <p className="panel-note">{t("watchlist.mapLoadingBody")}</p>
    </section>
  );
}

const LINE_COLORS = ["#D95D39", "#2E6E62", "#B45309", "#0F766E", "#7C2D12", "#1D4ED8"];

const CHART_WIDTH = 920;
const CHART_HEIGHT = 360;
const CHART_PAD = { left: 54, right: 18, top: 18, bottom: 38 };

export default function WatchlistPage() {
  const router = useRouter();
  const { t } = useI18n();

  const watchlistHint = useFtueHint("watchlist");

  const { view, actions, derived, hover, selectWatch } = useWatchlistController({
    chartBaseHeight: CHART_HEIGHT,
    chartWidth: CHART_WIDTH,
    chartPad: CHART_PAD,
    lineColors: LINE_COLORS,
  });
  const hasHistoryData = Boolean(
    (derived.chartModel?.some((serie) => serie.points.length > 0) ?? false) ||
      Object.keys(derived.calendarEvents).length > 0,
  );
  const isLoadingHistory = Boolean(derived.selectedWatch && actions.isLoadingHistoryInitial && !hasHistoryData);
  const isRefreshingHistory = Boolean(actions.isRefreshingFiltered && hasHistoryData);

  return (
    <main className="shell watchlist-page" id="main-content">
      <div className="page-header watchlist-header">
        <div className="watchlist-header-left">
          <button className="btn-ghost" type="button" onClick={() => router.push("/dashboard")}>
            {t("shared.actions.back")}
          </button>
        </div>
        <div className="page-title">
          <h1>{t("watchlist.title")}</h1>
          <p>{t("watchlist.subtitle")}</p>
        </div>
        <div className="page-actions watchlist-header-right">
          <button className="btn-primary" type="button" onClick={() => actions.setShowAdd(true)}>
            {t("watchlist.addFlight")}
          </button>
        </div>
      </div>

      {watchlistHint.visible ? (
        <section className="notice notice-compact notice-info section-gap" role="status" aria-live="polite">
          <div>
            <strong>{t("watchlist.quickStartTitle")}</strong>
            <p>{t("watchlist.quickStartBody")}</p>
          </div>
          <div className="notice-actions">
            <button type="button" className="btn-ghost btn-compact" onClick={watchlistHint.dismiss}>
              {t("watchlist.quickStartConfirm")}
            </button>
          </div>
        </section>
      ) : null}

      {derived.lastUpdatedGlobal ? (
        <div className="notice notice-info section-gap" role="status" aria-live="polite">
          {t("watchlist.lastUpdate", { value: derived.lastUpdatedGlobal })}
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

      <section className="watchlist-cockpit-grid section-gap">
        <div className="watchlist-area watchlist-area-history">
          <HistoryIntegratedPanel
            selectedWatch={derived.selectedWatch}
            viewMode={view.viewMode}
            isLoadingHistory={isLoadingHistory}
            isRefreshingHistory={isRefreshingHistory}
            isRefreshingFiltered={actions.isRefreshingFiltered}
            selectedOrigin={view.selectedOrigin}
            selectedDestination={view.selectedDestination}
            selectedDates={view.selectedDates}
            selectedPoint={view.selectedPoint}
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
            calendarHasUsefulData={derived.calendarHasUsefulData}
            chartWidth={CHART_WIDTH}
            chartPad={CHART_PAD}
            onToggleViewMode={view.toggleViewMode}
            onApplyFilters={actions.refreshFiltered}
            onPointChange={view.setSelectedPoint}
            onRangeChange={view.setRangeWindow}
            onToggleRangeWindow={view.toggleRangeWindow}
            onResetZoom={view.resetZoom}
            onChartMouseMove={hover.handleChartMove}
            onChartMouseLeave={hover.clearHover}
            onPrevMonth={view.prevMonth}
            onNextMonth={view.nextMonth}
          />
        </div>

        <div className="watchlist-area watchlist-area-routes">
          <SmartWatchListPanel
            items={actions.items}
            smartListItems={derived.smartListItems}
            watchMeta={derived.watchMeta}
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
            onBulkRefresh={actions.bulkRefresh}
            isRefreshingBulk={actions.isRefreshingBulk}
            isLoading={actions.isLoadingWatchlist}
            listErrorMessage={actions.listErrorMessage}
            onRetryLoad={actions.load}
            onOpenAddWatch={() => actions.setShowAdd(true)}
          />
        </div>

        <div className="watchlist-area watchlist-area-detail">
          <WatchDetailPanel
            selectedWatch={derived.selectedWatch}
            detail={actions.selectedWatchDetail}
            summary={actions.selectedWatchSummary}
            isLoading={actions.isLoadingSelectedWatchDetail}
            onRefreshWatch={actions.refresh}
            onPauseWatch={(watchId) => actions.updateWatchStatus(watchId, "paused")}
            onResumeWatch={(watchId) => actions.updateWatchStatus(watchId, "active")}
          />
        </div>

        <div className="watchlist-area watchlist-area-map">
          <WatchlistMapDecisionPanel
            routes={derived.watchMapRoutes}
            hasSelectedRoute={Boolean(derived.selectedWatch)}
            hasWatchItems={actions.items.length > 0}
            selectedRouteContext={
              derived.selectedWatch
                ? {
                    origin: derived.selectedWatch.origin_iata,
                    destination: derived.selectedWatch.destination_iata,
                    travelDate: derived.selectedWatch.travel_date_local,
                    status: derived.selectedWatch.status,
                    lastCaptureAt: actions.selectedWatchDetail?.latest_snapshot?.captured_at_utc ?? null,
                  }
                : null
            }
            mode={derived.watchMapMode}
            insight={derived.watchMapInsight}
            compareLimitExceeded={view.compareIds.length > 4}
            onFocusWatch={(watchId) => {
              const watch = actions.items.find((item) => item.id === watchId);
              if (!watch) return;
              selectWatch(watch);
            }}
          />
        </div>

        <div className="watchlist-area watchlist-area-compare">
          <ComparePanels
            compareCards={derived.compareCards}
            compareOptions={derived.compareOptions}
            compareSelection={derived.compareSelection}
            compareBadges={derived.compareBadges}
            compareIds={view.compareIds}
            compareNotice={view.compareNotice}
            onToggleCompare={view.toggleCompare}
          />
        </div>
      </section>

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

