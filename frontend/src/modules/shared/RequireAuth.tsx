"use client";

import type { ReactNode } from "react";
import { useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { apiFetchWithStatus } from "@/modules/shared/api";
import { clearToken, hasToken } from "@/modules/shared/auth";
import { isDashboardDemoAccessEnabled, signInDashboardDemoAccount } from "@/modules/shared/dashboard-demo-session";
import { buildLoginRedirect, currentPathWithSearch } from "@/modules/shared/navigation";
import { Skeleton, SkeletonPanel } from "@/modules/shared/Skeleton";
import { persistLocale, useI18n } from "@/i18n";

type GateState = "checking" | "authed" | "redirecting";
type Me = { locale?: string | null };

export default function RequireAuth({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { t } = useI18n();
  const { notify } = useNotificationCenter();
  const [state, setState] = useState<GateState>("checking");
  const notifiedRef = useRef(false);

  useEffect(() => {
    let active = true;
    const returnUrl = pathname || "/dashboard";
    const loginRedirect = buildLoginRedirect(currentPathWithSearch() || returnUrl);

    async function validateSession() {
      if (!hasToken()) {
        const canUseDashboardDemoAccount = pathname === "/dashboard" && isDashboardDemoAccessEnabled();
        if (canUseDashboardDemoAccount) {
          const didSignIn = await signInDashboardDemoAccount();
          if (!active) return;
          if (didSignIn) {
            notify({
              tone: "success",
              title: t("shared.notifications.dashboardAutoLoginTitle"),
              description: t("shared.notifications.dashboardAutoLoginBody"),
              durationMs: 2800,
            });
          } else {
            notify({
              tone: "warning",
              title: t("shared.notifications.dashboardAutoLoginFailedTitle"),
              description: t("shared.errors.sessionRequired"),
            });
            notifiedRef.current = true;
            setState("redirecting");
            router.replace(loginRedirect);
            return;
          }
        } else {
          if (!notifiedRef.current) {
            notify({
              tone: "warning",
              title: t("shared.notifications.sessionRequiredTitle"),
              description: t("shared.errors.sessionRequired"),
            });
            notifiedRef.current = true;
          }
          setState("redirecting");
          router.replace(loginRedirect);
          return;
        }
      }
      const meResult = await apiFetchWithStatus<Me>("/auth/me", undefined, { timeoutMs: 7000 });
      if (meResult.ok) {
        const me = meResult.data;
        if (me?.locale) {
          persistLocale(me.locale === "en" ? "en" : "es");
        }
        if (active) setState("authed");
        return;
      }

      if (meResult.status === 401) {
        clearToken();
        if (!notifiedRef.current) {
          notify({
            tone: "warning",
            title: t("shared.notifications.sessionExpiredTitle"),
            description: t("shared.errors.sessionExpired"),
          });
          notifiedRef.current = true;
        }
      }
      setState("redirecting");
      router.replace(loginRedirect);
    }

    validateSession();
    return () => {
      active = false;
    };
  }, [notify, pathname, router, t]);

  if (state !== "authed") {
    return (
      <main className="shell auth-guard">
        <SkeletonPanel className="auth-guard-card air-loader-wrap" ariaLabel={t("account.authGuard.title")}>
          <Skeleton variant="pill" width={220} height={18} />
          <Skeleton variant="line" width="74%" />
          <Skeleton variant="line" width="58%" />
        </SkeletonPanel>
      </main>
    );
  }

  return <>{children}</>;
}
