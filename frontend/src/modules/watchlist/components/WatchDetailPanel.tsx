import { useEffect, useState } from "react";

import { useI18n } from "@/i18n";
import { apiFetch } from "@/modules/shared/api";
import { formatCurrency, formatPercent, formatRelativeTime } from "@/modules/shared/format";
import { getWatchStatusMeta } from "@/modules/shared/statusCatalog";
import { freshnessLabel, safeDateTime } from "@/modules/watchlist/presentation";
import { hasPriceSummaryData } from "@/modules/watchlist/summary";
import type { PriceCalendarResponse, PriceSummary, Watch, WatchDetail } from "@/modules/watchlist/types";

type WatchDetailPanelProps = {
  selectedWatch: Watch | null;
  detail: WatchDetail | null;
  summary: PriceSummary | null;
  isLoading: boolean;
  onRefreshWatch: (watchId: string) => void;
  onPauseWatch: (watchId: string) => void;
  onResumeWatch: (watchId: string) => void;
};

export function WatchDetailPanel({
  selectedWatch,
  detail,
  summary,
  isLoading,
  onRefreshWatch,
  onPauseWatch,
  onResumeWatch,
}: WatchDetailPanelProps) {
  const { t } = useI18n();
  const [calendar, setCalendar] = useState<PriceCalendarResponse | null>(null);

  useEffect(() => {
    if (!selectedWatch?.id) {
      setCalendar(null);
      return;
    }
    let mounted = true;
    apiFetch<PriceCalendarResponse>(`/prices/calendar?watch_id=${selectedWatch.id}`)
      .then((payload) => {
        if (!mounted) return;
        setCalendar(payload);
      })
      .catch(() => {
        if (!mounted) return;
        setCalendar(null);
      });
    return () => {
      mounted = false;
    };
  }, [selectedWatch?.id]);

  if (!selectedWatch) {
    return (
      <section className="panel panel-soft section-gap">
        <h2 className="panel-title">{t("watchlist.detail.title")}</h2>
        <p className="panel-note">{t("watchlist.detail.empty")}</p>
      </section>
    );
  }

  const focus = detail || selectedWatch;
  const status = getWatchStatusMeta(focus.status, t);

  return (
    <section className="panel panel-soft section-gap">
      <div className="row-between">
        <h2 className="panel-title">{t("watchlist.detail.title")}</h2>
        {isLoading ? <span className="panel-note">{t("watchlist.detail.loading")}</span> : null}
      </div>
      <div className="stack">
        <strong>{focus.origin_iata} {"->"} {focus.destination_iata}</strong>
        <span className="panel-note">{focus.travel_date_local}</span>
        <span className={`status-pill ${status.tone}`}>{status.label}</span>
        <span className="panel-note">
          {t("watchlist.detail.currentPrice")} {detail?.latest_snapshot ? formatCurrency(detail.latest_snapshot.raw_price, detail.latest_snapshot.raw_currency) : "--"}
        </span>
        <span className="panel-note">
          {t("watchlist.detail.latestSnapshot")} {detail?.latest_snapshot ? safeDateTime(detail.latest_snapshot.captured_at_utc) : "--"}
        </span>
        <span className="panel-note">
          {t("watchlist.detail.freshness")} {detail?.latest_snapshot ? freshnessLabel(detail.latest_snapshot.captured_at_utc) : t("watchlist.detail.freshnessUnknown")}
        </span>
        {detail?.latest_snapshot ? (
          <span className="panel-note">
            {t("watchlist.detail.lastUpdateRelative")} {formatRelativeTime(detail.latest_snapshot.captured_at_utc)}
          </span>
        ) : null}
      </div>
      <div className="alert-actions">
        <button className="btn-secondary btn-compact" type="button" onClick={() => onRefreshWatch(focus.id)}>
          {t("watchlist.detail.actions.refresh")}
        </button>
        {focus.status === "paused" ? (
          <button className="btn-ghost btn-compact" type="button" onClick={() => onResumeWatch(focus.id)}>
            {t("watchlist.detail.actions.resume")}
          </button>
        ) : (
          <button className="btn-ghost btn-compact" type="button" onClick={() => onPauseWatch(focus.id)}>
            {t("watchlist.detail.actions.pause")}
          </button>
        )}
      </div>
      <div className="history-summary history-summary--kpis">
        {summary && hasPriceSummaryData(summary) ? (
          <>
            <div className="history-kpi"><span>{t("watchlist.summary.latest")}</span><strong>{summary.latest_price == null ? "--" : formatCurrency(summary.latest_price, "EUR")}</strong></div>
            <div className="history-kpi"><span>{t("watchlist.summary.min")}</span><strong>{summary.min_price == null ? "--" : formatCurrency(summary.min_price, "EUR")}</strong></div>
            <div className="history-kpi"><span>{t("watchlist.summary.max")}</span><strong>{summary.max_price == null ? "--" : formatCurrency(summary.max_price, "EUR")}</strong></div>
            <div className="history-kpi"><span>{t("watchlist.summary.avg")}</span><strong>{summary.avg_price == null ? "--" : formatCurrency(summary.avg_price, "EUR")}</strong></div>
            <div className="history-kpi"><span>{t("watchlist.summary.delta")}</span><strong>{summary.delta_pct == null ? "--" : formatPercent(summary.delta_pct)}</strong></div>
            <div className="history-kpi"><span>{t("watchlist.summary.count")}</span><strong>{summary.count}</strong></div>
          </>
        ) : (
          <p className="panel-note">{t("watchlist.summary.empty")}</p>
        )}
      </div>
      <div className="history-summary">
        <h3 className="panel-title">Calendario</h3>
        {calendar?.days?.length ? (
          <>
            <p className="panel-note">Los precios son orientativos y dependen de la frescura del proveedor.</p>
            <div className="table-wrap">
              <table className="table-compact">
                <thead>
                  <tr>
                    <th>Día</th>
                    <th>Mín</th>
                    <th>Máx</th>
                    <th>Media</th>
                    <th>Capturas</th>
                    <th>Señal</th>
                  </tr>
                </thead>
                <tbody>
                  {calendar.days.map((day) => (
                    <tr key={`calendar-${day.date}`}>
                      <td>{day.date}</td>
                      <td>{formatCurrency(day.min_price, calendar.currency)}</td>
                      <td>{formatCurrency(day.max_price, calendar.currency)}</td>
                      <td>{formatCurrency(day.avg_price, calendar.currency)}</td>
                      <td>{day.snapshot_count}</td>
                      <td>
                        {day.is_daily_min ? "Mínimo del periodo" : day.is_daily_max ? "Máximo del periodo" : day.freshness_state || "normal"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <p className="panel-note">Aún no hay suficientes capturas para crear un calendario.</p>
        )}
      </div>
    </section>
  );
}
