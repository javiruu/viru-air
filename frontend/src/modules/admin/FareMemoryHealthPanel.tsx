import type { FareMemoryCountMap, FareMemoryHealth, FareMemoryHistoricalAggregate } from "@/modules/admin/fareMemoryHealth";
import { buildFareMemorySummary } from "@/modules/admin/fareMemoryHealth";

type FareMemoryHealthPanelProps = {
  readonly snapshot: FareMemoryHealth;
};

type MetricCardProps = {
  readonly label: string;
  readonly value: string | number;
  readonly detail: string;
  readonly tone?: "success" | "warning" | "error" | "info";
};

type CountMapRowsProps = {
  readonly title: string;
  readonly emptyLabel: string;
  readonly values: FareMemoryCountMap;
};

const DATE_FORMATTER = new Intl.DateTimeFormat("es-ES", {
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

function formatTimestamp(value: string | null): string {
  if (!value) return "sin datos";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return DATE_FORMATTER.format(parsed);
}

function formatPrice(route: FareMemoryHistoricalAggregate): string {
  try {
    return new Intl.NumberFormat("es-ES", {
      style: "currency",
      currency: route.currency,
      maximumFractionDigits: 0,
    }).format(route.latest_price);
  } catch {
    return `${route.latest_price} ${route.currency}`.trim();
  }
}

function MetricCard({ label, value, detail, tone = "info" }: MetricCardProps) {
  return (
    <article className="module-card">
      <div className="row-between">
        <strong>{label}</strong>
        <span className={`status-pill ${tone}`}>{value}</span>
      </div>
      <p className="panel-note">{detail}</p>
    </article>
  );
}

function CountMapRows({ title, emptyLabel, values }: CountMapRowsProps) {
  const rows = Object.entries(values);

  return (
    <article className="panel panel-soft">
      <div className="panel-header">
        <h3 className="panel-title">{title}</h3>
        <span className="panel-note">{rows.length} estados</span>
      </div>
      <div className="stack">
        {rows.length === 0 ? (
          <p className="panel-note">{emptyLabel}</p>
        ) : (
          rows.map(([label, value]) => (
            <div className="list-row" key={label}>
              <span>{label}</span>
              <strong>{value}</strong>
            </div>
          ))
        )}
      </div>
    </article>
  );
}

export function FareMemoryHealthPanel({ snapshot }: FareMemoryHealthPanelProps) {
  const summary = buildFareMemorySummary(snapshot);
  const generatedAt = formatTimestamp(snapshot.generated_at);

  return (
    <section className="section-gap-lg" aria-labelledby="fare-memory-health-title">
      <div className="panel panel-soft section-gap">
        <div className="panel-header">
          <div>
            <h2 className="panel-title" id="fare-memory-health-title">Fare Memory</h2>
            <p className="panel-subtitle">
              Radar operativo de cache, revalidaciones y memoria historica agregada.
            </p>
          </div>
          <span className="status-pill info">Generado {generatedAt}</span>
        </div>
        <div className="dashboard-primary-grid">
          <MetricCard
            label="Cache rapido"
            value={summary.cacheEntries}
            detail={`${summary.expiredEntries} entradas caducadas y ${summary.negativeActiveEntries} negativas activas.`}
            tone={summary.expiredEntries > 0 ? "warning" : "success"}
          />
          <MetricCard
            label="Memoria de ofertas"
            value={summary.priceObservations}
            detail={`${summary.offerEntries} ofertas, ${summary.observationsLast24h} observaciones en 24h.`}
            tone={summary.changedLast24h > 0 ? "warning" : "info"}
          />
          <MetricCard
            label="Cola de revalidacion"
            value={summary.queuedJobs}
            detail={`${summary.runningJobs} running, ${summary.overdueQueued} vencidas, ${summary.failedLast24h} fallos en 24h.`}
            tone={summary.failedJobs > 0 || summary.overdueQueued > 0 ? "warning" : "success"}
          />
          <MetricCard
            label="Rutas con senal"
            value={summary.refreshSignalCount}
            detail={`${summary.trackedRoutes} rutas populares y ${summary.historicalRouteCount} historicos visibles.`}
          />
        </div>
      </div>

      <section className="split section-gap" aria-label="Detalles de Fare Memory">
        <article className="panel panel-soft">
          <div className="panel-header">
            <h3 className="panel-title">Rutas a refrescar</h3>
            <span className="panel-note">prioridad tecnica</span>
          </div>
          <div className="stack">
            {snapshot.refresh_signals.top_routes.length === 0 ? (
              <p className="panel-note">Sin rutas candidatas. La cabina esta tranquila.</p>
            ) : (
              snapshot.refresh_signals.top_routes.map((route) => (
                <div className="list-row" key={`${route.route}-${route.travel_date}`}>
                  <div>
                    <strong>{route.route}</strong>
                    <div className="panel-note">
                      {route.travel_date} - {route.active_watch_count} watches - {route.recent_search_count} busquedas
                    </div>
                  </div>
                  <span className="status-pill warning">P{route.suggested_job_priority}</span>
                </div>
              ))
            )}
          </div>
        </article>

        <article className="panel panel-soft">
          <div className="panel-header">
            <h3 className="panel-title">Historico dinamico</h3>
            <span className="panel-note">{snapshot.historical_aggregates.mode}</span>
          </div>
          <div className="stack">
            {snapshot.historical_aggregates.top_routes.length === 0 ? (
              <p className="panel-note">Aun no hay agregados historicos suficientes.</p>
            ) : (
              snapshot.historical_aggregates.top_routes.map((route) => (
                <div className="list-row" key={`${route.route}-${route.departure_date}-${route.currency}`}>
                  <div>
                    <strong>{route.route}</strong>
                    <div className="panel-note">
                      {route.departure_date} - {route.observation_count} observaciones - ultimo {formatPrice(route)}
                    </div>
                  </div>
                  <span className={`status-pill ${route.compaction_candidate ? "warning" : "info"}`}>
                    {route.compaction_candidate ? "Compactar luego" : "Lectura viva"}
                  </span>
                </div>
              ))
            )}
          </div>
        </article>
      </section>

      <section className="split section-gap">
        <CountMapRows
          title="Frescura cache"
          emptyLabel="Sin cache clasificada todavia."
          values={snapshot.search_cache.freshness}
        />
        <CountMapRows
          title="Jobs por tipo"
          emptyLabel="Sin jobs de revalidacion registrados."
          values={snapshot.revalidation_jobs.job_type}
        />
      </section>
    </section>
  );
}
