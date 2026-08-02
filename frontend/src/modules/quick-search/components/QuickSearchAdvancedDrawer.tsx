import React, { memo, RefObject } from "react";
import { createPortal } from "react-dom";

import { QuickSearchFieldErrors } from "@/modules/quick-search/types";
import { QuickSearchCopyKey } from "@/modules/shared/quickSearchCopy";
import { useEscapeClose } from "@/modules/shared/useEscapeClose";

type ActiveChip = {
  id: string;
  label: string;
  onClear: () => void;
};

type AdvancedDrawerProps = {
  isOpen: boolean;
  onClose: () => void;
  closeRef?: RefObject<HTMLButtonElement | null>;
  
  departAfter: string;
  departBefore: string;
  strictFilters: boolean;
  includeStops: boolean;
  maxStops: number;
  bufferMin: string;
  excludeOrigins: string[];
  excludeDestinations: string[];
  excludeOriginInput: string;
  excludeDestinationInput: string;
  fieldErrors: QuickSearchFieldErrors;
  t: (key: QuickSearchCopyKey) => string;
  
  setDepartAfter: (value: string) => void;
  setDepartBefore: (value: string) => void;
  setStrictFilters: (value: boolean) => void;
  setIncludeStops: (value: boolean) => void;
  setMaxStops: (value: number) => void;
  setBufferMin: (value: string) => void;
  setExcludeOriginInput: (value: string) => void;
  setExcludeDestinationInput: (value: string) => void;
  addExcludeOrigin: () => void;
  addExcludeDestination: () => void;
  removeExcludeOrigin: (iata: string) => void;
  removeExcludeDestination: (iata: string) => void;
  onClearAll: () => void;
  onApplyAndSearch?: () => void;
  pendingSearchChanges?: boolean;
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

function QuickSearchAdvancedDrawerInner(props: AdvancedDrawerProps) {
  useEscapeClose(props.onClose, props.isOpen);
  if (!props.isOpen) return null;

  const drawer = (
    <>
      <button
        type="button"
        className="qs-filters-backdrop"
        aria-label={props.t("pickClose")}
        onClick={props.onClose}
      />
      <aside
        id="qs-advanced-drawer"
        role="dialog"
        aria-modal="true"
        aria-label={props.t("moreOptions")}
        className="panel panel-soft qs-filters-panel open"
        data-ui="qs-advanced-drawer"
      >
        <div className="qs-filters-header">
          <div>
            <span className="qs-filter-eyebrow">{props.t("filterConsoleEyebrow")}</span>
            <h2>{props.t("moreOptions")}</h2>
            <span className="muted">{props.t("filterConsoleEyebrow")}</span>
          </div>
          <button
            type="button"
            className="btn-ghost qs-filters-close"
            aria-label={props.t("pickClose")}
            ref={props.closeRef}
            onClick={props.onClose}
          >
            {props.t("pickClose")}
          </button>
        </div>

        <div className="qs-filter-console-drawer">
          
          <section className="qs-filter-group qs-filter-group-guided" data-ui="qs-filter-stops">
            <div className="qs-filter-section-head">
              <div>
                <span className="qs-filter-eyebrow">{props.t("filterAppliedOnSearch")}</span>
                <h3>{props.t("separateFlightsTitle")}</h3>
                <p>{props.t("separateFlightsBody")}</p>
              </div>
            </div>
            <div className="qs-filter-grid">
              <label className="qs-check qs-filter-wide" data-ui="qs-filter-include-stops">
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
              {props.includeStops && (
                <>
                  <label className="field">
                    {props.t("maxStops")}
                    <select
                      name="max_stops"
                      value={props.maxStops}
                      onChange={(e) => props.setMaxStops(Number(e.target.value))}
                      className="qs-input"
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
                      name="buffer_min"
                      autoComplete="off"
                      min="30"
                      max="1440"
                      value={props.bufferMin}
                      onChange={(e) => props.setBufferMin(e.target.value)}
                      placeholder="45"
                      className="qs-input"
                      aria-invalid={Boolean(props.fieldErrors.buffer_min)}
                      data-ui="qs-filter-buffer-min"
                    />
                    {props.fieldErrors.buffer_min ? <small className="qs-error">{props.fieldErrors.buffer_min}</small> : null}
                  </label>
                </>
              )}
            </div>
            {props.includeStops && (
              <div className="qs-warning">
                {props.t("selfConnectWarningDetail")}
              </div>
            )}
          </section>

          <section className="qs-filter-group qs-filter-group-guided" data-ui="qs-filter-exclusions">
            <div className="qs-filter-section-head">
              <div>
                <span className="qs-filter-eyebrow">{props.t("filterAppliedOnSearch")}</span>
                <h3>{props.t("exclusionsTitle")}</h3>
                <p>{props.t("exclusionsBody")}</p>
              </div>
            </div>
            <div className="qs-filter-grid">
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
                <h3>Horarios de salida</h3>
                <p>Limita la franja horaria en la que quieres volar.</p>
              </div>
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

        </div>

        <div className="qs-filter-actions">
          <button type="button" className="btn-ghost qs-reset-all" onClick={props.onClearAll} data-ui="qs-filter-reset-advanced">
            {props.t("resetAll")}
          </button>
          {props.pendingSearchChanges && props.onApplyAndSearch ? (
            <button type="button" className="btn-search" onClick={props.onApplyAndSearch} data-ui="qs-filter-apply-search">
              {props.t("applyAndSearch")}
            </button>
          ) : null}
        </div>
      </aside>
    </>
  );

  return typeof document !== "undefined" ? createPortal(drawer, document.body) : null;
}

function areAdvancedDrawerPropsEqual(prev: AdvancedDrawerProps, next: AdvancedDrawerProps): boolean {
  return (
    prev.isOpen === next.isOpen
    && prev.departAfter === next.departAfter
    && prev.departBefore === next.departBefore
    && prev.strictFilters === next.strictFilters
    && prev.includeStops === next.includeStops
    && prev.maxStops === next.maxStops
    && prev.bufferMin === next.bufferMin
    && prev.excludeOrigins === next.excludeOrigins
    && prev.excludeDestinations === next.excludeDestinations
    && prev.excludeOriginInput === next.excludeOriginInput
    && prev.excludeDestinationInput === next.excludeDestinationInput
    && prev.fieldErrors === next.fieldErrors
    && prev.pendingSearchChanges === next.pendingSearchChanges
  );
}

export const QuickSearchAdvancedDrawer = memo(QuickSearchAdvancedDrawerInner, areAdvancedDrawerPropsEqual);
