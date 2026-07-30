"use client";

import { CheckCheck, ListChecks } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { useI18n } from "@/i18n";
import {
  filterNotificationItems,
  groupNotificationItems,
  normalizeNotificationFilter,
  normalizeNotificationInboxResponse,
  type NotificationFilter,
  type NotificationInboxItem,
  type NotificationInboxSummary,
} from "@/modules/signals/notificationInboxModel";
import { SignalsInboxTimeline } from "@/modules/signals/SignalsInboxTimeline";
import { SignalsSectionNav } from "@/modules/signals/SignalsSectionNav";
import { apiFetch } from "@/modules/shared/api";

const EMPTY_SUMMARY: NotificationInboxSummary = {
  total: 0,
  unread: 0,
  price: 0,
  security: 0,
  digest: 0,
  worker: 0,
};

export function SignalsInbox({ requestedFilter }: { requestedFilter?: string | null }) {
  const { t } = useI18n();
  const { notify } = useNotificationCenter();
  const [items, setItems] = useState<NotificationInboxItem[]>([]);
  const [summary, setSummary] = useState<NotificationInboxSummary>({ ...EMPTY_SUMMARY });
  const [filter, setFilter] = useState<NotificationFilter>(() => normalizeNotificationFilter(requestedFilter ?? null));
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  const loadNotifications = useCallback(async () => {
    setStatus("loading");
    try {
      const response = normalizeNotificationInboxResponse(await apiFetch<unknown>("/notifications"));
      setItems(response.items);
      setSummary(response.summary);
      setStatus("ready");
    } catch {
      setStatus("error");
      notify({ tone: "error", title: t("notifications.states.error"), durationMs: 3600 });
    }
  }, [notify, t]);

  useEffect(() => {
    void loadNotifications();
  }, [loadNotifications]);

  useEffect(() => {
    setFilter(normalizeNotificationFilter(requestedFilter ?? null));
  }, [requestedFilter]);

  const actionableCount = useMemo(() => filterNotificationItems(items, "actionable").length, [items]);
  const filters = useMemo(
    () =>
      [
        { value: "all", label: t("notifications.filters.all"), count: summary.total },
        { value: "actionable", label: t("notifications.filters.actionable"), count: actionableCount },
        { value: "unread", label: t("notifications.filters.unread"), count: summary.unread },
        { value: "price", label: t("notifications.filters.price"), count: summary.price },
        { value: "security", label: t("notifications.filters.security"), count: summary.security },
        { value: "digest", label: t("notifications.filters.digest"), count: summary.digest },
        { value: "worker", label: t("notifications.filters.worker"), count: summary.worker },
      ] as const,
    [actionableCount, summary, t],
  );
  const groups = useMemo(
    () => groupNotificationItems(filterNotificationItems(items, filter)),
    [filter, items],
  );

  async function markRead(item: NotificationInboxItem): Promise<void> {
    try {
      await apiFetch(`/notifications/${item.source_type}/${item.source_id}/read`, { method: "POST" });
      await loadNotifications();
      notify({ tone: "success", title: t("notifications.toast.markedRead"), durationMs: 2600 });
    } catch {
      notify({ tone: "error", title: t("notifications.toast.error"), durationMs: 3600 });
    }
  }

  async function markAllRead(): Promise<void> {
    try {
      await apiFetch("/notifications/read-all", { method: "POST" });
      await loadNotifications();
      notify({ tone: "success", title: t("notifications.toast.markedAll"), durationMs: 2600 });
    } catch {
      notify({ tone: "error", title: t("notifications.toast.error"), durationMs: 3600 });
    }
  }

  return (
    <main className="shell stack notifications-page" id="main-content">
      <header className="page-header">
        <div>
          <p className="eyebrow">{t("notifications.hero.kicker")}</p>
          <h1>{t("notifications.pageTitle")}</h1>
          <p>{t("notifications.pageSubtitle")}</p>
        </div>
        <div className="panel-actions">
          <button className="btn-secondary" type="button" onClick={markAllRead} disabled={summary.unread === 0}>
            <CheckCheck size={16} aria-hidden="true" />
            {t("notifications.hero.markAll")}
          </button>
        </div>
      </header>

      <SignalsSectionNav activeSection="inbox" />

      <section className="panel panel-soft notifications-hero">
        <div className="notifications-briefing">
          <span className="notifications-briefing-icon" aria-hidden="true">
            <ListChecks size={20} />
          </span>
          <div>
            <p className="eyebrow">{t("notifications.hero.briefingKicker")}</p>
            <strong>{actionableCount}</strong>
            <h2 className="panel-title">{t("notifications.hero.briefingTitle")}</h2>
            <p className="panel-subtitle">{t("notifications.hero.briefingBody", { unread: summary.unread })}</p>
          </div>
        </div>
        <div className="notifications-summary-grid" aria-label={t("notifications.hero.summaryLabel")}>
          {(["total", "price", "security"] as const).map((key) => (
            <article className="notifications-summary-card" key={key}>
              <span>{t(`notifications.summary.${key}`)}</span>
              <strong>{summary[key]}</strong>
            </article>
          ))}
          <article className="notifications-summary-card">
            <span>{t("notifications.summary.system")}</span>
            <strong>{summary.digest + summary.worker}</strong>
          </article>
        </div>
      </section>

      <section className="panel panel-soft stack section-gap" id="signals-inbox-list">
        <div className="notifications-filterbar" aria-label={t("notifications.filters.label")}>
          {filters.map((option) => {
            const active = filter === option.value;
            return (
              <button
                key={option.value}
                type="button"
                aria-pressed={active}
                className={`btn-ghost btn-compact notifications-filter ${active ? "is-active" : ""}`}
                onClick={() => setFilter(option.value)}
              >
                {option.label}
                <span>{option.count}</span>
              </button>
            );
          })}
        </div>

        <SignalsInboxTimeline
          filter={filter}
          groups={groups}
          status={status}
          onMarkRead={(item) => void markRead(item)}
          onRetry={() => void loadNotifications()}
        />
      </section>
    </main>
  );
}
