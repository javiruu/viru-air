"use client";

import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import { apiFetchWithStatus } from "@/modules/shared/api";
import { clearToken, hasToken } from "@/modules/shared/auth";
import { buildLoginRedirect, currentPathWithSearch } from "@/modules/shared/navigation";
import AirLoader from "@/modules/shared/AirLoader";
import { persistLocale, useI18n } from "@/i18n";

type GateState = "checking" | "authed" | "redirecting";
type Me = { locale?: string | null };

export default function RequireAuth({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { t } = useI18n();
  const [state, setState] = useState<GateState>("checking");

  useEffect(() => {
    let active = true;
    const returnUrl = pathname || "/dashboard";
    const loginRedirect = buildLoginRedirect(currentPathWithSearch() || returnUrl);

    async function validateSession() {
      if (!hasToken()) {
        setState("redirecting");
        router.replace(loginRedirect);
        return;
      }
      const meResult = await apiFetchWithStatus<Me>("/auth/me");
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
      }
      setState("redirecting");
      router.replace(loginRedirect);
    }

    validateSession();
    return () => {
      active = false;
    };
  }, [pathname, router]);

  if (state !== "authed") {
    return (
      <main className="shell auth-guard">
        <div className="panel panel-soft auth-guard-card air-loader-wrap">
          <AirLoader />
          <div className="auth-guard-title">{t("account.authGuard.title")}</div>
          <p>{t("account.authGuard.body")}</p>
        </div>
      </main>
    );
  }

  return <>{children}</>;
}
