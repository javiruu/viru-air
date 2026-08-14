"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { usePathname } from "next/navigation";

import { useI18n } from "@/i18n";
import { NAV_V1_PRIVATE } from "@/modules/shared/navigationV1";

export default function PrivateNav({ unreadSignals = 0 }: { unreadSignals?: number }) {
  const { t } = useI18n();
  const pathname = usePathname();
  const pathnameValue = pathname ?? "";
  const [menuOpen, setMenuOpen] = useState(false);
  const closeMenu = useCallback(() => setMenuOpen(false), []);

  useEffect(() => {
    document.title = unreadSignals > 0 ? `(${unreadSignals}) Viru Air` : "Viru Air";
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
