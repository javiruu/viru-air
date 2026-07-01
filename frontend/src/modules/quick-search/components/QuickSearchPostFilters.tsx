"use client";

import React, { useState } from "react";

import { QuickSearchFieldErrors } from "@/modules/quick-search/types";
import { QuickSearchCopyKey } from "@/modules/shared/quickSearchCopy";

type Props = {
  visible: boolean;
  priceMin: string;
  priceMax: string;
  durationMax: string;
  sortBy: "ranking" | "price" | "duration" | "freshness";
  fieldErrors: QuickSearchFieldErrors;
  t: (key: QuickSearchCopyKey) => string;
  setPriceMin: (value: string) => void;
  setPriceMax: (value: string) => void;
  setDurationMax: (value: string) => void;
  setSortBy: (value: "ranking" | "price" | "duration" | "freshness") => void;
};

export function QuickSearchPostFilters(props: Props) {
  const [moreOpen, setMoreOpen] = useState(false);

  if (!props.visible) return null;

  const hasAdvancedFilters = Boolean(props.priceMin || props.priceMax || props.durationMax);

  return (
    <div className="qs-post-filters" data-ui="qs-post-filters">
      <div className="qs-post-filters__head">
        <span className="qs-filter-eyebrow">{props.t("filterAppliedToResults")}</span>
      </div>
      <div className="qs-post-filters__grid">
        <label className="field qs-post-filters-sort">
          <span className="qs-filter-label">{props.t("orderBy")}</span>
          <select
            name="sort_by"
            autoComplete="off"
            value={props.sortBy}
            onChange={(e) => props.setSortBy(e.target.value as "ranking" | "price" | "duration" | "freshness")}
            className="qs-input"
            data-ui="qs-post-filter-sort"
          >
            <option value="ranking">{props.t("sortRanking")}</option>
            <option value="price">{props.t("sortPrice")}</option>
            <option value="duration">{props.t("sortDuration")}</option>
            <option value="freshness">{props.t("sortFreshness")}</option>
          </select>
        </label>

        <button
          type="button"
          className="btn-ghost btn-compact qs-post-filters-toggle"
          aria-expanded={moreOpen}
          onClick={() => setMoreOpen((v) => !v)}
          data-ui="qs-post-filters-toggle"
        >
          <svg className="qs-inline-icon" viewBox="0 0 24 24" aria-hidden="true" width="16" height="16">
            <path
              d={moreOpen ? "M18 15l-6-6-6 6" : "M6 9l6 6 6-6"}
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          {props.t("moreOptions")}
          {hasAdvancedFilters ? <span className="qs-active-dot" aria-label="Filtro activo" /> : null}
        </button>
      </div>

      {moreOpen ? (
        <div className="qs-post-filters__more" data-ui="qs-post-filters-more">
          <div className="qs-post-filters__more-grid">
            <label className="field">
              <span className="qs-filter-label">{props.t("priceMin")}</span>
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
                data-ui="qs-post-filter-price-min"
              />
              {props.fieldErrors.price_min ? <small className="qs-error">{props.fieldErrors.price_min}</small> : null}
            </label>
            <label className="field">
              <span className="qs-filter-label">{props.t("priceMax")}</span>
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
                data-ui="qs-post-filter-price-max"
              />
              {props.fieldErrors.price_max ? <small className="qs-error">{props.fieldErrors.price_max}</small> : null}
            </label>
            <label className="field">
              <span className="qs-filter-label">{props.t("durationMax")}</span>
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
                data-ui="qs-post-filter-duration-max"
              />
              {props.fieldErrors.duration_max ? <small className="qs-error">{props.fieldErrors.duration_max}</small> : null}
            </label>
          </div>
        </div>
      ) : null}
    </div>
  );
}
