import type { ReactNode } from "react";

import AccountMenu from "@/modules/shared/AccountMenu";
import ThemeToggle from "@/modules/shared/ThemeToggle";
import RequireAuth from "@/modules/shared/RequireAuth";
import PrivateNav from "@/modules/shared/PrivateNav";

export default function PrivateLayout({ children }: { children: ReactNode }) {
  return (
    <RequireAuth>
      <div className="private-layout">
        <div className="private-account-anchor">
          <PrivateNav />
          <div className="private-account-controls">
            <div className="private-theme-toggle">
              <ThemeToggle />
            </div>
            <AccountMenu />
          </div>
        </div>
        <div className="private-content">{children}</div>
      </div>
    </RequireAuth>
  );
}
