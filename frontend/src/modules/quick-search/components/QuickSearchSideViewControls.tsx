"use client";

import type { QuickSearchSortBy, QuickSearchVisibleFiltersState } from "@/modules/quick-search/types";
import type { QuickSearchCopyKey } from "@/modules/shared/quickSearchCopy";

type Props = {
  title: string;
  subtitle: string;
  state: QuickSearchVisibleFiltersState;
  t: (key: QuickSearchCopyKey) => string;
  onChange: (patch: Partial<QuickSearchVisibleFiltersState>) => void;
  onReset: () => void;
};

export function QuickSearchSideViewControls({ title, subtitle, state, t, onChange, onReset }: Props) {
  return (
    <section className="qs-dual-view-controls" aria-label={title}>
      <div className="qs-dual-view-controls__head">
        <div>
          <strong>{title}</strong>
          <p>{subtitle}</p>
        </div>
        <button type="button" className="btn-ghost btn-compact" onClick={onReset}>
          {t("resetGroup")}
        </button>
      </div>

      <div className="qs-dual-view-controls__grid">
        <label className="field">
          {t("priceMin")}
          <input
            type="number"
            min={0}
            step={1}
            value={state.priceMin}
            onChange={(event) => onChange({ priceMin: event.target.value })}
            className="qs-input"
          />
        </label>

        <label className="field">
          {t("priceMax")}
          <input
            type="number"
            min={0}
            step={1}
            value={state.priceMax}
            onChange={(event) => onChange({ priceMax: event.target.value })}
            className="qs-input"
          />
        </label>

        <label className="field">
          {t("durationMax")}
          <input
            type="number"
            min={1}
            step={1}
            value={state.durationMax}
            onChange={(event) => onChange({ durationMax: event.target.value })}
            className="qs-input"
          />
        </label>

        <label className="field">
          {t("orderBy")}
          <select
            value={state.sortBy}
            onChange={(event) => onChange({ sortBy: event.target.value as QuickSearchSortBy })}
            className="qs-input"
          >
            <option value="ranking">{t("sortRanking")}</option>
            <option value="price">{t("sortPrice")}</option>
            <option value="duration">{t("sortDuration")}</option>
            <option value="freshness">{t("sortFreshness")}</option>
          </select>
        </label>
      </div>
    </section>
  );
}
