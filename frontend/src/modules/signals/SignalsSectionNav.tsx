"use client";

import { Inbox, SlidersHorizontal } from "lucide-react";
import Link from "next/link";

import { useI18n } from "@/i18n";

type SignalsSection = "inbox" | "rules";

type SignalsSectionNavProps = {
  readonly activeSection: SignalsSection;
};

const SIGNAL_SECTIONS = [
  {
    id: "inbox",
    href: "/notifications",
    icon: Inbox,
    labelKey: "notifications.sections.inbox",
    descriptionKey: "notifications.sections.inboxDescription",
  },
  {
    id: "rules",
    href: "/notifications?view=rules",
    icon: SlidersHorizontal,
    labelKey: "notifications.sections.rules",
    descriptionKey: "notifications.sections.rulesDescription",
  },
] as const;

export function SignalsSectionNav({ activeSection }: SignalsSectionNavProps) {
  const { t } = useI18n();

  return (
    <nav className="signals-section-nav" aria-label={t("notifications.sections.label")}>
      {SIGNAL_SECTIONS.map((section) => {
        const Icon = section.icon;
        const active = section.id === activeSection;

        return (
          <Link
            key={section.id}
            className={`signals-section-link${active ? " is-active" : ""}`}
            href={section.href}
            aria-current={active ? "page" : undefined}
          >
            <span className="signals-section-icon" aria-hidden="true">
              <Icon size={18} strokeWidth={1.8} />
            </span>
            <span>
              <strong>{t(section.labelKey)}</strong>
              <small>{t(section.descriptionKey)}</small>
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
