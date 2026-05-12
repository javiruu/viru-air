"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { useI18n } from "@/i18n";
import { apiFetch } from "@/modules/shared/api";
import { getSystemStatusMeta } from "@/modules/shared/statusCatalog";

type Me = { id: string; email: string; locale: string; is_admin: boolean };

type ProductHealth = {
  usage: Record<string, { daily: number; weekly: number; trend: string }>;
  indicators: {
    search_empty_rate_pct: number;
    watchlist_refresh_to_action_pct: number;
    alert_create_rate_pct: number;
  };
  performance: {
    quick_search_avg_ms: number;
    dashboard_avg_ms: number;
    watchlist_refresh_avg_ms: number;
  };
  errors: {
    recent: Array<{ section: string; message: string; created_at: string }>;
    frequent: Array<{ message: string; count: number; last_seen: string | null }>;
    last_occurrence: string | null;
  };
  system: {
    status: "ok" | "degraded" | "critical";
    last_data_update: string | null;
    last_alert_execution: string | null;
  };
};

export default function ProductHealthPage() {
  const router = useRouter();
  const { t } = useI18n();
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [data, setData] = useState<ProductHealth | null>(null);

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const meData = await apiFetch<Me>("/auth/me");
        if (!active) return;
        setMe(meData);
        if (!meData.is_admin) {
          router.replace("/dashboard");
          return;
        }
        const payload = await apiFetch<ProductHealth>("/admin/product-health");
        if (active) setData(payload);
      } catch {
        if (active) setError("No se pudo cargar Product Health.");
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [router]);

  if (!me?.is_admin || loading) {
    return <main className="shell"><div className="notice notice-info">Cargando Product Health...</div></main>;
  }

  const systemMeta = data ? getSystemStatusMeta(data.system.status, t) : null;

  return (
    <main className="shell section-gap-lg">
      <section className="page-header">
        <div>
          <h1>Product Health</h1>
          <p className="panel-note">Observabilidad de uso, errores y rendimiento (solo admin).</p>
        </div>
        <Link href="/admin" className="btn-ghost">Volver a Admin</Link>
      </section>

      {error ? <div className="notice notice-error">{error}</div> : null}

      {data ? (
        <>
          <section className="panel panel-soft section-gap">
            <div className="panel-header">
              <h2 className="panel-title">Estado del sistema</h2>
              <span className={`status-pill ${systemMeta?.tone ?? "info"}`}>
                {systemMeta?.label ?? data.system.status}
              </span>
            </div>
            <p className="panel-note">Ãšltima actualizaciÃ³n de datos: {data.system.last_data_update ?? "sin datos"}</p>
            <p className="panel-note">Ãšltima ejecuciÃ³n de alertas: {data.system.last_alert_execution ?? "sin datos"}</p>
          </section>

          <section className="section-gap">
            <div className="dashboard-primary-grid">
              <article className="module-card"><strong>Visitas dashboard</strong><span>{data.usage.dashboard_view?.weekly ?? 0}</span></article>
              <article className="module-card"><strong>BÃºsquedas rÃ¡pidas</strong><span>{data.usage.quick_search_executed?.weekly ?? 0}</span></article>
              <article className="module-card"><strong>Refresh watchlist</strong><span>{data.usage.watchlist_refresh?.weekly ?? 0}</span></article>
              <article className="module-card"><strong>Alertas creadas</strong><span>{data.usage.alert_created?.weekly ?? 0}</span></article>
              <article className="module-card"><strong>Alertas disparadas</strong><span>{data.usage.alert_triggered?.weekly ?? 0}</span></article>
              <article className="module-card"><strong>Search empty</strong><span>{data.usage.search_empty_results?.weekly ?? 0}</span></article>
            </div>
          </section>

          <section className="panel section-gap">
            <h2 className="panel-title">Indicadores clave</h2>
            <div className="split section-gap-sm">
              <div className="panel-soft panel">
                <strong>% bÃºsquedas sin resultados</strong>
                <p>{data.indicators.search_empty_rate_pct}%</p>
              </div>
              <div className="panel-soft panel">
                <strong>Ratio refresh â†’ acciÃ³n</strong>
                <p>{data.indicators.watchlist_refresh_to_action_pct}%</p>
              </div>
              <div className="panel-soft panel">
                <strong>Tasa creaciÃ³n alertas</strong>
                <p>{data.indicators.alert_create_rate_pct}%</p>
              </div>
            </div>
          </section>

          <section className="panel section-gap">
            <h2 className="panel-title">Performance</h2>
            <ul>
              <li>Quick-search medio: {data.performance.quick_search_avg_ms} ms</li>
              <li>Dashboard medio: {data.performance.dashboard_avg_ms} ms</li>
              <li>Refresh watchlist medio: {data.performance.watchlist_refresh_avg_ms} ms</li>
            </ul>
          </section>

          <section className="split section-gap">
            <article className="panel">
              <h2 className="panel-title">Errores recientes</h2>
              {data.errors.recent.length === 0 ? <p className="panel-note">Sin errores recientes.</p> : (
                <ul>
                  {data.errors.recent.map((item, idx) => (
                    <li key={`${item.created_at}-${idx}`}>
                      <strong>{item.section}</strong> Â· {item.message}
                    </li>
                  ))}
                </ul>
              )}
            </article>

            <article className="panel">
              <h2 className="panel-title">Errores frecuentes</h2>
              {data.errors.frequent.length === 0 ? <p className="panel-note">Sin errores frecuentes.</p> : (
                <ul>
                  {data.errors.frequent.map((item, idx) => (
                    <li key={`${item.message}-${idx}`}>
                      <strong>{item.count}x</strong> Â· {item.message}
                    </li>
                  ))}
                </ul>
              )}
            </article>
          </section>
        </>
      ) : null}
    </main>
  );
}



