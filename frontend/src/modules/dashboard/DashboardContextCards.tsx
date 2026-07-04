"use client";

import Link from "next/link";

import type { DashboardFoundForYou } from "@/modules/dashboard/found-for-you";
import { buildWatchlistViewSearchParams } from "@/modules/shared/useRouteState";
import { formatCurrency, formatRelativeTime } from "@/modules/shared/format";
import type { ResumeSearchSnapshot } from "@/modules/quick-search/resume-search";

type TranslateFn = (key: string, params?: Record<string, string | number>) => string;

function buildFoundHref(item: DashboardFoundForYou): string {
  const search = buildWatchlistViewSearchParams({
    origin: item.origin,
    destination: item.destination,
    travelDate: item.travelDate,
  });
  return search ? `/watchlist?${search}` : "/watchlist";
}

export function DashboardContextCards(args: {
  foundForYou: DashboardFoundForYou | null;
  locale: string;
  resumeSnapshot: ResumeSearchSnapshot | null;
  t: TranslateFn;
  onDismissFound: () => void;
  onDismissResume: () => void;
}) {
  const { foundForYou, locale, onDismissFound, onDismissResume, resumeSnapshot, t } = args;
  if (!foundForYou && !resumeSnapshot) return null;

  return (
    <section className="dashboard-context-grid">
      {foundForYou ? (
        <article className="dashboard-context-card dashboard-context-card-found">
          <div className="dashboard-context-copy">
            <span className="dashboard-context-eyebrow">{t("dashboard.foundForYou.title")}</span>
            <strong>
              {foundForYou.matchedCountry
                ? t("dashboard.foundForYou.messageMatchedCountry", {
                    country: foundForYou.matchedCountry,
                    origin: foundForYou.origin,
                    route: foundForYou.routeLabel,
                    price: formatCurrency(foundForYou.currentPrice, foundForYou.currency, locale),
                  })
                : t("dashboard.foundForYou.messageGeneric", {
                    route: foundForYou.routeLabel,
                    price: formatCurrency(foundForYou.currentPrice, foundForYou.currency, locale),
                  })}
            </strong>
            <p>
              {foundForYou.matchedCountry
                ? t("dashboard.foundForYou.reasonMatchedCountry", { country: foundForYou.matchedCountry })
                : t("dashboard.foundForYou.reasonGeneric")}
            </p>
          </div>
          <div className="dashboard-context-actions">
            <Link href={buildFoundHref(foundForYou)} className="btn-secondary">
              {t("dashboard.foundForYou.primaryAction")}
            </Link>
            <button type="button" className="link-subtle" onClick={onDismissFound}>
              {t("dashboard.foundForYou.secondaryAction")}
            </button>
          </div>
        </article>
      ) : null}

      {resumeSnapshot ? (
        <article className="dashboard-context-card dashboard-context-card-resume">
          <div className="dashboard-context-copy">
            <span className="dashboard-context-eyebrow">{t("dashboard.resumeSearch.title")}</span>
            <strong>{resumeSnapshot.summary}</strong>
            <p>{resumeSnapshot.detail}</p>
            <span className="dashboard-context-meta">
              {t("dashboard.resumeSearch.savedAt", {
                relative: formatRelativeTime(resumeSnapshot.savedAt, locale),
              })}
            </span>
          </div>
          <div className="dashboard-context-actions">
            <Link href={resumeSnapshot.href} className="btn-secondary">
              {t("dashboard.resumeSearch.primaryAction")}
            </Link>
            <button type="button" className="link-subtle" onClick={onDismissResume}>
              {t("dashboard.resumeSearch.secondaryAction")}
            </button>
          </div>
        </article>
      ) : null}
    </section>
  );
}
