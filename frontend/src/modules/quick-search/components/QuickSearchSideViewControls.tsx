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
        {state.sortBy !== "price" ? (
          <button type="button" className="btn-ghost btn-compact" onClick={onReset}>
            {t("resetGroup")}
          </button>
        ) : null}
      </div>

      <div className="qs-dual-view-controls__grid">
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
