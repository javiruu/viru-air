"use client";

import { useI18n } from "@/i18n";

import type { HotelWatchlistEntry } from "../types";

function formatCreatedAt(value: string, localeTag: string): string {
  return new Intl.DateTimeFormat(localeTag, {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function fallbackHotelId(hotelId: string): string {
  if (hotelId.length <= 14) return hotelId;
  return `${hotelId.slice(0, 8)}...${hotelId.slice(-4)}`;
}

export function HotelWatchlistPanel({
  entries,
  loading,
  error,
  busyHotelIds,
  onRemove,
}: {
  entries: HotelWatchlistEntry[];
  loading: boolean;
  error: string | null;
  busyHotelIds: string[];
  onRemove: (itemId: string, hotelId: string) => void;
}) {
  const { t, localeTag } = useI18n();

  return (
    <section className="panel panel-soft hotel-watchlist-panel">
      <div className="panel-header">
        <h2 className="panel-title">{t("hotels.watchlist.title")}</h2>
        <span className="status-pill info">{entries.length}</span>
      </div>

      {loading ? <p className="panel-note section-gap-sm">{t("hotels.watchlist.loading")}</p> : null}
      {error ? <p className="panel-note section-gap-sm">{error}</p> : null}
      {!loading && !error && entries.length === 0 ? <p className="panel-note section-gap-sm">{t("hotels.watchlist.empty")}</p> : null}

      {!loading && entries.length > 0 ? (
        <div className="hotel-watchlist-list section-gap-sm">
          {entries.map(({ item, hotel, detailUnavailable }) => {
            const busy = busyHotelIds.includes(item.hotel_id);
            const title = hotel?.canonical_name || item.label || fallbackHotelId(item.hotel_id);
            const subtitle = hotel ? `${hotel.city}, ${hotel.country_code}` : item.label && item.label !== title ? item.label : null;

            return (
              <article key={item.id} className="list-row hotel-watchlist-item">
                <div className="hotel-watchlist-copy">
                  <strong>{title}</strong>
                  {subtitle ? <p className="panel-note">{subtitle}</p> : null}
                  <p className="panel-note">{t("hotels.watchlist.savedAt", { date: formatCreatedAt(item.created_at, localeTag) })}</p>
                  {detailUnavailable ? <p className="panel-note">{t("hotels.watchlist.detailUnavailable")}</p> : null}
                </div>
                <div className="hotel-watchlist-actions">
                  <button type="button" className="btn-ghost btn-compact" onClick={() => onRemove(item.id, item.hotel_id)} disabled={busy}>
                    {busy ? t("shared.states.loading") : t("hotels.watchlist.remove")}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}
