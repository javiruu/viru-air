"use client";

import { useEffect, useState, type ReactNode } from "react";

import AccountMenu from "@/modules/shared/AccountMenu";
import LanguageToggle from "@/modules/shared/LanguageToggle";
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
    apiFetchWithStatus<NotificationSummary>("/notifications/summary", undefined, { timeoutMs: 3500 }).then((result) => {
      if (active && result.ok) setUnreadSignals(result.data.unread);
    });
    return () => { active = false; };
  }, []);

  return (
    <RequireAuth>
      <div className="private-layout">
        <PrivateTopBar>
          <PrivateNav unreadSignals={unreadSignals} />
          <div className="private-account-controls">
            <div className="private-locale-toggle">
              <LanguageToggle />
            </div>
            <div className="private-theme-toggle">
              <ThemeToggle />
            </div>
            <AccountMenu />
          </div>
        </PrivateTopBar>
        <div className="private-content">{children}</div>
        <MobileBottomNav unreadSignals={unreadSignals} />
        <ViruFooterBlock />
      </div>
    </RequireAuth>
  );
}
