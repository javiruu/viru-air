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
import { apiFetchWithStatus } from "@/modules/shared/api";

type NotificationSummary = { readonly unread: number };

export default function PrivateLayout({ children }: { children: ReactNode }) {
  const [unreadSignals, setUnreadSignals] = useState(0);

  useEffect(() => {
    let active = true;
    let latestRequest = 0;
    const refreshUnreadSignals = () => {
      const requestId = ++latestRequest;
      apiFetchWithStatus<NotificationSummary>("/notifications/summary", undefined, { timeoutMs: 3500 }).then((result) => {
        if (active && requestId === latestRequest && result.ok) setUnreadSignals(result.data.unread);
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
