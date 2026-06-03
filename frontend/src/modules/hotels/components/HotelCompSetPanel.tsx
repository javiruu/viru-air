"use client";

import { useI18n } from "@/i18n";

import type { HotelCompSetDetailOut, HotelCompSetOut, HotelDetailOut, HotelNearbySuggestionOut, HotelSearchOut } from "../types";

export function HotelCompSetPanel({
  compSets,
  selectedCompSet,
  anchorDetail,
  anchorLoading,
  anchorError,
  hotels,
  selectedHotelId,
  nearbySuggestions,
  nearbyLoading,
  nearbyMessage,
  onCreateCompSet,
  onSelectCompSet,
  onAddMember,
  onDeleteMember,
}: {
  compSets: HotelCompSetOut[];
  selectedCompSet: HotelCompSetDetailOut | null;
  anchorDetail: HotelDetailOut | null;
  anchorLoading: boolean;
  anchorError: string | null;
  hotels: HotelSearchOut[];
  selectedHotelId: string | null;
  nearbySuggestions: HotelNearbySuggestionOut[];
  nearbyLoading: boolean;
  nearbyMessage: string | null;
  onCreateCompSet: (name: string, anchorHotelId: string) => void;
  onSelectCompSet: (compSetId: string) => void;
  onAddMember: (compSetId: string, hotelId: string) => void;
  onDeleteMember: (compSetId: string, memberId: string) => void;
}) {
  const { t } = useI18n();
  const selectedHotelAlreadyInCompSet = selectedCompSet
    ? selectedHotelId === selectedCompSet.anchor_hotel_id || selectedCompSet.members.some((member) => member.hotel_id === selectedHotelId)
    : false;

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
          <button
            key={compSet.id}
            type="button"
            className={`hotel-comp-set-item${selectedCompSet?.id === compSet.id ? " is-active" : ""}`}
            onClick={() => onSelectCompSet(compSet.id)}
          >
            {compSet.name}
          </button>
        ))}
        {compSets.length === 0 ? <p className="panel-note">{t("hotels.compSet.empty")}</p> : null}
      </div>
      {selectedCompSet ? (
        <div className="section-gap-sm hotel-comp-set-active">
          <div className="hotel-comp-set-summary">
            <div>
              <span className="hotel-comp-set-eyebrow">{t("hotels.compSet.activeLabel")}</span>
              <strong>{selectedCompSet.name}</strong>
              {anchorDetail ? (
                <p className="panel-note">
                  {t("hotels.compSet.anchor")}: {anchorDetail.canonical_name} · {anchorDetail.city}, {anchorDetail.country_code}
                </p>
              ) : null}
              {anchorLoading ? <p className="panel-note">{t("hotels.compSet.anchorLoading")}</p> : null}
              {anchorError ? <p className="panel-note">{anchorError}</p> : null}
            </div>
            <span className="status-pill info">{t("hotels.compSet.members")}: {selectedCompSet.members.length}</span>
          </div>
          <div className="hotel-comp-set-actions">
            <button
              type="button"
              className="btn-ghost btn-compact"
              disabled={!selectedHotelId || selectedHotelAlreadyInCompSet}
              onClick={() => selectedHotelId && onAddMember(selectedCompSet.id, selectedHotelId)}
            >
              {t("hotels.compSet.addSelected")}
            </button>
          </div>
          <section className="hotel-comp-set-members-section section-gap-sm">
            <div className="panel-header">
              <h3 className="panel-title">{t("hotels.compSet.membersTitle")}</h3>
              <span className="status-pill info">{selectedCompSet.members.length}</span>
            </div>
            {selectedCompSet.members.length === 0 ? (
              <p className="panel-note">{t("hotels.compSet.membersEmpty")}</p>
            ) : (
              <div className="hotel-comp-set-member-list">
                {selectedCompSet.members.map((member) => {
                  const memberHotel = hotels.find((h) => h.id === member.hotel_id);
                  return (
                    <article key={member.id} className="list-row hotel-comp-set-member-item">
                      <div className="hotel-comp-set-member-copy">
                        <strong>{memberHotel?.canonical_name || member.hotel_id}</strong>
                        {memberHotel ? <p className="panel-note">{memberHotel.city}, {memberHotel.country_code}</p> : null}
                      </div>
                      <button
                        type="button"
                        className="btn-ghost btn-compact"
                        onClick={() => onDeleteMember(selectedCompSet.id, member.id)}
                      >
                        {t("hotels.compSet.removeMember")}
                      </button>
                    </article>
                  );
                })}
              </div>
            )}
          </section>
          {selectedHotelAlreadyInCompSet ? <p className="panel-note">{t("hotels.compSet.addSelectedDisabled")}</p> : null}
          <section className="hotel-nearby-suggestions section-gap-sm">
            <div className="panel-header">
              <h3 className="panel-title">{t("hotels.compSet.nearbyTitle")}</h3>
              <span className="status-pill info">{nearbySuggestions.length}</span>
            </div>
            <p className="panel-note">{t("hotels.compSet.nearbyHint")}</p>
            {nearbyLoading ? <p className="panel-note">{t("shared.states.loading")}</p> : null}
            {nearbyMessage ? <p className="panel-note">{nearbyMessage}</p> : null}
            {!nearbyLoading && !nearbyMessage ? (
              <div className="hotel-nearby-list">
                {nearbySuggestions.map((suggestion) => (
                  <article key={suggestion.hotel_id} className="hotel-nearby-item">
                    <div className="hotel-nearby-copy">
                      <strong>{suggestion.canonical_name}</strong>
                      <p className="panel-note">
                        {suggestion.city}, {suggestion.country_code}
                      </p>
                      <p className="panel-note">{suggestion.stars ? `${suggestion.stars}\u2605` : t("hotels.card.noStars")}</p>
                    </div>
                    <div className="hotel-nearby-actions">
                      <span className="status-pill info">
                        {t("hotels.compSet.nearbyDistance", { distance: suggestion.distance_km.toFixed(1) })}
                      </span>
                      <button
                        type="button"
                        className="btn-ghost btn-compact"
                        onClick={() => onAddMember(selectedCompSet.id, suggestion.hotel_id)}
                      >
                        {t("hotels.compSet.addNearby")}
                      </button>
                    </div>
                  </article>
                ))}
                {nearbySuggestions.length === 0 ? <p className="panel-note">{t("hotels.compSet.nearbyEmpty")}</p> : null}
              </div>
            ) : null}
          </section>
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
