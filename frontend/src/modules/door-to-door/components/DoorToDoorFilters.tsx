import React from "react";

import { useI18n } from "@/i18n";
import type { DoorToDoorPreferences, DoorToDoorSortBy } from "@/modules/door-to-door/types";

export function DoorToDoorFilters({
  preferences,
  onChange,
  embedded = false,
}: {
  preferences: DoorToDoorPreferences;
  onChange: (next: DoorToDoorPreferences) => void;
  embedded?: boolean;
}) {
  const { t } = useI18n();
  function patch(next: Partial<DoorToDoorPreferences>) {
    onChange({ ...preferences, ...next });
  }
  const content = (
    <>
      <div className="d2d-filter-grid">
        <label className="field">
          {t("doorToDoor.filters.sortBy")}
          <select className="prefs-control" value={preferences.sort_by} onChange={(event) => patch({ sort_by: event.target.value as DoorToDoorSortBy })}>
            <option value="best_balance">{t("doorToDoor.filters.bestBalance")}</option>
            <option value="cheapest">{t("doorToDoor.filters.cheapest")}</option>
            <option value="lowest_risk">{t("doorToDoor.filters.lowestRisk")}</option>
            <option value="fastest">{t("doorToDoor.filters.fastest")}</option>
            <option value="fewest_changes">{t("doorToDoor.filters.fewestChanges")}</option>
          </select>
        </label>
        <label className="field">
          {t("doorToDoor.filters.minBuffer")}
          <input className="prefs-control" type="number" min={45} max={360} value={preferences.min_airport_buffer_minutes} onChange={(event) => patch({ min_airport_buffer_minutes: Number(event.target.value) })} />
        </label>
        <label className="field">
          {t("doorToDoor.filters.passengers")}
          <input className="prefs-control" type="number" min={1} max={9} value={preferences.passengers} onChange={(event) => patch({ passengers: Number(event.target.value) })} />
        </label>
        <label className="field">
          {t("doorToDoor.filters.maxPrice")}
          <input className="prefs-control" type="number" min={0} value={preferences.max_price ?? ""} placeholder="80" onChange={(event) => patch({ max_price: event.target.value === "" ? null : Number(event.target.value) })} />
          <span className="field-hint">{t("doorToDoor.filters.maxPriceHint")}</span>
        </label>
        <label className="field">
          {t("doorToDoor.filters.luggage")}
          <select className="prefs-control" value={preferences.luggage} onChange={(event) => patch({ luggage: event.target.value as DoorToDoorPreferences["luggage"] })}>
            <option value="backpack">{t("doorToDoor.filters.backpack")}</option>
            <option value="cabin">{t("doorToDoor.filters.cabin")}</option>
            <option value="checked">{t("doorToDoor.filters.checked")}</option>
          </select>
        </label>
      </div>
      <div className="d2d-toggle-row">
        <button type="button" className={`btn-ghost btn-compact ${preferences.public_transport_only ? "is-active" : ""}`} onClick={() => patch({ public_transport_only: !preferences.public_transport_only })}>{t("doorToDoor.filters.publicOnly")}</button>
        <button type="button" className={`btn-ghost btn-compact ${preferences.allow_rideshare ? "is-active" : ""}`} onClick={() => patch({ allow_rideshare: !preferences.allow_rideshare })}>{t("doorToDoor.filters.rideshare")}</button>
        <button type="button" className={`btn-ghost btn-compact ${preferences.allow_shuttle ? "is-active" : ""}`} onClick={() => patch({ allow_shuttle: !preferences.allow_shuttle })}>{t("doorToDoor.filters.shuttle")}</button>
      </div>
    </>
  );

  if (embedded) return <div className="d2d-filters-content">{content}</div>;

  return (
    <section className="panel panel-soft d2d-filters">
      <div className="panel-header">
        <h2 className="panel-title">{t("doorToDoor.filters.title")}</h2>
      </div>
      {content}
    </section>
  );
}
