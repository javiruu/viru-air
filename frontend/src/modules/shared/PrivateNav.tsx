"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";

import { useI18n } from "@/i18n";
import { apiFetchWithStatus } from "@/modules/shared/api";
import { NAV_V1_PRIVATE } from "@/modules/shared/navigationV1";

type NotificationSummary = {
  readonly unread: number;
};

export default function PrivateNav() {
  const { t } = useI18n();
  const pathname = usePathname();
  const pathnameValue = pathname ?? "";
  const [unreadSignals, setUnreadSignals] = useState(0);

  useEffect(() => {
    let active = true;
    apiFetchWithStatus<NotificationSummary>("/notifications/summary", undefined, { timeoutMs: 3500 }).then((result) => {
      if (active && result.ok) {
        setUnreadSignals(result.data.unread);
      }
    });
    return () => {
      active = false;
    };
  }, []);

  return (
    <nav className="private-nav" aria-label={t("shared.a11y.mainNavigation")}>
      {NAV_V1_PRIVATE.map((item) => {
        const active = pathnameValue === item.href || pathnameValue.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`private-nav-link${active ? " is-active" : ""}`}
            aria-current={active ? "page" : undefined}
            aria-label={
              item.href === "/notifications" && unreadSignals > 0
                ? t("shared.a11y.notificationsUnread", { count: unreadSignals })
                : undefined
            }
          >
            {t(item.labelKey)}
            {item.href === "/notifications" && unreadSignals > 0 ? (
              <span className="private-nav-badge" aria-hidden="true">{unreadSignals > 99 ? "99+" : unreadSignals}</span>
            ) : null}
          </Link>
        );
      })}
    </nav>
  );
}
