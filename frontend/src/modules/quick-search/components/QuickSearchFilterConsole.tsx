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
  radiusActive: boolean;
  radiusKm: number;
  priceMin: string;
  priceMax: string;
  durationMax: string;
  riskFilter: "all" | "low" | "medium" | "high";
  sortBy: "ranking" | "price" | "duration" | "risk" | "freshness";
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
  formatRiskLabel: (label?: string | null) => string;
  setRadiusKm: (value: number) => void;
  setPriceMin: (value: string) => void;
  setPriceMax: (value: string) => void;
  setDurationMax: (value: string) => void;
  setRiskFilter: (value: "all" | "low" | "medium" | "high") => void;
  setSortBy: (value: "ranking" | "price" | "duration" | "risk" | "freshness") => void;
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
  onApplyAndSearch: () => void;
  onApplyPreferences: () => void;
  onClearAllFilters: () => void;
  onResetCoverage: () => void;
  onResetTiming: () => void;
  onResetVisible: () => void;
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
  const timingSummary = `${props.departAfter || "--"}-${props.departBefore || "--"}`;
  const visibleSummary =
    props.priceMin || props.priceMax || props.durationMax || props.riskFilter !== "all"
      ? props.t("filterVisibleCustom")
      : props.t("filterVisibleOpen");
  const experimentalSummary = props.includeStops ? props.t("filterExperimentalOn") : props.t("filterExperimentalOff");

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
                <h3>{props.t("coverageTitle")}</h3>
                <p>{props.t("coverageBody")}</p>
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
            <div className="qs-filter-grid">
              <label className="qs-check" data-ui="qs-filter-nearby-origin">
                <input
                  type="checkbox"
                  name="include_nearby_origins"
                  checked={props.includeNearbyOrigins}
                  onChange={(e) => props.setIncludeNearbyOrigins(e.target.checked)}
                />
                <span className="qs-check-ui" aria-hidden="true">
                  <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                    <path d="M5.5 12.5 10 17l8.5-9" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
                {props.t("nearbyOrigins")}
              </label>
              <label className="qs-check" data-ui="qs-filter-nearby-destination">
                <input
                  type="checkbox"
                  name="include_nearby_destinations"
                  checked={props.includeNearbyDestinations}
                  onChange={(e) => props.setIncludeNearbyDestinations(e.target.checked)}
                />
                <span className="qs-check-ui" aria-hidden="true">
                  <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                    <path d="M5.5 12.5 10 17l8.5-9" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
                {props.t("nearbyDestinations")}
              </label>
              <label className="field qs-filter-wide">
                {props.t("radiusLabel")}
                <div className="qs-range">
                  <input
                    type="range"
                    name="radius_km_range"
                    min={10}
                    max={500}
                    step={10}
                    value={props.radiusKm}
                    onChange={(e) => props.setRadiusKm(Number(e.target.value))}
                    disabled={!props.radiusActive}
                    data-ui="qs-filter-radius-range"
                  />
                  <input
                    name="radius_km"
                    type="number"
                    min={10}
                    max={500}
                    step={10}
                    autoComplete="off"
                    value={props.radiusKm}
                    onChange={(e) => props.setRadiusKm(Number(e.target.value))}
                    className="qs-input"
                    disabled={!props.radiusActive}
                    data-ui="qs-filter-radius-input"
                  />
                </div>
                <small className="muted">{props.radiusActive ? props.t("radiusHint") : props.t("radiusInactive")}</small>
              </label>
              <div className="field">
                <span>{props.t("excludeOrigins")}</span>
                <div className="qs-chip-input">
                  {props.excludeOrigins.map((iata) => (
                    <button
                      key={`origin-${iata}`}
                      type="button"
                      className="qs-chip"
                      onClick={() => props.removeExcludeOrigin(iata)}
                      aria-label={props.t("ariaRemoveFilter").replace("{value}", iata)}
                    >
                      <span>{iata}</span>
                      <QuickSearchCloseIcon />
                    </button>
                  ))}
                  <input
                    name="exclude_origins"
                    autoComplete="off"
                    value={props.excludeOriginInput}
                    onChange={(e) => props.setExcludeOriginInput(e.target.value.toUpperCase())}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === "," || e.key === " ") {
                        e.preventDefault();
                        props.addExcludeOrigin();
                      }
                    }}
                    onBlur={props.addExcludeOrigin}
                    placeholder="MAD, BCN"
                    className="qs-input"
                    data-ui="qs-filter-exclude-origins"
                  />
                </div>
              </div>
              <div className="field">
                <span>{props.t("excludeDestinations")}</span>
                <div className="qs-chip-input">
                  {props.excludeDestinations.map((iata) => (
                    <button
                      key={`dest-${iata}`}
                      type="button"
                      className="qs-chip"
                      onClick={() => props.removeExcludeDestination(iata)}
                      aria-label={props.t("ariaRemoveFilter").replace("{value}", iata)}
                    >
                      <span>{iata}</span>
                      <QuickSearchCloseIcon />
                    </button>
                  ))}
                  <input
                    name="exclude_destinations"
                    autoComplete="off"
                    value={props.excludeDestinationInput}
                    onChange={(e) => props.setExcludeDestinationInput(e.target.value.toUpperCase())}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === "," || e.key === " ") {
                        e.preventDefault();
                        props.addExcludeDestination();
                      }
                    }}
                    onBlur={props.addExcludeDestination}
                    placeholder="DUB, LIS"
                    className="qs-input"
                    data-ui="qs-filter-exclude-destinations"
                  />
                </div>
              </div>
            </div>
          </section>

          <section className="qs-filter-group qs-filter-group-guided" data-ui="qs-filter-timing">
            <div className="qs-filter-section-head">
              <div>
                <span className="qs-filter-eyebrow">{props.t("filterAppliedOnSearch")}</span>
                <h3>{props.t("timeTitle")}</h3>
                <p>{props.t("timeSubtitle")}</p>
              </div>
              <button type="button" className="btn-ghost btn-compact" onClick={props.onResetTiming} data-ui="qs-filter-reset-timing">
                {props.t("resetGroup")}
              </button>
            </div>
            <div className="qs-filter-grid">
              <label className="field">
                {props.t("departAfter")}
                <input
                  type="time"
                  name="depart_after"
                  autoComplete="off"
                  value={props.departAfter}
                  onChange={(e) => props.setDepartAfter(e.target.value)}
                  className="qs-input"
                  data-ui="qs-filter-depart-after"
                />
              </label>
              <label className="field">
                {props.t("departBefore")}
                <input
                  type="time"
                  name="depart_before"
                  autoComplete="off"
                  value={props.departBefore}
                  onChange={(e) => props.setDepartBefore(e.target.value)}
                  className="qs-input"
                  data-ui="qs-filter-depart-before"
                />
              </label>
              <label className="qs-check qs-filter-wide" data-ui="qs-filter-strict">
                <input
                  type="checkbox"
                  name="strict_filters"
                  checked={props.strictFilters}
                  onChange={(e) => props.setStrictFilters(e.target.checked)}
                />
                <span className="qs-check-ui" aria-hidden="true">
                  <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                    <path d="M5.5 12.5 10 17l8.5-9" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
                {props.t("strictMode")}
              </label>
            </div>
            {!props.strictFilters ? <div className="qs-warning">{props.t("strictWarning")}</div> : null}
          </section>

          <section className="qs-filter-group qs-filter-group-guided" data-ui="qs-filter-visible-results">
            <div className="qs-filter-section-head">
              <div>
                <span className="qs-filter-eyebrow">{props.t("filterAppliedToResults")}</span>
                <h3>{props.t("visibleResultsTitle")}</h3>
                <p>{props.t("visibleResultsBody")}</p>
              </div>
              <button type="button" className="btn-ghost btn-compact" onClick={props.onResetVisible} data-ui="qs-filter-reset-visible">
                {props.t("resetGroup")}
              </button>
            </div>
            <div className="qs-filter-grid">
              <label className="field">
                {props.t("priceMin")}
                <input
                  type="number"
                  min={0}
                  step={1}
                  name="price_min"
                  autoComplete="off"
                  value={props.priceMin}
                  onChange={(e) => props.setPriceMin(e.target.value)}
                  placeholder="10"
                  className="qs-input"
                  aria-invalid={Boolean(props.fieldErrors.price_min)}
                  data-ui="qs-filter-price-min"
                />
                {props.fieldErrors.price_min ? <small className="qs-error">{props.fieldErrors.price_min}</small> : null}
              </label>
              <label className="field">
                {props.t("priceMax")}
                <input
                  type="number"
                  min={0}
                  step={1}
                  name="price_max"
                  autoComplete="off"
                  value={props.priceMax}
                  onChange={(e) => props.setPriceMax(e.target.value)}
                  placeholder="120"
                  className="qs-input"
                  aria-invalid={Boolean(props.fieldErrors.price_max)}
                  data-ui="qs-filter-price-max"
                />
                {props.fieldErrors.price_max ? <small className="qs-error">{props.fieldErrors.price_max}</small> : null}
              </label>
              <label className="field">
                {props.t("durationMax")}
                <input
                  type="number"
                  min={1}
                  step={1}
                  name="duration_max"
                  autoComplete="off"
                  value={props.durationMax}
                  onChange={(e) => props.setDurationMax(e.target.value)}
                  placeholder="240"
                  className="qs-input"
                  aria-invalid={Boolean(props.fieldErrors.duration_max)}
                  data-ui="qs-filter-duration-max"
                />
                {props.fieldErrors.duration_max ? <small className="qs-error">{props.fieldErrors.duration_max}</small> : null}
              </label>
              <label className="field">
                {props.t("riskAllowed")}
                <select
                  name="risk_filter"
                  autoComplete="off"
                  value={props.riskFilter}
                  onChange={(e) => props.setRiskFilter(e.target.value as "all" | "low" | "medium" | "high")}
                  className="qs-input"
                  data-ui="qs-filter-risk"
                >
                  <option value="all">{props.t("riskAll")}</option>
                  <option value="low">{props.t("riskLow")}</option>
                  <option value="medium">{props.t("riskMedium")}</option>
                  <option value="high">{props.t("riskHigh")}</option>
                </select>
              </label>
              <label className="field qs-filter-wide">
                {props.t("orderBy")}
                <select
                  name="sort_by"
                  autoComplete="off"
                  value={props.sortBy}
                  onChange={(e) => props.setSortBy(e.target.value as "ranking" | "price" | "duration" | "risk" | "freshness")}
                  className="qs-input"
                  data-ui="qs-filter-sort"
                >
                  <option value="ranking">{props.t("sortRanking")}</option>
                  <option value="price">{props.t("sortPrice")}</option>
                  <option value="duration">{props.t("sortDuration")}</option>
                  <option value="risk">{props.t("sortRisk")}</option>
                  <option value="freshness">{props.t("sortFreshness")}</option>
                </select>
              </label>
            </div>
          </section>

          <section className="qs-filter-group qs-filter-group-guided qs-filter-group-partial" data-ui="qs-filter-experimental">
            <div className="qs-filter-section-head">
              <div>
                <span className="qs-filter-eyebrow">{props.t("filterPartialSupport")}</span>
                <h3>{props.t("stopsTitle")}</h3>
                <p>{props.t("stopsSubtitle")}</p>
              </div>
              <button type="button" className="btn-ghost btn-compact" onClick={props.onResetExperimental} data-ui="qs-filter-reset-experimental">
                {props.t("resetGroup")}
              </button>
            </div>
            <div className="qs-filter-grid">
              <label className="qs-check" data-ui="qs-filter-include-stops">
                <input
                  type="checkbox"
                  name="include_stops"
                  checked={props.includeStops}
                  onChange={(e) => props.setIncludeStops(e.target.checked)}
                />
                <span className="qs-check-ui" aria-hidden="true">
                  <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                    <path d="M5.5 12.5 10 17l8.5-9" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
                {props.t("includeStops")}
              </label>
              <label className="field">
                {props.t("maxStops")}
                <select
                  name="max_stops"
                  autoComplete="off"
                  value={props.maxStops}
                  onChange={(e) => props.setMaxStops(Number(e.target.value))}
                  className="qs-input"
                  disabled={!props.includeStops}
                  data-ui="qs-filter-max-stops"
                >
                  <option value={1}>{props.t("stopsOne")}</option>
                  <option value={2}>{props.t("stopsTwo")}</option>
                </select>
              </label>
              <label className="field">
                {props.t("bufferMin")}
                <input
                  type="number"
                  min={0}
                  step={1}
                  name="buffer_min"
                  autoComplete="off"
                  value={props.bufferMin}
                  onChange={(e) => props.setBufferMin(e.target.value)}
                  placeholder="45"
                  className="qs-input"
                  disabled={!props.includeStops}
                  aria-invalid={Boolean(props.fieldErrors.buffer_min)}
                  data-ui="qs-filter-buffer-min"
                />
                {props.fieldErrors.buffer_min ? <small className="qs-error">{props.fieldErrors.buffer_min}</small> : null}
                <small className="muted">{props.t("bufferMinHint")}</small>
              </label>
            </div>
            <div className="qs-warning qs-warning-warm">{props.t("selfConnectWarning")}</div>
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
    <section className="panel panel-soft qs-filter-console" data-ui="qs-filter-console">
      <div className="qs-filter-console-head">
        <div>
          <span className="qs-filter-eyebrow">{props.t("filterConsoleEyebrow")}</span>
          <h3>{props.t("filterConsoleTitle")}</h3>
          <p>{props.t("filterConsoleSubtitle")}</p>
        </div>
        <div className="qs-filter-console-actions">
          <span className="qs-filter-count" data-ui="qs-filter-count">
            {props.activeFiltersCount} {props.t("filterCountLabel")}
            {props.appliedFiltersCount > 0 ? ` / ${props.appliedFiltersCount}` : ""}
          </span>
          <button type="button" className="btn-ghost btn-compact" onClick={props.onOpenFilters} data-ui="qs-filter-open">
            {props.t("toolbarFilters")}
          </button>
        </div>
      </div>

      <div className="qs-filter-console-grid">
        <button type="button" className="qs-filter-console-card" onClick={props.onOpenFilters} data-ui="qs-filter-card-coverage" aria-label={props.t("coverageTitle")}>
          <span>{props.t("coverageTitle")}</span>
          <strong>{coverageSummary}</strong>
          <SupportBadge tone="live">{props.t("filterAppliedOnSearch")}</SupportBadge>
        </button>
        <button type="button" className="qs-filter-console-card" onClick={props.onOpenFilters} data-ui="qs-filter-card-timing" aria-label={props.t("timeTitle")}>
          <span>{props.t("timeTitle")}</span>
          <strong>{timingSummary}</strong>
          <SupportBadge tone="live">{props.strictFilters ? props.t("summaryStrictOn") : props.t("summaryStrictOff")}</SupportBadge>
        </button>
        <button type="button" className="qs-filter-console-card" onClick={props.onOpenFilters} data-ui="qs-filter-card-visible" aria-label={props.t("visibleResultsTitle")}>
          <span>{props.t("visibleResultsTitle")}</span>
          <strong>{visibleSummary}</strong>
          <SupportBadge>{props.t("filterAppliedToResults")}</SupportBadge>
        </button>
        <button type="button" className="qs-filter-console-card" onClick={props.onOpenFilters} data-ui="qs-filter-card-experimental" aria-label={props.t("stopsTitle")}>
          <span>{props.t("stopsTitle")}</span>
          <strong>{experimentalSummary}</strong>
          <SupportBadge tone="partial">{props.t("filterPartialSupport")}</SupportBadge>
        </button>
      </div>

      {props.pendingSearchChanges ? (
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

      {props.activeChips.length > 0 ? (
        <div className="qs-active-chips qs-filter-console-chips" data-ui="qs-filter-active-chips">
          <span className="muted">{props.t("toolbarActiveFilters")}</span>
          <button type="button" className="btn-ghost qs-reset-all-inline" onClick={props.onClearAllFilters}>
            {props.t("resetAll")}
          </button>
          {props.activeChips.map((chip) => (
            <button
              key={chip.id}
              type="button"
              className="qs-chip"
              onClick={chip.onClear}
              aria-label={props.t("ariaRemoveFilter").replace("{value}", chip.label)}
              data-ui={`qs-filter-chip-${chip.id}`}
            >
              <span>{chip.label}</span>
              <QuickSearchCloseIcon />
            </button>
          ))}
        </div>
      ) : (
        <p className="panel-note qs-filter-console-empty">{props.t("filterNoActive")}</p>
      )}

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
    && prev.radiusActive === next.radiusActive
    && prev.radiusKm === next.radiusKm
    && prev.priceMin === next.priceMin
    && prev.priceMax === next.priceMax
    && prev.durationMax === next.durationMax
    && prev.riskFilter === next.riskFilter
    && prev.sortBy === next.sortBy
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
    && prev.formatRiskLabel === next.formatRiskLabel
    && prev.setRadiusKm === next.setRadiusKm
    && prev.setPriceMin === next.setPriceMin
    && prev.setPriceMax === next.setPriceMax
    && prev.setDurationMax === next.setDurationMax
    && prev.setRiskFilter === next.setRiskFilter
    && prev.setSortBy === next.setSortBy
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
    && prev.onApplyAndSearch === next.onApplyAndSearch
    && prev.onApplyPreferences === next.onApplyPreferences
    && prev.onClearAllFilters === next.onClearAllFilters
    && prev.onResetCoverage === next.onResetCoverage
    && prev.onResetTiming === next.onResetTiming
    && prev.onResetVisible === next.onResetVisible
    && prev.onResetExperimental === next.onResetExperimental
    && prev.onPresetDirect === next.onPresetDirect
    && prev.onPresetOriginNearby === next.onPresetOriginNearby
    && prev.onPresetBothNearby === next.onPresetBothNearby
    && prev.onPresetRegional === next.onPresetRegional
  );
}

export const QuickSearchFilterConsole = memo(QuickSearchFilterConsoleInner, areFilterConsolePropsEqual);
