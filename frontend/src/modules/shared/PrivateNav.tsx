"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useI18n } from "@/i18n";
import { NAV_V1_PRIVATE } from "@/modules/shared/navigationV1";

export default function PrivateNav() {
  const { t } = useI18n();
  const pathname = usePathname();
  const pathnameValue = pathname ?? "";

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
          >
            {t(item.labelKey)}
          </Link>
        );
      })}
    </nav>
  );
}
