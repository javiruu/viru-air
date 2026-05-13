import { useMemo, useState } from "react";

import { useI18n } from "@/i18n";
import { formatCurrency, formatSignedCurrency } from "@/modules/shared/format";
import { getWatchStatusMeta } from "@/modules/shared/statusCatalog";
import { buildSparklinePath, safeDateTime } from "@/modules/watchlist/presentation";
import { getFreshnessPresentation } from "@/modules/watchlist/summary";

type ListSort = "freshness" | "price_asc" | "price_desc" | "delta";

type WatchItem = {
  id: string;
  origin_iata: string;
  destination_iata: string;
  travel_date_local: string;
  target_price?: number | null;
  status: string;
};

type HistoryRow = {
  watchId: string;
  capturedAt: string;
  price: number;
};

type WatchMetaEntry = {
  latest: {
    capturedAt: string;
    price: number;
    currency: string;
  } | null;
  previous: {
    price: number;
    currency: string;
  } | null;
};

type SmartWatchListPanelProps = {
  items: WatchItem[];
  smartListItems: WatchItem[];
  watchMeta: Map<string, WatchMetaEntry>;
  historyRows: HistoryRow[];
  lastUpdatedGlobal: string;
  watchSearch: string;
  watchSort: ListSort;
  hasSearchFilter: boolean;
  selectedWatchId: string;
  refreshingWatchId: string | null;
  onSearchChange: (value: string) => void;
  onSortChange: (value: ListSort) => void;
  onClearSearch: () => void;
  onSelectWatch: (watch: WatchItem) => void;
  onRefreshWatch: (watchId: string) => void;
  onPauseWatch: (watchId: string) => void;
  onResumeWatch: (watchId: string) => void;
  onDeleteWatch: (watchId: string) => void;
  onBulkPause: (watchIds: string[]) => void;
  onBulkResume: (watchIds: string[]) => void;
  onBulkDelete: (watchIds: string[]) => void;
  onBulkRefresh: (watchIds: string[]) => void;
  isRefreshingBulk: boolean;
  onOpenAddWatch: () => void;
};

export function SmartWatchListPanel({
  items,
  smartListItems,
  watchMeta,
  historyRows,
  lastUpdatedGlobal,
  watchSearch,
  watchSort,
  hasSearchFilter,
  selectedWatchId,
  refreshingWatchId,
  onSearchChange,
  onSortChange,
  onClearSearch,
  onSelectWatch,
  onRefreshWatch,
  onPauseWatch,
  onResumeWatch,
  onDeleteWatch,
  onBulkPause,
  onBulkResume,
  onBulkDelete,
  onBulkRefresh,
  isRefreshingBulk,
  onOpenAddWatch,
}: SmartWatchListPanelProps) {
  const { t } = useI18n();
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const hasSelection = selectedIds.length > 0;
  const selectionCount = selectedIds.length;
  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);

  return (
    <section className="panel panel-soft section-gap">
      <div className="panel-header">
        <div>
          <h2 className="panel-title">{t("watchlist.smartList.heading")}</h2>
          <span className="muted">
            {t("watchlist.smartList.activeCount", { count: items.length })}{lastUpdatedGlobal ? ` · Última actualización ${lastUpdatedGlobal}` : ""}
          </span>
          {items.length > 0 ? (
            <span className="watch-smart-meta">
              {t("watchlist.smartList.showingCount", { shown: smartListItems.length, total: items.length })}
            </span>
          ) : null}
        </div>
        <div className="watch-smart-tools">
          <label className="watch-smart-search" htmlFor="watch-smart-search">
            Buscar
            <input
              id="watch-smart-search"
              name="watch_smart_search"
              autoComplete="off"
              value={watchSearch}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder="MAD DUB 2026-04-20"
            />
          </label>
          <label className="watch-smart-sort" htmlFor="watch-smart-sort">
            Ordenar
            <select
              id="watch-smart-sort"
              name="watch_smart_sort"
              autoComplete="off"
              value={watchSort}
              onChange={(event) => onSortChange(event.target.value as ListSort)}
            >
              <option value="freshness">Frescura</option>
              <option value="price_asc">Precio ascendente</option>
              <option value="price_desc">Precio descendente</option>
              <option value="delta">Mayor variación</option>
            </select>
          </label>
          <button
            type="button"
            className="btn-ghost btn-compact watch-smart-reset"
            onClick={onClearSearch}
            disabled={!hasSearchFilter}
          >
            Limpiar búsqueda
          </button>
          {hasSelection ? (
            <div className="alert-actions watch-bulk-toolbar" role="toolbar" aria-label={t("watchlist.bulk.toolbarAriaLabel")} data-testid="watchlist-bulk-toolbar">
              <span className="watch-smart-meta">{t("watchlist.bulk.selectedCount", { count: selectionCount })}</span>
              <button type="button" className="btn-secondary btn-compact" onClick={() => onBulkRefresh(selectedIds)} disabled={isRefreshingBulk}>
                {isRefreshingBulk ? t("watchlist.bulk.refreshing") : t("watchlist.bulk.refreshSelected")}
              </button>
              <button type="button" className="btn-ghost btn-compact" onClick={() => onBulkPause(selectedIds)}>{t("watchlist.bulk.pause")}</button>
              <button type="button" className="btn-ghost btn-compact" onClick={() => onBulkResume(selectedIds)}>{t("watchlist.bulk.resume")}</button>
              <button type="button" className="btn-ghost btn-compact" onClick={() => onBulkDelete(selectedIds)}>{t("watchlist.bulk.delete")}</button>
            </div>
          ) : null}
        </div>
      </div>
      {items.length === 0 ? (
        <div className="empty-guide">
          <p className="panel-note">Todavía no tienes vuelos vigilados.</p>
          <div className="empty-steps">
            <div>
              <strong>1. Define tu ruta</strong>
              <span>Elige origen, destino y fecha exacta.</span>
            </div>
            <div>
              <strong>2. Marca precio objetivo</strong>
              <span>Opcional, para detectar bajadas rápido.</span>
            </div>
            <div>
              <strong>3. Activa alertas</strong>
              <span>Recibe cambios sin revisar a mano.</span>
            </div>
          </div>
          <button className="btn-primary" type="button" onClick={onOpenAddWatch}>
            Añadir tu primer vuelo
          </button>
        </div>
      ) : null}
      {items.length > 0 && smartListItems.length === 0 ? (
        <div className="watch-empty-search" role="status" aria-live="polite">
          <p>No hay vuelos que coincidan con la búsqueda actual.</p>
          <button type="button" className="btn-ghost btn-compact" onClick={onClearSearch}>
            Ver todos los vuelos
          </button>
        </div>
      ) : null}
      {smartListItems.map((watch) => {
        const watchStatus = getWatchStatusMeta(watch.status, t);
        const meta = watchMeta.get(watch.id);
        const trend = !meta?.latest || !meta?.previous
          ? "flat"
          : meta.latest.price > meta.previous.price
            ? "up"
            : meta.latest.price < meta.previous.price
              ? "down"
              : "flat";
        const deltaLabel = !meta?.latest || !meta?.previous
          ? "Sin variación"
          : formatSignedCurrency(meta.latest.price - meta.previous.price, meta.latest.currency);
        const routeHealthLabel = trend === "up" ? "Sube" : trend === "down" ? "Baja" : "Estable";

        const values = historyRows
          .filter((row) => row.watchId === watch.id)
          .sort((a, b) => new Date(a.capturedAt).getTime() - new Date(b.capturedAt).getTime())
          .slice(-7)
          .map((row) => row.price);
        const sparkPath = buildSparklinePath(values);
        const freshness = getFreshnessPresentation({
          t,
          lastUpdatedAt: meta?.latest?.capturedAt,
          freshnessState: meta?.latest ? "observing" : null,
        });

        return (
          <article
            key={watch.id}
            className={`list-row watch-row ${selectedWatchId === watch.id ? "watch-selected" : ""}`}
            onClick={() => onSelectWatch(watch)}
            role="button"
            tabIndex={0}
            aria-pressed={selectedWatchId === watch.id}
            aria-label={`Seleccionar vuelo ${watch.origin_iata} a ${watch.destination_iata} del ${watch.travel_date_local}`}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onSelectWatch(watch);
              }
            }}
          >
            <div className="watch-details">
              <div className="watch-route">
                <input
                  type="checkbox"
                  checked={selectedSet.has(watch.id)}
                  onChange={(event) => {
                    event.stopPropagation();
                    setSelectedIds((prev) =>
                      event.target.checked ? Array.from(new Set([...prev, watch.id])) : prev.filter((id) => id !== watch.id),
                    );
                  }}
                  aria-label={`Seleccionar ${watch.origin_iata} ${watch.destination_iata}`}
                />
                <strong>{watch.origin_iata}{" -> "}{watch.destination_iata}</strong>
                <span className="watch-date">{watch.travel_date_local}</span>
                <span className={`status-pill ${watchStatus.tone}`}>{watchStatus.label}</span>
                <span className={`status-pill ${trend === "up" ? "error" : trend === "down" ? "success" : "warning"}`}>
                  {routeHealthLabel}
                </span>
              </div>
              <div className="watch-meta">
                <span className="watch-meta-chip">Última actualización: {safeDateTime(meta?.latest?.capturedAt)}</span>
                <span className="watch-meta-chip">{t("watchlist.detail.freshness")} {freshness.fullText}</span>
                <span className="watch-note">Precio orientativo base 1 adulto, sin extras.</span>
              </div>
            </div>
            <div className="watch-price-area">
              <div className="watch-price">
                <span className="watch-price-caption">Precio actual</span>
                <strong className="watch-price-main">
                  {meta?.latest ? formatCurrency(meta.latest.price, meta.latest.currency) : "--"}
                </strong>
                <span className={`trend-chip trend-${trend}`}>
                  <span className="trend-icon" aria-hidden="true">
                    <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                      <path
                        d="M6 15l6-6 6 6"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </span>
                  {deltaLabel}
                </span>
              </div>
              <div className="watch-spark">
                {sparkPath ? (
                  <svg viewBox="0 0 96 28" role="img" aria-label="Tendencia breve de precio">
                    <path d={sparkPath} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  </svg>
                ) : (
                  <span className="muted">Sin tendencia</span>
                )}
              </div>
              <button
                className="btn-secondary"
                type="button"
                disabled={refreshingWatchId === watch.id}
                aria-busy={refreshingWatchId === watch.id}
                onClick={(event) => {
                  event.stopPropagation();
                  onRefreshWatch(watch.id);
                }}
              >
                {refreshingWatchId === watch.id ? "Actualizando..." : "Actualizar"}
              </button>
              <div className="alert-actions">
                {watch.status === "paused" ? (
                  <button className="btn-ghost btn-compact" type="button" onClick={(e) => { e.stopPropagation(); onResumeWatch(watch.id); }}>
                    Reanudar
                  </button>
                ) : (
                  <button className="btn-ghost btn-compact" type="button" onClick={(e) => { e.stopPropagation(); onPauseWatch(watch.id); }}>
                    Pausar
                  </button>
                )}
                <button className="btn-ghost btn-compact" type="button" onClick={(e) => { e.stopPropagation(); onDeleteWatch(watch.id); }}>
                  Eliminar
                </button>
              </div>
            </div>
          </article>
        );
      })}
    </section>
  );
}




