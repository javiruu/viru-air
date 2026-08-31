"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import {
  Bell,
  CircleHelp,
  Compass,
  HeartPulse,
  Hotel,
  LayoutDashboard,
  Menu,
  Route,
  Search,
  Settings2,
  X,
  type LucideIcon,
} from "lucide-react";

import { useI18n } from "@/i18n";
import { NAV_V1_PRIVATE } from "@/modules/shared/navigationV1";
import ViruWordmark from "@/modules/shared/ViruWordmark";

const PRIVATE_NAV_ICONS: Record<(typeof NAV_V1_PRIVATE)[number]["href"], LucideIcon> = {
  "/dashboard": LayoutDashboard,
  "/watchlist": HeartPulse,
  "/puerta-a-puerta": Route,
  "/quick-search": Search,
  "/hoteles": Hotel,
  "/notifications": Bell,
  "/recomendaciones": Compass,
  "/preferencias": Settings2,
  "/soporte/ayuda": CircleHelp,
};

export default function PrivateNav({ unreadSignals = 0 }: { unreadSignals?: number }) {
  const { t } = useI18n();
  const pathname = usePathname();
  const pathnameValue = pathname ?? "";
  const [menuOpen, setMenuOpen] = useState(false);
  const toggleRef = useRef<HTMLButtonElement>(null);
  const navRef = useRef<HTMLElement>(null);
  const closeMenu = useCallback((restoreFocus = true) => {
    setMenuOpen(false);
    if (restoreFocus) {
      window.requestAnimationFrame(() => toggleRef.current?.focus());
    }
  }, []);

  useEffect(() => {
    document.title = unreadSignals > 0 ? `(${unreadSignals}) Viru Air` : "Viru Air";
  }, [unreadSignals]);

  useEffect(() => {
    if (!menuOpen) return;
    const previousOverflow = document.body.style.overflow;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeMenu();
      }
    };
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", closeOnEscape);
    navRef.current?.querySelector<HTMLAnchorElement>(".private-nav-link")?.focus();
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [closeMenu, menuOpen]);

  return (
    <>
      {menuOpen ? <div className="private-nav-backdrop" onClick={() => closeMenu()} aria-hidden="true" /> : null}
      <button
        ref={toggleRef}
        className="private-nav-toggle"
        type="button"
        aria-label={menuOpen ? t("shared.actions.closeMenu") : t("shared.actions.openMenu")}
        aria-expanded={menuOpen}
        aria-controls="private-workspace-navigation"
        onClick={() => setMenuOpen((prev) => !prev)}
      >
        {menuOpen ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
      </button>
      <nav
        ref={navRef}
        id="private-workspace-navigation"
        className={`private-nav${menuOpen ? " open" : ""}`}
        aria-label={t("shared.a11y.mainNavigation")}
      >
        <Link
          href="/dashboard"
          prefetch={false}
          className="private-nav-brand"
          aria-label="Viru Air, ir al panel"
          onClick={() => closeMenu(false)}
        >
          <ViruWordmark />
        </Link>
        <div className="private-nav-links">
          {NAV_V1_PRIVATE.map((item) => {
            const Icon = PRIVATE_NAV_ICONS[item.href];
            const active = pathnameValue === item.href || pathnameValue.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                prefetch={false}
                className={`private-nav-link${active ? " is-active" : ""}`}
                aria-current={active ? "page" : undefined}
                aria-label={
                  item.href === "/notifications" && unreadSignals > 0
                    ? t("shared.a11y.notificationsUnread", { count: unreadSignals })
                    : undefined
                }
                onClick={() => closeMenu(false)}
              >
                <Icon className="private-nav-icon" size={18} strokeWidth={1.8} aria-hidden="true" />
                <span className="private-nav-label">{t(item.labelKey)}</span>
                {item.href === "/notifications" && unreadSignals > 0 ? (
                  <span className="private-nav-badge" aria-hidden="true">{unreadSignals > 99 ? "99+" : unreadSignals}</span>
                ) : null}
              </Link>
            );
          })}
        </div>
      </nav>
    </>
  );
}
