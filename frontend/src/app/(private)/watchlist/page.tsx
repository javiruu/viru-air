"use client";

import { useCallback, useEffect, useMemo, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import { Download } from "lucide-react";

import { buildJsonExportFilename, downloadJson } from "@/modules/shared/jsonExport";
import { readWatchlistNavigationParams, buildWatchlistViewSearchParams } from "@/modules/shared/useRouteState";

import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { useI18n } from "@/i18n";
import { useFtueHint } from "@/lib/ftue";
import { AddWatchModal } from "@/modules/watchlist/components/AddWatchModal";
import { AirportPickerModal } from "@/modules/watchlist/components/AirportPickerModal";
import { ComparePanels } from "@/modules/watchlist/components/ComparePanels";
import { CommunityPricingDrawer } from "@/modules/watchlist/components/CommunityPricingDrawer";
import { HistoryIntegratedPanel } from "@/modules/watchlist/components/HistoryIntegratedPanel";
import { SmartWatchListPanel } from "@/modules/watchlist/components/SmartWatchListPanel";
import { WatchDetailPanel } from "@/modules/watchlist/components/WatchDetailPanel";
import { WatchlistCombinationPanel } from "@/modules/watchlist/components/WatchlistCombinationPanel";
import { monthLabel } from "@/modules/watchlist/dateUtils";
import { buildWatchlistExportPayload } from "@/modules/watchlist/exportWatchlistJson";
import { useWatchlistController } from "@/modules/watchlist/useWatchlistController";
import { useWatchLiveFlight } from "@/modules/watchlist/useWatchLiveFlight";
import {
  selectPrimaryFlightLabel,
  selectPrimaryLivePosition,
} from "@/modules/watchlist/liveFlightPresentation";
import { Skeleton, SkeletonPanel } from "@/modules/shared/Skeleton";

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
    <SkeletonPanel className="watch-map-panel section-gap" ariaLabel={t("watchlist.mapLoadingBody")}>
      <Skeleton variant="pill" width={170} height={18} />
      <Skeleton variant="line" width="64%" />
      <Skeleton variant="card" className="loading-skeleton-card" />
    </SkeletonPanel>
  );
}

const LINE_COLORS = ["#D95D39", "#2E6E62", "#B45309", "#0F766E", "#7C2D12", "#1D4ED8"];

const CHART_WIDTH = 920;
const CHART_HEIGHT = 420;
const CHART_PAD = { left: 54, right: 18, top: 18, bottom: 38 };

export default function WatchlistPage() {
  const router = useRouter();
  const { t, localeTag } = useI18n();
  const { notify } = useNotificationCenter();

  const watchlistHint = useFtueHint("watchlist");

  const { view, actions, derived, hover, viewport, selectWatch, selectWatchById } = useWatchlistController({
    chartBaseHeight: CHART_HEIGHT,
    chartWidth: CHART_WIDTH,
    chartPad: CHART_PAD,
    lineColors: LINE_COLORS,
  });
  const liveFlight = useWatchLiveFlight(derived.selectedWatch?.id ?? null);
  const livePosition = selectPrimaryLivePosition(liveFlight.data);
  const liveFlightLabel = selectPrimaryFlightLabel(liveFlight.data);

  // ── URL state: read navigation params on mount to auto-select flight ─
  const searchParams = useSearchParams();
  const hasAppliedUrlState = useRef(false);
  useEffect(() => {
    if (hasAppliedUrlState.current || actions.items.length === 0) return;
    hasAppliedUrlState.current = true;
    const nav = readWatchlistNavigationParams(searchParams);
    if (nav.watchId) {
      const match = actions.items.find((item) => item.id === nav.watchId);
      if (match) {
        selectWatch(match);
        return;
      }
    }
    if (nav.origin && nav.destination) {
      const match = actions.items.find(
        (item) =>
          item.origin_iata === nav.origin &&
          item.destination_iata === nav.destination &&
          (!nav.travelDate || item.travel_date_local === nav.travelDate),
      );
      if (match) {
        selectWatch(match);
      }
    }
  }, [searchParams, actions.items, selectWatch]);

  // ── URL state: persist selection to URL on change ──────────────────
  const prevSelectionRef = useRef({ watchId: "", origin: "", destination: "", travelDate: "" });
  useEffect(() => {
    if (!hasAppliedUrlState.current) return;
    const current = derived.selectedWatch;
    const prev = prevSelectionRef.current;
    const origin = current?.origin_iata || "";
    const destination = current?.destination_iata || "";
    const travelDate = current?.travel_date_local || "";
    const watchId = current?.id || "";
    if (
      watchId === prev.watchId &&
      origin === prev.origin &&
      destination === prev.destination &&
      travelDate === prev.travelDate
    ) return;
    prevSelectionRef.current = { watchId, origin, destination, travelDate };
    const qs = buildWatchlistViewSearchParams({
      watchId,
      origin,
      destination,
      travelDate,
      view: view.viewMode !== "chart" ? view.viewMode : undefined,
      range: view.rangeWindow !== "30" ? (view.rangeWindow as "30" | "all") : undefined,
    });
    const url = `/watchlist${qs ? `?${qs}` : ""}`;
    router.replace(url, { scroll: false });
  }, [derived.selectedWatch, view.viewMode, view.rangeWindow, router]);

  const hasHistoryData = Boolean(
    (derived.chartModel?.some((serie) => serie.points.length > 0) ?? false) ||
      Object.keys(derived.calendarEvents).length > 0,
  );
  const isLoadingHistory = Boolean(derived.selectedWatch && actions.isLoadingHistoryInitial && !hasHistoryData);
  const isRefreshingHistory = Boolean(actions.isRefreshingFiltered && hasHistoryData);
  const hasNotices = Boolean(watchlistHint.visible || derived.lastUpdatedGlobal || actions.message);
  const selectedRouteContext = useMemo(() => derived.selectedWatch ? ({
    origin: derived.selectedWatch.origin_iata,
    destination: derived.selectedWatch.destination_iata,
    travelDate: derived.selectedWatch.travel_date_local,
    status: derived.selectedWatch.status,
    lastCaptureAt: actions.selectedWatchDetail?.latest_snapshot?.captured_at_utc ?? null,
  }) : null, [derived.selectedWatch, actions.selectedWatchDetail]);

  const handleSelectWatch = useCallback((watch: Parameters<typeof selectWatch>[0]) => {
    selectWatch(watch);
    notify({ tone: "success", title: t("watchlist.messages.flightSelected") });
  }, [selectWatch, notify, t]);
  const onFocusWatch = useCallback((watchId: string) => {
    const watch = actions.items.find((item) => item.id === watchId);
    if (!watch) return;
    handleSelectWatch(watch);
  }, [actions.items, handleSelectWatch]);
  const handleSelectWatchById = (watchId: string) => {
    const watchExists = actions.items.some((item) => item.id === watchId);
    if (!watchExists) return;
    selectWatchById(watchId);
    notify({ tone: "success", title: t("watchlist.messages.flightSelected") });
  };
  const canExportWatchlist = actions.items.length > 0 && !actions.isLoadingWatchlist;
  const handleExportWatchlist = () => {
    if (!canExportWatchlist) return;
    const exportedAt = new Date().toISOString();
    const payload = buildWatchlistExportPayload({
      items: actions.items,
      historyRows: actions.historyRows,
      exportedAt,
    });
    downloadJson(buildJsonExportFilename("viru-watchlist", exportedAt), payload);
    notify({
      tone: "success",
      title: t("watchlist.export.success", {
        count: payload.totals.flights,
        snapshots: payload.totals.snapshots,
      }),
    });
  };

  return (
    <main className="shell watchlist-page" id="main-content">
      <div className="page-header watchlist-header watchlist-page-header-shell">
        <div className="watchlist-header-left">
          <button className="btn-ghost watchlist-back-link" type="button" onClick={() => router.push("/dashboard")}>
            {t("shared.actions.back")}
          </button>
        </div>
        <div className="page-title watchlist-page-title">
          <h1>{t("watchlist.title")}</h1>
          <p>{t("watchlist.subtitle")}</p>
        </div>
        <div className="page-actions watchlist-header-right">
          <button
            className="btn-ghost watchlist-export-cta"
            type="button"
            onClick={handleExportWatchlist}
            disabled={!canExportWatchlist}
            aria-label={t("watchlist.export.ariaLabel")}
          >
            <Download className="qs-inline-icon" aria-hidden="true" />
            {t("watchlist.export.button")}
          </button>
          <button className="btn-primary watchlist-add-cta" type="button" onClick={() => actions.setShowAdd(true)}>
            {t("watchlist.addFlight")}
          </button>
        </div>
      </div>

      {hasNotices ? (
        <div className="watchlist-notice-stack section-gap">
          {watchlistHint.visible ? (
            <section className="notice notice-compact notice-info watchlist-notice watchlist-notice--hint" role="status" aria-live="polite">
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
            <div className="notice notice-compact notice-info watchlist-notice watchlist-notice--freshness" role="status" aria-live="polite">
              {t("watchlist.lastUpdate", { value: derived.lastUpdatedGlobal })}
            </div>
          ) : null}

          {actions.message ? (
            <div
              className={`notice notice-compact watchlist-notice watchlist-notice--message ${actions.messageType === "success" ? "notice-success" : "notice-error"}`}
              role="status"
              aria-live="polite"
            >
              {actions.message}
            </div>
          ) : null}
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
            chartIsCompact={derived.chartIsCompact}
            chartHeight={derived.chartHeight}
            chartModel={derived.chartModel}
            selectedPointData={derived.selectedPointData}
            hoverPoint={hover.hoverPoint}
            visibleMonth={derived.visibleMonth}
            monthTitle={monthLabel(derived.visibleMonth, localeTag)}
            monthCells={derived.monthCells}
            calendarEvents={derived.calendarEvents}
            calendarRange={derived.calendarRange}
            calendarCurrency={derived.calendarCurrency}
            calendarHasUsefulData={derived.calendarHasUsefulData}
            chartWidth={CHART_WIDTH}
            chartPad={CHART_PAD}
            chartViewBox={viewport.viewBox}
            chartIsZoomed={viewport.isZoomed}
            chartIsDragging={viewport.isDragging}
            onApplyFilters={actions.refreshFiltered}
            onChartMouseMove={hover.handleChartMove}
            onChartMouseLeave={hover.clearHover}
            onChartWheel={viewport.onWheel}
            onChartPointerDown={viewport.onPointerDown}
            onChartPointerMove={viewport.onPointerMove}
            onChartPointerUp={viewport.onPointerUp}
            onChartPointerCancel={viewport.onPointerCancel}
            onChartPointerLeave={viewport.onPointerLeave}
            onResetChartZoom={viewport.resetZoom}
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
            onSearchChange={view.setWatchSearch}
            onSortChange={view.setWatchSort}
            onClearSearch={() => view.setWatchSearch("")}
            onSelectWatch={handleSelectWatch}
            onCommunityAction={(watch, trigger) => {
              actions.communityPricing.open(watch, trigger);
            }}
            onPauseWatch={(watchId) => actions.updateWatchStatus(watchId, "paused")}
            onResumeWatch={(watchId) => actions.updateWatchStatus(watchId, "active")}
            onDeleteWatch={actions.deleteWatch}
            onBulkPause={(ids) => actions.bulkUpdateStatus(ids, "paused")}
            onBulkResume={(ids) => actions.bulkUpdateStatus(ids, "active")}
            onBulkDelete={actions.bulkDelete}
            isLoading={actions.isLoadingWatchlist}
            listErrorMessage={actions.listErrorMessage}
            onRetryLoad={actions.load}
            onOpenAddWatch={() => actions.setShowAdd(true)}
            isCalendarSelectorOpen={view.isCalendarSelectorOpen}
            calendarSelectorDay={view.calendarSelectorDay}
            calendarSelectorMonth={derived.calendarSelectorVisibleMonth}
            calendarSelectorMonthCells={derived.calendarSelectorMonthCells}
            calendarSelectorEvents={derived.calendarSelectorEvents}
            calendarSelectorFlightsByDay={derived.calendarSelectorFlightsByDay}
            onToggleCalendarSelector={view.toggleCalendarSelector}
            onCloseCalendarSelector={view.closeCalendarSelector}
            onCalendarSelectorDayChange={view.setCalendarSelectorDay}
            onSelectWatchById={handleSelectWatchById}
            onCalendarPrevMonth={view.prevMonth}
            onCalendarNextMonth={view.nextMonth}
          />
          <WatchlistCombinationPanel
            groups={derived.combinationGroups}
            selectedWatchId={view.selectedWatchId}
            onSelectWatchById={handleSelectWatchById}
          />
        </div>

        <div className="watchlist-area watchlist-area-detail">
          <WatchDetailPanel
            selectedWatch={derived.selectedWatch}
            detail={actions.selectedWatchDetail}
            summary={actions.selectedWatchSummary}
            isLoading={actions.isLoadingSelectedWatchDetail}
            liveTracking={liveFlight.data}
            isLoadingLiveTracking={liveFlight.isLoading}
            isRefreshingLiveTracking={liveFlight.isRefreshing}
            hasLiveTrackingError={liveFlight.hasError}
            onRefreshLiveTracking={liveFlight.refresh}
            onPauseWatch={(watchId) => actions.updateWatchStatus(watchId, "paused")}
            onResumeWatch={(watchId) => actions.updateWatchStatus(watchId, "active")}
            onSaveFareProfile={actions.updateFareProfile}
            mapContent={
              derived.selectedWatch ? (
                <WatchlistMapDecisionPanel
                  routes={derived.watchMapRoutes}
                  hasSelectedRoute
                  hasWatchItems={actions.items.length > 0}
                  selectedRouteContext={selectedRouteContext}
                  mode={derived.watchMapMode}
                  insight={derived.watchMapInsight}
                  compareLimitExceeded={view.compareIds.length > 4}
                  livePosition={livePosition}
                  liveFlightLabel={liveFlightLabel}
                  onFocusWatch={onFocusWatch}
                />
              ) : null
            }
          />
        </div>

        <div className="watchlist-area watchlist-area-compare">
          <ComparePanels
            compareOptions={derived.compareOptions}
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

      <CommunityPricingDrawer
        watch={actions.communityPricing.activeWatch}
        stage={actions.communityPricing.stage}
        price={actions.communityPricing.price}
        isSaving={actions.communityPricing.isSaving}
        error={actions.communityPricing.error}
        onPriceChange={actions.communityPricing.setPrice}
        onClose={actions.communityPricing.close}
        onMarkPurchased={() => {
          void actions.communityPricing.markPurchased();
        }}
        onBeginContribution={actions.communityPricing.beginContribution}
        onReturnToOverview={actions.communityPricing.backToOverview}
        onChooseFlew={actions.communityPricing.chooseFlew}
        onSaveNoFlight={() => {
          void actions.communityPricing.saveNoFlight();
        }}
        onSavePrice={() => {
          void actions.communityPricing.savePrice();
        }}
        onDeleteResponse={() => {
          void actions.communityPricing.deleteResponse();
        }}
        onDismissThanks={actions.communityPricing.dismissThanks}
      />
    </main>
  );
}

