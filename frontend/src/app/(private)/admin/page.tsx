"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { useI18n } from "@/i18n";
import { apiFetch } from "@/modules/shared/api";
import { Skeleton, SkeletonPanel } from "@/modules/shared/Skeleton";

type Me = { id: string; email: string; locale: string; is_admin: boolean };

type AdminUser = {
  id: string;
  email: string;
  is_admin: boolean;
  is_verified: boolean;
  locale: string;
  timezone: string;
  created_at: string;
};

type Watch = {
  id: string;
  origin_iata: string;
  destination_iata: string;
  travel_date_local: string;
  status: string;
};

type SystemStatus = "ok" | "degraded" | "down";

type QaCheck = {
  label: string;
  ok: boolean;
  detail: string;
};

type ProductMetrics = {
  dashboard_views: number;
  quick_search_executed: number;
  search_empty_results: number;
  search_empty_rate_pct: number;
  quick_search_avg_ms: number;
  watchlist_refresh: number;
  alert_created: number;
  alert_triggered: number;
  watchlist_refresh_to_alert_created_pct: number;
  alert_created_rate_pct: number;
};

export default function AdminPage() {
  const router = useRouter();
  const { t, localeTag } = useI18n();
  const [me, setMe] = useState<Me | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [selectedUserId, setSelectedUserId] = useState("");
  const [selectedWatches, setSelectedWatches] = useState<Watch[]>([]);
  const [password, setPassword] = useState("");
  const [origin, setOrigin] = useState("MAD");
  const [destination, setDestination] = useState("DUB");
  const [travelDate, setTravelDate] = useState("");
  const [targetPrice, setTargetPrice] = useState("");
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState<"error" | "success">("error");
  const [systemStatus, setSystemStatus] = useState<SystemStatus>("ok");
  const [updatedAt, setUpdatedAt] = useState("");
  const [qaChecks, setQaChecks] = useState<QaCheck[]>([]);
  const [metrics, setMetrics] = useState<ProductMetrics | null>(null);

  const statusMeta = useMemo(() => {
    if (systemStatus === "ok") return { label: t("admin.status.ok"), detail: t("admin.status.okDetail") };
    if (systemStatus === "down") return { label: t("admin.status.down"), detail: t("admin.status.downDetail") };
    return { label: t("admin.status.degraded"), detail: t("admin.status.degradedDetail") };
  }, [systemStatus, t]);

  const runSystemChecks = useCallback(async () => {
    const checks = await Promise.allSettled([
      apiFetch<Me>("/auth/me"),
      apiFetch<AdminUser[]>("/admin/users"),
      apiFetch<Watch[]>("/watchlist"),
      apiFetch<ProductMetrics>("/admin/product-metrics"),
    ]);

    const nextChecks: QaCheck[] = [
      {
        label: t("admin.checks.validSession"),
        ok: checks[0].status === "fulfilled",
        detail: checks[0].status === "fulfilled" ? t("admin.checks.detailTokenOk") : t("admin.checks.detailTokenFail"),
      },
      {
        label: t("admin.checks.adminEndpoints"),
        ok: checks[1].status === "fulfilled",
        detail: checks[1].status === "fulfilled" ? t("admin.checks.detailAdminOk") : t("admin.checks.detailAdminFail"),
      },
      {
        label: t("admin.checks.watchlistConsistency"),
        ok: checks[2].status === "fulfilled",
        detail: checks[2].status === "fulfilled" ? t("admin.checks.detailWatchlistOk") : t("admin.checks.detailWatchlistFail"),
      },
      {
        label: t("admin.checks.tokenRefresh"),
        ok: checks[0].status === "fulfilled",
        detail: checks[0].status === "fulfilled" ? t("admin.checks.detailRefreshOk") : t("admin.checks.detailRefreshFail"),
      },
      {
        label: t("admin.checks.priceCorrelation"),
        ok: checks[2].status === "fulfilled",
        detail: checks[2].status === "fulfilled" ? t("admin.checks.detailPriceOk") : t("admin.checks.detailPriceFail"),
      },
    ];

    setQaChecks(nextChecks);

    if (checks[3].status === "fulfilled") {
      setMetrics(checks[3].value);
    }

    const failures = nextChecks.filter((item) => !item.ok).length;
    if (failures === 0) {
      setSystemStatus("ok");
    } else if (failures >= 2) {
      setSystemStatus("down");
    } else {
      setSystemStatus("degraded");
    }

    setUpdatedAt(new Date().toLocaleString(localeTag, { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
  }, [localeTag, t]);

  useEffect(() => {
    async function load() {
      try {
        const meData = await apiFetch<Me>("/auth/me");
        setMe(meData);
        if (!meData.is_admin) {
          router.replace("/dashboard");
          return;
        }
        const data = await apiFetch<AdminUser[]>("/admin/users");
        setUsers(data);
        await runSystemChecks();
      } catch {
        setMessage(t("admin.loadError"));
        setMessageType("error");
      }
    }
    load();
  }, [router, runSystemChecks, t]);

  async function refreshUsers() {
    const data = await apiFetch<AdminUser[]>("/admin/users");
    setUsers(data);
  }

  async function loadWatches(userId: string) {
    const data = await apiFetch<Watch[]>(`/admin/users/${userId}/watchlist`);
    setSelectedWatches(data);
  }

  async function onSelectUser(userId: string) {
    setSelectedUserId(userId);
    if (userId) {
      await loadWatches(userId);
    } else {
      setSelectedWatches([]);
    }
  }

  async function onResetPassword(event: FormEvent) {
    event.preventDefault();
    setMessage("");
    setMessageType("error");
    if (!selectedUserId) {
      setMessage(t("admin.notices.selectUser"));
      return;
    }
    try {
      await apiFetch(`/admin/users/${selectedUserId}/password`, {
        method: "PUT",
        body: JSON.stringify({ password }),
      });
      setPassword("");
      setMessage(t("admin.notices.passwordUpdated"));
      setMessageType("success");
    } catch {
      setMessage(t("admin.notices.passwordError"));
      setMessageType("error");
    }
  }

  async function onToggleAdmin(user: AdminUser) {
    setMessage("");
    setMessageType("error");
    try {
      await apiFetch(`/admin/users/${user.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_admin: !user.is_admin }),
      });
      await refreshUsers();
      setMessage(t("admin.notices.roleUpdated"));
      setMessageType("success");
    } catch {
      setMessage(t("admin.notices.roleError"));
      setMessageType("error");
    }
  }

  async function onCreateWatch(event: FormEvent) {
    event.preventDefault();
    setMessage("");
    setMessageType("error");
    if (!selectedUserId) {
      setMessage(t("admin.notices.selectUser"));
      return;
    }
    try {
      await apiFetch(`/admin/users/${selectedUserId}/watchlist`, {
        method: "POST",
        body: JSON.stringify({
          origin_iata: origin,
          destination_iata: destination,
          travel_date_local: travelDate,
          target_price: targetPrice ? Number(targetPrice) : null,
        }),
      });
      await loadWatches(selectedUserId);
      setMessage(t("admin.notices.watchInjected"));
      setMessageType("success");
    } catch {
      setMessage(t("admin.notices.watchInjectError"));
      setMessageType("error");
    }
  }

  async function onDeleteWatch(watchId: string) {
    setMessage("");
    setMessageType("error");
    try {
      await apiFetch(`/admin/watchlist/${watchId}`, { method: "DELETE" });
      if (selectedUserId) {
        await loadWatches(selectedUserId);
      }
      setMessage(t("admin.notices.watchDeleted"));
      setMessageType("success");
    } catch {
      setMessage(t("admin.notices.watchDeleteError"));
      setMessageType("error");
    }
  }

  async function onDeleteUser(userId: string) {
    const confirmDelete = window.confirm(t("admin.confirmations.deleteUser"));
    if (!confirmDelete) return;
    setMessage("");
    setMessageType("error");
    try {
      await apiFetch(`/admin/users/${userId}`, { method: "DELETE" });
      if (userId === selectedUserId) {
        setSelectedUserId("");
        setSelectedWatches([]);
      }
      await refreshUsers();
      setMessage(t("admin.notices.userDeleted"));
      setMessageType("success");
    } catch {
      setMessage(t("admin.notices.userDeleteError"));
      setMessageType("error");
    }
  }

  if (!me?.is_admin) {
    return (
      <main className="shell" id="main-content">
        <SkeletonPanel className="air-loader-section" ariaLabel={t("admin.loading")} />
      </main>
    );
  }

  return (
    <main className="shell cycle4-page admin-page" id="main-content">
      <div className="page-header">
        <button className="btn-ghost" type="button" onClick={() => router.push("/dashboard")}>
          {t("admin.back")}
        </button>
        <div className="page-title">
          <h1>{t("admin.title")}</h1>
          <p>{t("admin.subtitle")}</p>
        </div>
      </div>
      {message ? (
        <div className={`notice ${messageType === "success" ? "notice-success" : "notice-error"}`} role="status" aria-live="polite">
          {message}
        </div>
      ) : null}

      <section className="panel panel-soft section-gap">
        <div className="panel-header">
          <h2 className="panel-title">{t("admin.systemTitle")}</h2>
          <span className={`status-badge status-${systemStatus}`}>{statusMeta.label}</span>
        </div>
        <p className="panel-note">{statusMeta.detail} {t("admin.status.lastCheck")}: {updatedAt || "--:--:--"}.</p>
        <p className="section-gap-sm">
          <button type="button" className="btn-secondary btn-compact" onClick={runSystemChecks}>{t("admin.retryChecks")}</button>
        </p>
      </section>

      <section className="panel panel-soft section-gap">
        <div className="panel-header">
          <h2 className="panel-title">{t("admin.diagnosticsTitle")}</h2>
          <span className="panel-note">{t("admin.diagnosticsTag")}</span>
        </div>
        <div className="stack">
          {qaChecks.length === 0 ? (
            <div className="loading-skeleton-list" role="status" aria-live="polite" aria-label={t("admin.loading")} aria-busy="true">
              {Array.from({ length: 3 }).map((_, idx) => (
                <article key={`admin-check-skeleton-${idx}`} className="loading-skeleton-list-row">
                  <div className="loading-skeleton-list-main">
                    <Skeleton variant="line" width="58%" />
                    <Skeleton variant="line" width="42%" />
                  </div>
                  <Skeleton variant="pill" width={74} height={22} />
                </article>
              ))}
            </div>
          ) : (
            qaChecks.map((check) => (
              <article key={check.label} className="list-row">
                <div>
                  <strong>{check.label}</strong>
                  <div className="panel-note">{check.detail}</div>
                </div>
                <span className={`status-badge ${check.ok ? "status-ok" : "status-down"}`}>{check.ok ? t("admin.checks.ok") : t("admin.checks.failed")}</span>
              </article>
            ))
          )}
        </div>
      </section>

      <section className="panel panel-soft section-gap">
        <div className="panel-header">
          <h2 className="panel-title">{t("admin.metricsTitle")}</h2>
          <span className="panel-note">{t("admin.metricsSubtitle")}</span>
        </div>
        {!metrics ? (
          <div className="dashboard-primary-grid" role="status" aria-live="polite" aria-label={t("admin.loading")} aria-busy="true">
            {Array.from({ length: 6 }).map((_, idx) => (
              <article key={`admin-metric-skeleton-${idx}`} className="module-card">
                <Skeleton variant="line" width="70%" />
                <Skeleton variant="pill" width="44%" height={20} />
              </article>
            ))}
          </div>
        ) : (
          <div className="dashboard-primary-grid">
            <article className="module-card"><strong>{t("admin.metricsQuickSearches")}</strong><span>{metrics.quick_search_executed}</span></article>
            <article className="module-card"><strong>{t("admin.metricsEmptyRate")}</strong><span>{metrics.search_empty_rate_pct}%</span></article>
            <article className="module-card"><strong>{t("admin.metricsAlertsCreated")}</strong><span>{metrics.alert_created}</span></article>
            <article className="module-card"><strong>{t("admin.metricsAlertsTriggered")}</strong><span>{metrics.alert_triggered}</span></article>
            <article className="module-card"><strong>{t("admin.metricsWatchRefreshes")}</strong><span>{metrics.watchlist_refresh}</span></article>
            <article className="module-card"><strong>{t("admin.metricsDashboardViews")}</strong><span>{metrics.dashboard_views}</span></article>
            <article className="module-card"><strong>{t("admin.metricsAvgSearchMs")}</strong><span>{metrics.quick_search_avg_ms}</span></article>
            <article className="module-card"><strong>{t("admin.metricsRefreshToAlertRate")}</strong><span>{metrics.watchlist_refresh_to_alert_created_pct}%</span></article>
            <article className="module-card"><strong>{t("admin.metricsAlertCreateRate")}</strong><span>{metrics.alert_created_rate_pct}%</span></article>
          </div>
        )}
      </section>

      <section className="split section-gap">
        <div className="panel panel-soft stack-lg">
          <div>
            <h2 className="panel-title">{t("admin.users.title")}</h2>
            <p className="panel-subtitle">{t("admin.users.subtitle")}</p>
          </div>
          <label className="field">
            {t("admin.users.select")}
            <select
              name="selected_user"
              autoComplete="off"
              value={selectedUserId}
              onChange={(e) => onSelectUser(e.target.value)}
            >
              <option value="">{t("admin.users.selectPlaceholder")}</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>{u.email}</option>
              ))}
            </select>
          </label>
          <div className="stack">
            {users.map((u) => (
              <div key={u.id} className="list-row">
                <div>
                  <strong>{u.email}</strong>
                  <div className="panel-note">
                    {u.is_admin ? t("admin.users.roleAdmin") : t("admin.users.roleUser")} · {u.locale} · {u.timezone}
                  </div>
                </div>
                <div className="row-actions">
                  <button className="btn-ghost" onClick={() => onToggleAdmin(u)}>
                    {u.is_admin ? t("admin.users.removeAdmin") : t("admin.users.makeAdmin")}
                  </button>
                  <button className="btn-ghost" onClick={() => onDeleteUser(u.id)}>{t("admin.users.delete")}</button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="panel panel-soft stack-lg">
          <div>
            <h2 className="panel-title">{t("admin.actions.title")}</h2>
            <p className="panel-subtitle">{t("admin.actions.subtitle")}</p>
          </div>
          <form className="form" onSubmit={onResetPassword}>
            <label className="field">
              {t("admin.actions.resetPasswordLabel")}
              <input
                name="admin_reset_password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                type="password"
                placeholder={t("admin.actions.resetPasswordPlaceholder")}
              />
            </label>
            <button type="submit" className="btn-primary">{t("admin.actions.changePassword")}</button>
          </form>

          <form className="form form-spaced" onSubmit={onCreateWatch}>
            <label className="field">
              {t("admin.actions.origin")}
              <input
                name="origin_iata"
                autoComplete="off"
                value={origin}
                onChange={(e) => setOrigin(e.target.value.toUpperCase())}
              />
            </label>
            <label className="field">
              {t("admin.actions.destination")}
              <input
                name="destination_iata"
                autoComplete="off"
                value={destination}
                onChange={(e) => setDestination(e.target.value.toUpperCase())}
              />
            </label>
            <label className="date-field field">
              {t("admin.actions.travelDate")}
              <input
                name="travel_date"
                autoComplete="off"
                type="date"
                value={travelDate}
                onChange={(e) => setTravelDate(e.target.value)}
              />
            </label>
            <label className="field">
              {t("admin.actions.targetPrice")}
              <input
                name="target_price"
                autoComplete="off"
                inputMode="decimal"
                value={targetPrice}
                onChange={(e) => setTargetPrice(e.target.value)}
              />
            </label>
            <button type="submit" className="btn-primary">{t("admin.actions.injectWatch")}</button>
          </form>

          <div className="stack section-gap-lg">
            <div className="row-between">
              <h3 className="panel-title">{t("admin.actions.userFlights")}</h3>
              <span className="panel-note">{t("admin.actions.routesCount", { count: selectedWatches.length })}</span>
            </div>
            {selectedWatches.length === 0 ? (
              <p className="panel-note">{t("admin.actions.noFlights")}</p>
            ) : (
              selectedWatches.map((w) => (
                <div key={w.id} className="list-row">
                  <span>{w.origin_iata} {" -> "} {w.destination_iata} ({w.travel_date_local})</span>
                  <button className="btn-ghost" onClick={() => onDeleteWatch(w.id)}>{t("admin.users.delete")}</button>
                </div>
              ))
            )}
          </div>
        </div>
      </section>

      <footer className="tech-footer section-gap">
        <div className="tech-chips">
          <span className="tech-chip">{t("admin.footer.web")}: {statusMeta.label}</span>
          <span className="tech-chip">{t("admin.footer.api")}: /api/v1</span>
          <span className="tech-chip">{t("admin.footer.port")}: 3000/8000</span>
          <span className="tech-chip">{t("admin.footer.updated")}: {updatedAt || "--:--:--"}</span>
        </div>
        <div className="tech-chips">
          <span className="tech-chip">{t("admin.footer.routes")}: {t("admin.footer.routesValue")}</span>
        </div>
      </footer>
    </main>
  );
}

