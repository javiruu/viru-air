"use client";

import Link from "next/link";
import { BellRing, CheckCheck, RadioTower, ShieldCheck, Tags, Wrench } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { useI18n } from "@/i18n";
import { apiFetch } from "@/modules/shared/api";
import { formatRelativeTime } from "@/modules/shared/format";

type NotificationCategory = "price" | "security" | "digest" | "worker";
type NotificationFilter = "all" | "unread" | NotificationCategory;
type NotificationTone = "success" | "warning" | "error" | "info";
type NotificationSourceType = "alert_event" | "hotel_alert_event" | "security_activity";

type NotificationInboxItem = {
  id: string;
  source_type: NotificationSourceType;
  source_id: string;
  category: NotificationCategory;
  tone: NotificationTone;
  title: string;
  body: string;
  route_label: string | null;
  action_href: string | null;
  created_at: string;
  read_at: string | null;
  is_read: boolean;
};

type NotificationInboxSummary = Record<"total" | "unread" | NotificationCategory, number>;

type NotificationInboxResponse = {
  items: NotificationInboxItem[];
  summary: NotificationInboxSummary;
};

const CATEGORY_ICONS = {
  price: Tags,
  security: ShieldCheck,
  digest: RadioTower,
  worker: Wrench,
} as const;

export default function NotificationsPage() {
  const { t, localeTag } = useI18n();
  const { notify } = useNotificationCenter();
  const [items, setItems] = useState<NotificationInboxItem[]>([]);
  const [summary, setSummary] = useState<NotificationInboxSummary>({
    total: 0,
    unread: 0,
    price: 0,
    security: 0,
    digest: 0,
    worker: 0,
  });
  const [filter, setFilter] = useState<NotificationFilter>("all");
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  const loadNotifications = useCallback(async () => {
    setStatus("loading");
    try {
      const response = await apiFetch<NotificationInboxResponse>("/notifications");
      setItems(response.items);
      setSummary(response.summary);
      setStatus("ready");
    } catch (error) {
      setStatus("error");
      notify({ tone: "error", title: t("notifications.states.error"), durationMs: 3600 });
    }
  }, [notify, t]);

  useEffect(() => {
    void loadNotifications();
  }, [loadNotifications]);

  const filters = useMemo(
    () =>
      [
        { value: "all", label: t("notifications.filters.all"), count: summary.total },
        { value: "unread", label: t("notifications.filters.unread"), count: summary.unread },
        { value: "price", label: t("notifications.filters.price"), count: summary.price },
        { value: "security", label: t("notifications.filters.security"), count: summary.security },
        { value: "digest", label: t("notifications.filters.digest"), count: summary.digest },
        { value: "worker", label: t("notifications.filters.worker"), count: summary.worker },
      ] as const,
    [summary, t],
  );

  const filteredItems = useMemo(() => {
    if (filter === "all") return items;
    if (filter === "unread") return items.filter((item) => !item.is_read);
    return items.filter((item) => item.category === filter);
  }, [filter, items]);

  async function markRead(item: NotificationInboxItem): Promise<void> {
    try {
      await apiFetch(`/notifications/${item.source_type}/${item.source_id}/read`, { method: "POST" });
      await loadNotifications();
      notify({ tone: "success", title: t("notifications.toast.markedRead"), durationMs: 2600 });
    } catch (error) {
      notify({ tone: "error", title: t("notifications.toast.error"), durationMs: 3600 });
    }
  }

  async function markAllRead(): Promise<void> {
    try {
      await apiFetch("/notifications/read-all", { method: "POST" });
      await loadNotifications();
      notify({ tone: "success", title: t("notifications.toast.markedAll"), durationMs: 2600 });
    } catch (error) {
      notify({ tone: "error", title: t("notifications.toast.error"), durationMs: 3600 });
    }
  }

  return (
    <main className="stack notifications-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">{t("notifications.hero.kicker")}</p>
          <h1>{t("notifications.pageTitle")}</h1>
          <p>{t("notifications.pageSubtitle")}</p>
        </div>
        <div className="panel-actions">
          <Link className="btn-ghost" href="/alerts">
            <BellRing size={16} aria-hidden="true" />
            {t("notifications.hero.openAlerts")}
          </Link>
          <button className="btn-secondary" type="button" onClick={markAllRead} disabled={summary.unread === 0}>
            <CheckCheck size={16} aria-hidden="true" />
            {t("notifications.hero.markAll")}
          </button>
        </div>
      </header>

      <section className="panel panel-soft notifications-hero">
        <div>
          <h2 className="panel-title">{t("notifications.hero.title")}</h2>
          <p className="panel-subtitle">{t("notifications.hero.subtitle")}</p>
        </div>
        <div className="notifications-summary-grid" aria-label={t("notifications.pageTitle")}>
          {(["unread", "total", "price", "security", "digest", "worker"] as const).map((key) => (
            <article className="notifications-summary-card" key={key}>
              <span>{t(`notifications.summary.${key}`)}</span>
              <strong>{summary[key]}</strong>
            </article>
          ))}
        </div>
      </section>

      <section className="panel panel-soft stack section-gap">
        <div className="notifications-filterbar" role="tablist" aria-label={t("notifications.pageTitle")}>
          {filters.map((option) => {
            const active = filter === option.value;
            return (
              <button
                key={option.value}
                type="button"
                role="tab"
                aria-selected={active}
                className={`btn-ghost btn-compact notifications-filter ${active ? "is-active" : ""}`}
                onClick={() => setFilter(option.value)}
              >
                {option.label}
                <span>{option.count}</span>
              </button>
            );
          })}
        </div>

        {status === "loading" ? (
          <div className="notifications-empty" role="status" aria-live="polite">
            <div className="notifications-radar" aria-hidden="true" />
            <strong>{t("notifications.states.loading")}</strong>
          </div>
        ) : null}

        {status === "error" ? (
          <div className="notifications-empty" role="alert">
            <div className="notifications-radar" aria-hidden="true" />
            <strong>{t("notifications.states.error")}</strong>
          </div>
        ) : null}

        {status === "ready" && filteredItems.length === 0 ? (
          <div className="notifications-empty">
            <div className="notifications-radar" aria-hidden="true" />
            <strong>{t("notifications.states.empty")}</strong>
            <p>{t("notifications.states.emptyBody")}</p>
          </div>
        ) : null}

        {status === "ready"
          ? filteredItems.map((item) => {
              const Icon = CATEGORY_ICONS[item.category];
              return (
                <article className={`list-row notifications-row ${item.is_read ? "" : "is-unread"}`} key={item.id}>
                  <div className={`notifications-row-icon ${item.tone}`} aria-hidden="true">
                    <Icon size={17} />
                  </div>
                  <div className="notifications-row-main">
                    <div className="notifications-row-title">
                      <strong>{item.title}</strong>
                      <span className={`status-pill ${item.is_read ? "info" : "warning"}`}>
                        {item.is_read ? t("notifications.row.read") : t("notifications.row.unread")}
                      </span>
                    </div>
                    <p>{item.body}</p>
                    <div className="notifications-row-meta">
                      <time dateTime={item.created_at}>{formatRelativeTime(item.created_at, localeTag)}</time>
                      {item.route_label ? <span>{item.route_label}</span> : null}
                    </div>
                  </div>
                  <div className="notifications-row-actions">
                    {item.action_href ? (
                      <Link className="btn-ghost btn-compact" href={item.action_href}>
                        {t("notifications.row.open")}
                      </Link>
                    ) : null}
                    {!item.is_read ? (
                      <button className="btn-secondary btn-compact" type="button" onClick={() => void markRead(item)}>
                        {t("notifications.row.markRead")}
                      </button>
                    ) : null}
                  </div>
                </article>
              );
            })
          : null}
      </section>
    </main>
  );
}
