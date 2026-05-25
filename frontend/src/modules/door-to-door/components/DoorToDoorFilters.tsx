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
      <div className="d2d-filter-section d2d-filter-section-params">
        <h3 className="d2d-filter-section-title">{t("doorToDoor.filters.parametersSection")}</h3>
        <div className="d2d-filter-grid">
          <label className="field">
            <span className="d2d-filter-label">{t("doorToDoor.filters.sortBy")}</span>
            <select className="prefs-control" value={preferences.sort_by} onChange={(event) => patch({ sort_by: event.target.value as DoorToDoorSortBy })}>
              <option value="best_balance">{t("doorToDoor.filters.bestBalance")}</option>
              <option value="cheapest">{t("doorToDoor.filters.cheapest")}</option>
              <option value="lowest_risk">{t("doorToDoor.filters.lowestRisk")}</option>
              <option value="fastest">{t("doorToDoor.filters.fastest")}</option>
              <option value="fewest_changes">{t("doorToDoor.filters.fewestChanges")}</option>
            </select>
          </label>
          <label className="field">
            <span className="d2d-filter-label">{t("doorToDoor.filters.minBuffer")}</span>
            <div className="d2d-input-with-suffix">
              <input className="prefs-control" type="number" min={45} max={360} value={preferences.min_airport_buffer_minutes} onChange={(event) => patch({ min_airport_buffer_minutes: Number(event.target.value) })} />
              <span className="d2d-input-suffix" aria-hidden="true">min</span>
            </div>
          </label>
          <label className="field">
            <span className="d2d-filter-label">{t("doorToDoor.filters.passengers")}</span>
            <input className="prefs-control" type="number" min={1} max={9} value={preferences.passengers} onChange={(event) => patch({ passengers: Number(event.target.value) })} />
          </label>
          <label className="field">
            <span className="d2d-filter-label">{t("doorToDoor.filters.maxPrice")}</span>
            <input className="prefs-control" type="number" min={0} value={preferences.max_price ?? ""} placeholder="80" onChange={(event) => patch({ max_price: event.target.value === "" ? null : Number(event.target.value) })} />
          </label>
          <label className="field">
            <span className="d2d-filter-label-with-help">
              <span className="d2d-filter-label">{t("doorToDoor.filters.luggage")}</span>
              <span className="d2d-filter-help" title={t("doorToDoor.filters.maxPriceHint")} aria-label={t("doorToDoor.filters.luggageHelpAria")}>?</span>
            </span>
            <select className="prefs-control" value={preferences.luggage} onChange={(event) => patch({ luggage: event.target.value as DoorToDoorPreferences["luggage"] })}>
              <option value="backpack">{t("doorToDoor.filters.backpack")}</option>
              <option value="cabin">{t("doorToDoor.filters.cabin")}</option>
              <option value="checked">{t("doorToDoor.filters.checked")}</option>
            </select>
          </label>
        </div>
      </div>
      <div className="d2d-filter-section d2d-filter-section-transport">
        <h3 className="d2d-filter-section-title">{t("doorToDoor.filters.transportSection")}</h3>
        <div className="d2d-toggle-row">
          <div className="field">
            <span className="d2d-filter-label">{t("doorToDoor.filters.publicOnly")}</span>
            <button
              type="button"
              role="switch"
              aria-checked={preferences.public_transport_only}
              aria-label={t("doorToDoor.filters.publicOnly")}
              className={`prefs-toggle ${preferences.public_transport_only ? "is-on" : ""}`}
              onClick={() => patch({ public_transport_only: !preferences.public_transport_only })}
            >
              <span className="prefs-toggle-track" aria-hidden="true">
                <span className="prefs-toggle-knob" />
              </span>
              <span className="sr-only">{preferences.public_transport_only ? t("doorToDoor.filters.enabled") : t("doorToDoor.filters.disabled")}</span>
            </button>
          </div>
          <div className="field">
            <span className="d2d-filter-label">{t("doorToDoor.filters.rideshare")}</span>
            <button
              type="button"
              role="switch"
              aria-checked={preferences.allow_rideshare}
              aria-label={t("doorToDoor.filters.rideshare")}
              className={`prefs-toggle ${preferences.allow_rideshare ? "is-on" : ""}`}
              onClick={() => patch({ allow_rideshare: !preferences.allow_rideshare })}
            >
              <span className="prefs-toggle-track" aria-hidden="true">
                <span className="prefs-toggle-knob" />
              </span>
              <span className="sr-only">{preferences.allow_rideshare ? t("doorToDoor.filters.enabled") : t("doorToDoor.filters.disabled")}</span>
            </button>
          </div>
          <div className="field">
            <span className="d2d-filter-label">{t("doorToDoor.filters.shuttle")}</span>
            <button
              type="button"
              role="switch"
              aria-checked={preferences.allow_shuttle}
              aria-label={t("doorToDoor.filters.shuttle")}
              className={`prefs-toggle ${preferences.allow_shuttle ? "is-on" : ""}`}
              onClick={() => patch({ allow_shuttle: !preferences.allow_shuttle })}
            >
              <span className="prefs-toggle-track" aria-hidden="true">
                <span className="prefs-toggle-knob" />
              </span>
              <span className="sr-only">{preferences.allow_shuttle ? t("doorToDoor.filters.enabled") : t("doorToDoor.filters.disabled")}</span>
            </button>
          </div>
        </div>
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
