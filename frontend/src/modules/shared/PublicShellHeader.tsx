"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import LanguageToggle from "@/modules/shared/LanguageToggle";
import { NAV_V1_PUBLIC } from "@/modules/shared/navigationV1";
import ThemeToggle from "@/modules/shared/ThemeToggle";
import { useI18n } from "@/i18n";

const PUBLIC_NAV_ITEMS = NAV_V1_PUBLIC.filter(
  (item) => item.href !== "/login" && item.href !== "/register",
);

export default function PublicShellHeader() {
  const { t } = useI18n();
  const pathname = usePathname();
  const pathnameValue = pathname ?? "";

  return (
    <div className="shell-header public-shell-header">
      <Link href="/" className="public-shell-brand">
        <span className="public-shell-brand-dot" aria-hidden="true" />
        <span className="public-shell-brand-label">Viru</span>
      </Link>
      <nav
        className="public-shell-nav"
        aria-label={t("shared.a11y.mainNavigation")}
      >
        {PUBLIC_NAV_ITEMS.map((item) => {
          const active = pathnameValue === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`public-shell-nav-link${active ? " is-active" : ""}`}
              aria-current={active ? "page" : undefined}
            >
              {t(item.labelKey)}
            </Link>
          );
        })}
      </nav>
      <div className="public-shell-actions">
        <LanguageToggle />
        <ThemeToggle />
      </div>
    </div>
  );
}
