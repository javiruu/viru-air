"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
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
  const [menuOpen, setMenuOpen] = useState(false);
  const closeMenu = useCallback(() => setMenuOpen(false), []);

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

  useEffect(() => {
    document.title = unreadSignals > 0 ? `(${unreadSignals}) Viru` : "Viru";
  }, [unreadSignals]);

  return (
    <>
      {menuOpen ? <div className="private-nav-backdrop" onClick={closeMenu} aria-hidden="true" /> : null}
      <nav
        className={`private-nav${menuOpen ? " open" : ""}`}
        aria-label={t("shared.a11y.mainNavigation")}
      >
      <button
        className="private-nav-toggle"
        type="button"
        aria-label={menuOpen ? t("shared.actions.closeMenu") : t("shared.actions.openMenu")}
        aria-expanded={menuOpen}
        onClick={() => setMenuOpen((prev) => !prev)}
      >
        <span className="private-nav-toggle-bar" />
        <span className="private-nav-toggle-bar" />
        <span className="private-nav-toggle-bar" />
      </button>
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
            onClick={closeMenu}
          >
            {t(item.labelKey)}
            {item.href === "/notifications" && unreadSignals > 0 ? (
              <span className="private-nav-badge" aria-hidden="true">{unreadSignals > 99 ? "99+" : unreadSignals}</span>
            ) : null}
          </Link>
        );
      })}
    </nav>
    </>
  );
}
