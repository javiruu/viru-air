"use client";

import { useI18n } from "@/i18n";

import type { HotelCompSetDetailOut, HotelCompSetOut, HotelSearchOut } from "../types";

export function HotelCompSetPanel({
  compSets,
  selectedCompSet,
  hotels,
  selectedHotelId,
  onCreateCompSet,
  onSelectCompSet,
  onAddMember,
}: {
  compSets: HotelCompSetOut[];
  selectedCompSet: HotelCompSetDetailOut | null;
  hotels: HotelSearchOut[];
  selectedHotelId: string | null;
  onCreateCompSet: (name: string, anchorHotelId: string) => void;
  onSelectCompSet: (compSetId: string) => void;
  onAddMember: (compSetId: string, hotelId: string) => void;
}) {
  const { t } = useI18n();

  return (
    <section className="panel panel-soft hotel-comp-set-panel">
      <div className="panel-header">
        <h2 className="panel-title">{t("hotels.compSet.title")}</h2>
        <span className="status-pill info">{t("hotels.compSet.badge")}</span>
      </div>
      <div className="section-gap-sm hotel-comp-set-actions">
        <button
          type="button"
          className="btn-secondary btn-compact"
          disabled={!selectedHotelId}
          onClick={() => selectedHotelId && onCreateCompSet(t("hotels.compSet.defaultName"), selectedHotelId)}
        >
          {t("hotels.compSet.create")}
        </button>
      </div>
      <div className="hotel-comp-set-list section-gap-sm">
        {compSets.map((compSet) => (
          <button key={compSet.id} type="button" className={`hotel-comp-set-item${selectedCompSet?.id === compSet.id ? " is-active" : ""}`} onClick={() => onSelectCompSet(compSet.id)}>
            {compSet.name}
          </button>
        ))}
        {compSets.length === 0 ? <p className="panel-note">{t("hotels.compSet.empty")}</p> : null}
      </div>
      {selectedCompSet ? (
        <div className="section-gap-sm">
          <p className="panel-note">{t("hotels.compSet.members")}: {selectedCompSet.members.length}</p>
          <div className="hotel-comp-set-actions">
            <button
              type="button"
              className="btn-ghost btn-compact"
              disabled={!selectedHotelId}
              onClick={() => selectedHotelId && onAddMember(selectedCompSet.id, selectedHotelId)}
            >
              {t("hotels.compSet.addSelected")}
            </button>
          </div>
        </div>
      ) : null}
      <div className="section-gap-sm">
        <p className="panel-note">{t("hotels.compSet.availableHotels")}: {hotels.length}</p>
      </div>
    </section>
  );
}

export function HotelEmptyState() {
  const { t } = useI18n();
  return (
    <section className="panel panel-soft hotel-empty-state">
      <h2 className="panel-title">{t("hotels.empty.title")}</h2>
      <p className="panel-subtitle">{t("hotels.empty.body")}</p>
    </section>
  );
}

