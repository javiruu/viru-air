"use client";

import Link from "next/link";

import { buildWatchlistViewSearchParams } from "@/modules/shared/useRouteState";
import { formatCurrency } from "@/modules/shared/format";
import type { DashboardNextAction } from "@/modules/dashboard/next-best-action";

type TranslateFn = (key: string, params?: Record<string, string | number>) => string;

function buildWatchHref(action: Extract<DashboardNextAction, { watchId: string }>): string {
  const search = buildWatchlistViewSearchParams({
    origin: action.origin,
    destination: action.destination,
    travelDate: action.travelDate,
  });
  return search ? `/watchlist?${search}` : "/watchlist";
}

function formatStaleLabel(staleHours: number | null, t: TranslateFn): string {
  if (staleHours == null) {
    return t("dashboard.nextAction.reasons.noPriceYet");
  }
  if (staleHours < 48) {
    return t("dashboard.nextAction.reasons.staleHours", { count: staleHours });
  }
  return t("dashboard.nextAction.reasons.staleDays", { count: Math.floor(staleHours / 24) });
}

export function DashboardNextActionCard(args: {
  action: DashboardNextAction;
  locale: string;
  t: TranslateFn;
  onAction: (action: DashboardNextAction) => void;
}) {
  const { action, locale, onAction, t } = args;

  switch (action.kind) {
    case "strong_drop":
      return (
        <div className="dashboard-next-action dashboard-next-action-success">
          <div className="dashboard-next-action-copy">
            <span className="dashboard-next-action-eyebrow">{t("dashboard.nextAction.title")}</span>
            <strong>{t("dashboard.nextAction.messages.strongDrop", { route: action.routeLabel, amount: formatCurrency(action.dropAmount, action.currency, locale) })}</strong>
            <p>{t("dashboard.nextAction.reasons.strongDrop", { price: formatCurrency(action.latestPrice, action.currency, locale) })}</p>
          </div>
          <div className="dashboard-next-action-meta">
            <span className="status-pill success">{t("dashboard.nextAction.badges.priceMove")}</span>
            <Link href={buildWatchHref(action)} className="btn-primary" onClick={() => onAction(action)}>
              {t("dashboard.nextAction.actions.viewWatch")}
            </Link>
          </div>
        </div>
      );
    case "new_low":
      return (
        <div className="dashboard-next-action dashboard-next-action-success">
          <div className="dashboard-next-action-copy">
            <span className="dashboard-next-action-eyebrow">{t("dashboard.nextAction.title")}</span>
            <strong>{t("dashboard.nextAction.messages.newLow", { route: action.routeLabel })}</strong>
            <p>{t("dashboard.nextAction.reasons.newLow", { price: formatCurrency(action.latestPrice, action.currency, locale), previous: formatCurrency(action.previousLowPrice, action.currency, locale) })}</p>
          </div>
          <div className="dashboard-next-action-meta">
            <span className="status-pill success">{t("dashboard.nextAction.badges.newLow")}</span>
            <Link href={buildWatchHref(action)} className="btn-primary" onClick={() => onAction(action)}>
              {t("dashboard.nextAction.actions.viewWatch")}
            </Link>
          </div>
        </div>
      );
    case "best_month":
      return (
        <div className="dashboard-next-action dashboard-next-action-calm">
          <div className="dashboard-next-action-copy">
            <span className="dashboard-next-action-eyebrow">{t("dashboard.nextAction.title")}</span>
            <strong>{t("dashboard.nextAction.messages.bestMonth", { route: action.routeLabel })}</strong>
            <p>{t("dashboard.nextAction.reasons.bestMonth", { count: action.monthlyObservationCount, price: formatCurrency(action.latestPrice, action.currency, locale) })}</p>
          </div>
          <div className="dashboard-next-action-meta">
            <span className="status-pill info">{t("dashboard.nextAction.badges.monthBest")}</span>
            <Link href={buildWatchHref(action)} className="btn-primary" onClick={() => onAction(action)}>
              {t("dashboard.nextAction.actions.viewWatch")}
            </Link>
          </div>
        </div>
      );
    case "unread_alerts":
      return (
        <div className="dashboard-next-action dashboard-next-action-warning">
          <div className="dashboard-next-action-copy">
            <span className="dashboard-next-action-eyebrow">{t("dashboard.nextAction.title")}</span>
            <strong>{t("dashboard.nextAction.messages.unreadAlerts", { count: action.unreadCount })}</strong>
            <p>{t("dashboard.nextAction.reasons.unreadAlerts")}</p>
          </div>
          <div className="dashboard-next-action-meta">
            <span className="status-pill warning">{t("dashboard.nextAction.badges.alerts")}</span>
            <Link href="/notifications" className="btn-primary" onClick={() => onAction(action)}>
              {t("dashboard.nextAction.actions.viewAlerts")}
            </Link>
          </div>
        </div>
      );
    case "stale_watch":
      return (
        <div className="dashboard-next-action dashboard-next-action-warning">
          <div className="dashboard-next-action-copy">
            <span className="dashboard-next-action-eyebrow">{t("dashboard.nextAction.title")}</span>
            <strong>{t("dashboard.nextAction.messages.staleWatch", { route: action.routeLabel })}</strong>
            <p>{t("dashboard.nextAction.reasons.staleWatch", { duration: formatStaleLabel(action.staleHours, t) })}</p>
          </div>
          <div className="dashboard-next-action-meta">
            <span className="status-pill warning">{t("dashboard.nextAction.badges.review")}</span>
            <Link href={buildWatchHref(action)} className="btn-primary" onClick={() => onAction(action)}>
              {t("dashboard.nextAction.actions.viewWatch")}
            </Link>
          </div>
        </div>
      );
    case "onboarding":
      return (
        <div className="dashboard-next-action dashboard-next-action-calm">
          <div className="dashboard-next-action-copy">
            <span className="dashboard-next-action-eyebrow">{t("dashboard.nextAction.title")}</span>
            <strong>{t("dashboard.nextAction.messages.onboarding")}</strong>
            <p>{t("dashboard.nextAction.reasons.onboarding")}</p>
          </div>
          <div className="dashboard-next-action-meta">
            <span className="status-pill info">{t("dashboard.nextAction.badges.start")}</span>
            <Link href="/quick-search" className="btn-primary" onClick={() => onAction(action)}>
              {t("dashboard.nextAction.actions.createWatch")}
            </Link>
          </div>
        </div>
      );
    case "calm":
      return (
        <div className="dashboard-next-action dashboard-next-action-calm">
          <div className="dashboard-next-action-copy">
            <span className="dashboard-next-action-eyebrow">{t("dashboard.nextAction.title")}</span>
            <strong>{t("dashboard.nextAction.messages.calm")}</strong>
            <p>{t("dashboard.nextAction.reasons.calm", { count: action.trackedCount })}</p>
          </div>
          <div className="dashboard-next-action-meta">
            <span className="status-pill info">{t("dashboard.nextAction.badges.calm")}</span>
            <Link href="/watchlist" className="btn-primary" onClick={() => onAction(action)}>
              {t("dashboard.nextAction.actions.openWatchlist")}
            </Link>
          </div>
        </div>
      );
  }
}
