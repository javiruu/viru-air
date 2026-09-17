"use client";

import { useEffect, useState, type ReactNode } from "react";

import AccountMenu from "@/modules/shared/AccountMenu";
import LanguageSelector from "@/modules/shared/LanguageSelector";
import MobileBottomNav from "@/modules/shared/MobileBottomNav";
import PrivateTopBar from "@/modules/shared/PrivateTopBar";
import ThemeToggle from "@/modules/shared/ThemeToggle";
import RequireAuth from "@/modules/shared/RequireAuth";
import PrivateNav from "@/modules/shared/PrivateNav";
import ViruFooterBlock from "@/modules/shared/ViruFooterBlock";
import { getNotificationsSummaryApiV1NotificationsSummaryGet } from "@/api/generated/notifications/notifications";

type NotificationSummary = { readonly unread: number };

export default function PrivateLayout({ children }: { children: ReactNode }) {
  const [unreadSignals, setUnreadSignals] = useState(0);

  useEffect(() => {
    let active = true;
    let latestRequest = 0;
    const refreshUnreadSignals = (event?: Event) => {
      if (event instanceof CustomEvent && event.detail?.unread === 0) {
        latestRequest += 1;
        setUnreadSignals(0);
        return;
      }
      const requestId = ++latestRequest;
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3500);

      getNotificationsSummaryApiV1NotificationsSummaryGet({ signal: controller.signal })
        .then((result) => {
          clearTimeout(timeoutId);
          if (active && requestId === latestRequest) {
            const payload = result as unknown as { unread: number };
            setUnreadSignals(payload.unread);
          }
        })
        .catch(() => {
          clearTimeout(timeoutId);
        });
    };

    refreshUnreadSignals();
    window.addEventListener("viru:notifications-changed", refreshUnreadSignals);
    return () => {
      active = false;
      window.removeEventListener("viru:notifications-changed", refreshUnreadSignals);
    };
  }, []);

  return (
    <RequireAuth>
      <div className="private-layout">
        <PrivateNav unreadSignals={unreadSignals} />
        <div className="private-workspace">
          <PrivateTopBar>
            <div className="private-account-controls">
              <div className="private-locale-toggle">
                <LanguageSelector />
              </div>
              <div className="private-theme-toggle">
                <ThemeToggle />
              </div>
              <AccountMenu />
            </div>
          </PrivateTopBar>
          <div className="private-content">{children}</div>
          <ViruFooterBlock />
        </div>
        <MobileBottomNav unreadSignals={unreadSignals} />
      </div>
    </RequireAuth>
  );
}
