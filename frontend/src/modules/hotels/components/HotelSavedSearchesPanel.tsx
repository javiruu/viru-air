"use client";

import { useState } from "react";
import { useI18n } from "@/i18n";
import type { HotelSavedSearchOut } from "../types";

export function HotelSavedSearchesPanel({
  searches,
  loading,
  error,
  busyId,
  saving,
  canSave,
  onSave,
  onRestore,
  onPause,
  onDelete,
}: {
  searches: HotelSavedSearchOut[];
  loading: boolean;
  error: string | null;
  busyId: string | null;
  saving: boolean;
  canSave: boolean;
  onSave: (label?: string) => Promise<void>;
  onRestore: (search: HotelSavedSearchOut) => void;
  onPause: (id: string, status: "active" | "paused") => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  const { t } = useI18n();
  const [label, setLabel] = useState("");

  return (
    <section className="panel panel-soft hotel-saved-searches-panel">
      <div className="panel-header">
        <h2 className="panel-title">{t("hotels.savedSearches.title")}</h2>
        <span className="status-pill info">{searches.length}</span>
      </div>
      {canSave ? (
        <div className="hotel-saved-search-create section-gap-sm">
          <input
            value={label}
            onChange={(event) => setLabel(event.target.value)}
            maxLength={120}
            placeholder={t("hotels.savedSearches.labelPlaceholder")}
            aria-label={t("hotels.savedSearches.label")}
          />
          <button type="button" className="btn-ghost btn-compact" disabled={saving} onClick={() => void onSave(label)}>
            {saving ? t("shared.states.loading") : t("hotels.savedSearches.save")}
          </button>
        </div>
      ) : null}
      {loading ? <p className="panel-note">{t("shared.states.loading")}</p> : null}
      {error ? <p className="panel-note" role="alert">{t("hotels.savedSearches.loadError")}</p> : null}
      {!loading && !error && searches.length === 0 ? (
        <p className="panel-note">{t("hotels.savedSearches.empty")}</p>
      ) : null}
      {!loading && !error && searches.length > 0 ? (
        <div className="hotel-saved-search-list section-gap-sm">
          {searches.map((search) => (
            <article key={search.id} className="list-row hotel-saved-search-item">
              <div>
                <strong>{search.label || t("hotels.savedSearches.untitled")}</strong>
                <p className="panel-note">{search.status === "paused" ? t("hotels.savedSearches.paused") : t("hotels.savedSearches.active")}</p>
              </div>
              <div className="hotel-tracked-offer-actions">
                <button type="button" className="btn-ghost btn-compact" onClick={() => onRestore(search)}>
                  {t("hotels.savedSearches.restore")}
                </button>
                <button
                  type="button"
                  className="btn-ghost btn-compact"
                  disabled={busyId === search.id}
                  onClick={() => void onPause(search.id, search.status === "paused" ? "active" : "paused")}
                >
                  {search.status === "paused" ? t("hotels.savedSearches.resume") : t("hotels.savedSearches.pause")}
                </button>
                <button type="button" className="btn-ghost btn-compact" disabled={busyId === search.id} onClick={() => void onDelete(search.id)}>
                  {t("hotels.savedSearches.delete")}
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
