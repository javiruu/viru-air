"use client";

import Link from "next/link";
import { RadioTower, ShieldCheck, Tags, Wrench } from "lucide-react";

import { useI18n } from "@/i18n";
import type {
  NotificationFilter,
  NotificationInboxItem,
  NotificationTimelineGroup,
} from "@/modules/signals/notificationInboxModel";
import { formatRelativeTime } from "@/modules/shared/format";

const CATEGORY_ICONS = {
  price: Tags,
  security: ShieldCheck,
  digest: RadioTower,
  worker: Wrench,
} as const;

type SignalsInboxTimelineProps = {
  filter: NotificationFilter;
  groups: NotificationTimelineGroup[];
  status: "loading" | "ready" | "error";
  onMarkRead: (item: NotificationInboxItem) => void;
  onRetry: () => void;
};

export function SignalsInboxTimeline({
  filter,
  groups,
  status,
  onMarkRead,
  onRetry,
}: SignalsInboxTimelineProps) {
  const { t, localeTag } = useI18n();

  if (status === "loading") {
    return (
      <div className="notifications-empty" role="status" aria-live="polite">
        <div className="notifications-radar" aria-hidden="true" />
        <strong>{t("notifications.states.loading")}</strong>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="notifications-empty" role="alert">
        <div className="notifications-radar" aria-hidden="true" />
        <strong>{t("notifications.states.error")}</strong>
        <button className="btn-secondary btn-compact" type="button" onClick={onRetry}>
          {t("notifications.states.retry")}
        </button>
      </div>
    );
  }

  if (groups.length === 0) {
    const actionable = filter === "actionable";
    return (
      <div className="notifications-empty">
        <div className="notifications-radar" aria-hidden="true" />
        <strong>{t(actionable ? "notifications.states.actionableEmpty" : "notifications.states.empty")}</strong>
        <p>{t(actionable ? "notifications.states.actionableEmptyBody" : "notifications.states.emptyBody")}</p>
      </div>
    );
  }

  return (
    <div className="notifications-timeline">
      {groups.map((group) => (
        <section className="notifications-timeline-group" key={group.key}>
          <div className="notifications-timeline-heading">
            <span>{t(`notifications.timeline.${group.key}`)}</span>
            <small>{t("notifications.timeline.count", { count: group.items.length })}</small>
          </div>
          <div className="notifications-timeline-list">
            {group.items.map((item) => {
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
                        {t(`notifications.row.actions.${item.category}`)}
                      </Link>
                    ) : null}
                    {!item.is_read ? (
                      <button
                        className="btn-secondary btn-compact"
                        type="button"
                        onClick={() => onMarkRead(item)}
                      >
                        {t("notifications.row.markRead")}
                      </button>
                    ) : null}
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
