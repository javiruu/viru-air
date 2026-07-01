import React, { memo, RefObject } from "react";
import { createPortal } from "react-dom";

import { QuickSearchFieldErrors } from "@/modules/quick-search/types";
import { QuickSearchCopyKey } from "@/modules/shared/quickSearchCopy";

type ActiveChip = {
  id: string;
  label: string;
  onClear: () => void;
};

type FilterConsoleProps = {
  activeChips: ActiveChip[];
  activeFiltersCount: number;
  appliedFiltersCount: number;
  pendingSearchChanges: boolean;
  isFiltersOpen: boolean;
  isCollapsed: boolean;
  radiusActive: boolean;
  radiusKm: number;

  includeStops: boolean;
  maxStops: number;
  bufferMin: string;
  includeNearbyOrigins: boolean;
  includeNearbyDestinations: boolean;
  departAfter: string;
  departBefore: string;
  strictFilters: boolean;
  excludeOrigins: string[];
  excludeDestinations: string[];
  excludeOriginInput: string;
  excludeDestinationInput: string;
  prefAvailable: boolean;
  prefBadge: boolean;
  fieldErrors: QuickSearchFieldErrors;
  filtersCloseRef: RefObject<HTMLButtonElement | null>;
  t: (key: QuickSearchCopyKey) => string;
  setRadiusKm: (value: number) => void;

  setIncludeStops: (value: boolean) => void;
  setMaxStops: (value: number) => void;
  setBufferMin: (value: string) => void;
  setIncludeNearbyOrigins: (value: boolean) => void;
  setIncludeNearbyDestinations: (value: boolean) => void;
  setDepartAfter: (value: string) => void;
  setDepartBefore: (value: string) => void;
  setStrictFilters: (value: boolean) => void;
  setExcludeOrigins: (value: string[]) => void;
  setExcludeDestinations: (value: string[]) => void;
  setExcludeOriginInput: (value: string) => void;
  setExcludeDestinationInput: (value: string) => void;
  addExcludeOrigin: () => void;
  addExcludeDestination: () => void;
  removeExcludeOrigin: (iata: string) => void;
  removeExcludeDestination: (iata: string) => void;
  onOpenFilters: () => void;
  onCloseFilters: () => void;
  onToggleCollapsed: () => void;
  onApplyAndSearch: () => void;
  onApplyPreferences: () => void;
  onClearAllFilters: () => void;
  onResetCoverage: () => void;
  onResetTiming: () => void;
  onResetExperimental: () => void;
  onPresetDirect: () => void;
  onPresetOriginNearby: () => void;
  onPresetBothNearby: () => void;
  onPresetRegional: () => void;
};

function QuickSearchCloseIcon() {
  return (
    <svg className="qs-inline-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M6.75 6.75 17.25 17.25M17.25 6.75 6.75 17.25"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
      />
    </svg>
  );
}

function SupportBadge({ children, tone = "neutral" }: { children: string; tone?: "neutral" | "partial" | "live" }) {
  return <span className={`qs-filter-support qs-filter-support-${tone}`}>{children}</span>;
}

function QuickSearchFilterConsoleInner(props: FilterConsoleProps) {

  const coverageSummary = props.radiusActive
    ? `${props.radiusKm} km`
    : props.t("filterCoverageDirect");
  const consoleSubtitle = props.radiusActive ? props.t("filterConsoleSubtitleFlex") : props.t("filterConsoleSubtitleExact");

  const drawer = (
    <>
      <button
        type="button"
        className="qs-filters-backdrop"
        aria-label={props.t("pickClose")}
        onClick={props.onCloseFilters}
      />
      <aside
        id="qs-filters-drawer"
        role="dialog"
        aria-modal="true"
        aria-label={props.t("filtersTitle")}
        className="panel panel-soft qs-filters-panel open"
        data-ui="qs-filter-drawer"
      >
        <div className="qs-filters-header">
          <div>
            <span className="qs-filter-eyebrow">{props.t("filterConsoleEyebrow")}</span>
            <h2>{props.t("filtersTitle")}</h2>
            <span className="muted">{props.t("filtersSubtitle")}</span>
            <p className="panel-note">{props.t("filtersMicrocopy")}</p>
          </div>
          <button
            type="button"
            className="btn-ghost qs-filters-close"
            aria-label={props.t("pickClose")}
            ref={props.filtersCloseRef}
            onClick={props.onCloseFilters}
          >
            {props.t("pickClose")}
          </button>
        </div>

        <div className="qs-filter-console-drawer">
          <section className="qs-filter-group qs-filter-group-guided" data-ui="qs-filter-coverage">
            <div className="qs-filter-section-head">
              <div>
                <span className="qs-filter-eyebrow">{props.t("filterAppliedOnSearch")}</span>
                <h3>Dónde puede buscar Viru</h3>
                <p>Amplía la búsqueda a aeropuertos cercanos o excluye los que no te interesen.</p>
              </div>
              <div className="qs-filter-section-actions">
                {props.prefBadge ? <span className="badge badge-control">{props.t("appliedPref")}</span> : null}
                <button type="button" className="btn-ghost btn-compact" onClick={props.onResetCoverage} data-ui="qs-filter-reset-coverage">
                  {props.t("resetGroup")}
                </button>
              </div>
            </div>
            <div className="qs-filter-presets" data-ui="qs-filter-coverage-presets">
              <button type="button" className="qs-filter-preset" onClick={props.onPresetDirect} data-ui="qs-filter-preset-direct">
                <strong>{props.t("filterPresetDirect")}</strong>
                <span>{props.t("filterPresetDirectHint")}</span>
              </button>
              <button type="button" className="qs-filter-preset" onClick={props.onPresetOriginNearby} data-ui="qs-filter-preset-origin-nearby">
                <strong>{props.t("filterPresetOriginNearby")}</strong>
                <span>{props.t("filterPresetOriginNearbyHint")}</span>
              </button>
              <button type="button" className="qs-filter-preset" onClick={props.onPresetBothNearby} data-ui="qs-filter-preset-both-nearby">
                <strong>{props.t("filterPresetBothNearby")}</strong>
                <span>{props.t("filterPresetBothNearbyHint")}</span>
              </button>
              <button type="button" className="qs-filter-preset" onClick={props.onPresetRegional} data-ui="qs-filter-preset-regional">
                <strong>{props.t("filterPresetRegional")}</strong>
                <span>{props.t("filterPresetRegionalHint")}</span>
              </button>
            </div>
          </section>
        </div>

        <div className="qs-filter-actions">
          <button type="button" className="btn-ghost qs-reset-all" onClick={props.onClearAllFilters} disabled={props.activeChips.length === 0} data-ui="qs-filter-reset-all">
            {props.t("resetAll")}
          </button>
          <button type="button" className="btn-ghost" onClick={props.onApplyPreferences} disabled={!props.prefAvailable} data-ui="qs-filter-apply-preferences">
            {props.t("resetPrefs")}
          </button>
          {props.pendingSearchChanges ? (
            <button type="button" className="btn-search" onClick={props.onApplyAndSearch} data-ui="qs-filter-apply-search">
              {props.t("applyAndSearch")}
            </button>
          ) : null}
        </div>
      </aside>
    </>
  );

  return (
    <section className={`panel panel-soft qs-filter-console ${props.isCollapsed ? "is-collapsed" : ""}`} data-ui="qs-filter-console">
      <div className="qs-filter-console-head">
        <div>
          <span className="qs-filter-eyebrow">{props.t("filterConsoleEyebrow")}</span>
          <h3>{props.t("filterConsoleTitle")}</h3>
          <p>{consoleSubtitle}</p>
        </div>
        <div className="qs-filter-console-actions">
          <span className="qs-filter-count" data-ui="qs-filter-count">
            {props.activeFiltersCount} {props.t("filterCountLabel")}
            {props.appliedFiltersCount > 0 ? ` / ${props.appliedFiltersCount}` : ""}
          </span>
          {props.activeChips.length > 0 ? (
            <button type="button" className="btn-ghost btn-compact qs-reset-all-inline" onClick={props.onClearAllFilters}>
              {props.t("resetAll")}
            </button>
          ) : null}
          <button
            type="button"
            className="btn-ghost btn-compact"
            aria-expanded={!props.isCollapsed}
            onClick={props.onToggleCollapsed}
            data-ui="qs-filter-console-toggle"
          >
            {props.isCollapsed ? props.t("filterConsoleToggleOpen") : props.t("filterConsoleToggleClose")}
          </button>
          <button type="button" className="btn-ghost btn-compact" onClick={props.onOpenFilters} data-ui="qs-filter-open">
            {props.t("toolbarFilters")}
          </button>
        </div>
      </div>

      {!props.isCollapsed ? <div className="qs-filter-console-grid">
        <button type="button" className="qs-filter-console-card" onClick={props.onOpenFilters} data-ui="qs-filter-card-coverage" aria-label="Dónde puede buscar Viru">
          <span>Dónde puede buscar Viru</span>
          <strong>{coverageSummary}</strong>
          <SupportBadge tone="live">{props.t("filterAppliedOnSearch")}</SupportBadge>
        </button>
      </div> : null}

      {!props.isCollapsed ? <div className="qs-filter-mode-legend" aria-live="polite">
        <span className="qs-filter-mode-chip">{props.t("filterAppliedOnSearch")}</span>
        <span className="qs-filter-mode-chip">{props.t("filterAppliedToResults")}</span>
      </div> : null}

      {!props.isCollapsed && props.pendingSearchChanges ? (
        <div className="qs-filter-pending" role="status" aria-live="polite" data-ui="qs-filter-pending">
          <div>
            <strong>{props.t("pendingChangesTitle")}</strong>
            <span>{props.t("pendingChangesBody")}</span>
          </div>
          <button type="button" className="btn-search qs-filter-pending-cta" onClick={props.onApplyAndSearch} data-ui="qs-filter-pending-apply-search">
            {props.t("applyAndSearch")}
          </button>
        </div>
      ) : null}



      {props.isFiltersOpen && typeof document !== "undefined" ? createPortal(drawer, document.body) : null}
    </section>
  );
}

function areFilterConsolePropsEqual(prev: FilterConsoleProps, next: FilterConsoleProps): boolean {
  return (
    prev.activeChips === next.activeChips
    && prev.activeFiltersCount === next.activeFiltersCount
    && prev.appliedFiltersCount === next.appliedFiltersCount
    && prev.pendingSearchChanges === next.pendingSearchChanges
    && prev.isFiltersOpen === next.isFiltersOpen
    && prev.isCollapsed === next.isCollapsed
    && prev.radiusActive === next.radiusActive
    && prev.radiusKm === next.radiusKm
    && prev.includeStops === next.includeStops
    && prev.maxStops === next.maxStops
    && prev.bufferMin === next.bufferMin
    && prev.includeNearbyOrigins === next.includeNearbyOrigins
    && prev.includeNearbyDestinations === next.includeNearbyDestinations
    && prev.departAfter === next.departAfter
    && prev.departBefore === next.departBefore
    && prev.strictFilters === next.strictFilters
    && prev.excludeOrigins === next.excludeOrigins
    && prev.excludeDestinations === next.excludeDestinations
    && prev.excludeOriginInput === next.excludeOriginInput
    && prev.excludeDestinationInput === next.excludeDestinationInput
    && prev.prefAvailable === next.prefAvailable
    && prev.prefBadge === next.prefBadge
    && prev.fieldErrors === next.fieldErrors
    && prev.filtersCloseRef === next.filtersCloseRef
    && prev.t === next.t
    && prev.setRadiusKm === next.setRadiusKm
    && prev.setIncludeStops === next.setIncludeStops
    && prev.setMaxStops === next.setMaxStops
    && prev.setBufferMin === next.setBufferMin
    && prev.setIncludeNearbyOrigins === next.setIncludeNearbyOrigins
    && prev.setIncludeNearbyDestinations === next.setIncludeNearbyDestinations
    && prev.setDepartAfter === next.setDepartAfter
    && prev.setDepartBefore === next.setDepartBefore
    && prev.setStrictFilters === next.setStrictFilters
    && prev.setExcludeOrigins === next.setExcludeOrigins
    && prev.setExcludeDestinations === next.setExcludeDestinations
    && prev.setExcludeOriginInput === next.setExcludeOriginInput
    && prev.setExcludeDestinationInput === next.setExcludeDestinationInput
    && prev.addExcludeOrigin === next.addExcludeOrigin
    && prev.addExcludeDestination === next.addExcludeDestination
    && prev.removeExcludeOrigin === next.removeExcludeOrigin
    && prev.removeExcludeDestination === next.removeExcludeDestination
    && prev.onOpenFilters === next.onOpenFilters
    && prev.onCloseFilters === next.onCloseFilters
    && prev.onToggleCollapsed === next.onToggleCollapsed
    && prev.onApplyAndSearch === next.onApplyAndSearch
    && prev.onApplyPreferences === next.onApplyPreferences
    && prev.onClearAllFilters === next.onClearAllFilters
    && prev.onResetCoverage === next.onResetCoverage
    && prev.onResetTiming === next.onResetTiming
    && prev.onResetExperimental === next.onResetExperimental
    && prev.onPresetDirect === next.onPresetDirect
    && prev.onPresetOriginNearby === next.onPresetOriginNearby
    && prev.onPresetBothNearby === next.onPresetBothNearby
    && prev.onPresetRegional === next.onPresetRegional
  );
}

export const QuickSearchFilterConsole = memo(QuickSearchFilterConsoleInner, areFilterConsolePropsEqual);
