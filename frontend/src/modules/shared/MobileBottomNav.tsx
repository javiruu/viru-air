"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bell, Eye, LayoutDashboard, Search } from "lucide-react";

import { useI18n } from "@/i18n";

const BOTTOM_NAV_ITEMS = [
  { href: "/dashboard", icon: LayoutDashboard, labelKey: "shared.footer.links.dashboard" as const },
  { href: "/watchlist", icon: Eye, labelKey: "shared.footer.links.watchlist" as const },
  { href: "/quick-search", icon: Search, labelKey: "shared.footer.links.quickSearch" as const },
  { href: "/notifications", icon: Bell, labelKey: "shared.footer.links.notifications" as const },
] as const;

export default function MobileBottomNav({ unreadSignals = 0 }: { unreadSignals?: number }) {
  const { t } = useI18n();
  const pathname = usePathname();
  const pathnameValue = pathname ?? "";

  return (
    <nav className="mobile-bottom-nav" aria-label={t("shared.a11y.mainNavigation")}>
      {BOTTOM_NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        const active = pathnameValue === item.href || pathnameValue.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`mobile-bottom-nav-link${active ? " is-active" : ""}`}
            aria-current={active ? "page" : undefined}
          >
            <span className="mobile-bottom-nav-icon">
              <Icon size={22} strokeWidth={active ? 2.5 : 1.8} />
              {item.href === "/notifications" && unreadSignals > 0 ? (
                <span className="mobile-bottom-nav-badge" aria-hidden="true">
                  {unreadSignals > 99 ? "99+" : unreadSignals}
                </span>
              ) : null}
            </span>
            <span className="mobile-bottom-nav-label">{t(item.labelKey)}</span>
          </Link>
        );
      })}
    </nav>
  );
}
