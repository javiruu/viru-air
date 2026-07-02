"use client";

import { useCallback, useEffect, useState } from "react";

import { useI18n } from "@/i18n";
import { trackEvent } from "@/modules/shared/analytics";
import { isDashboardLoginRequired, saveDashboardLoginRequired } from "@/modules/shared/auth";

export function DashboardAccessSwitch() {
  const { t } = useI18n();
  const [dashboardLoginRequired, setDashboardLoginRequired] = useState(true);

  useEffect(() => {
    setDashboardLoginRequired(isDashboardLoginRequired());
  }, []);

  const handleDashboardAccessChange = useCallback((isAutoEntryEnabled: boolean) => {
    const nextLoginRequired = !isAutoEntryEnabled;
    setDashboardLoginRequired(nextLoginRequired);
    saveDashboardLoginRequired(nextLoginRequired);
    trackEvent("dashboard_access_mode_changed", {
      area: "dashboard",
      mode: nextLoginRequired ? "login_required" : "demo_auto_entry",
    });
  }, []);

  const dashboardAutoEntryEnabled = !dashboardLoginRequired;

  return (
    <label className="dashboard-access-toggle">
      <span className="dashboard-access-toggle__copy">
        <strong>{t("dashboard.access.title")}</strong>
        <span>
          {dashboardAutoEntryEnabled ? t("dashboard.access.demoMode") : t("dashboard.access.loginRequired")}
        </span>
      </span>
      <input
        type="checkbox"
        checked={dashboardAutoEntryEnabled}
        onChange={(event) => handleDashboardAccessChange(event.target.checked)}
        aria-label={t("dashboard.access.ariaLabel")}
      />
      <span className="dashboard-access-toggle__track" aria-hidden="true">
        <span className="dashboard-access-toggle__thumb" />
      </span>
    </label>
  );
}
