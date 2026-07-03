"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useMemo, useState } from "react";

import { GlassSignInCard } from "@/components/components/forms/glass-sign-in";
import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { apiFetch, apiFetchWithStatus } from "@/modules/shared/api";
import type { AuthOut } from "@/modules/shared/auth";
import { clearToken, hasToken, saveToken } from "@/modules/shared/auth";
import { isDashboardDemoAccessEnabled, signInDashboardDemoAccount } from "@/modules/shared/dashboard-demo-session";
import { resolvePostAuthUrl } from "@/modules/shared/navigation";
import { SkeletonForm } from "@/modules/shared/Skeleton";
import { useI18n } from "@/i18n";

function RegisterContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { t } = useI18n();
  const { notify } = useNotificationCenter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [fieldError, setFieldError] = useState<{ email?: string; password?: string }>({});
  const [entryState, setEntryState] = useState<"checking" | "ready">("checking");

  const returnUrl = useMemo(() => {
    return resolvePostAuthUrl(searchParams?.get("returnUrl"));
  }, [searchParams]);

  useEffect(() => {
    let active = true;
    async function checkEntryRoute() {
      if (!hasToken()) {
        if (isDashboardDemoAccessEnabled()) {
          const didSignIn = await signInDashboardDemoAccount();
          if (!active) return;
          if (didSignIn) {
            router.replace("/dashboard");
            return;
          }
          notify({
            tone: "warning",
            title: t("shared.notifications.dashboardAutoLoginFailedTitle"),
            description: t("shared.errors.sessionRequired"),
          });
        }
        if (active) setEntryState("ready");
        return;
      }

      const result = await apiFetchWithStatus<{ id: string }>("/auth/me");
      if (!active) return;
      if (result.ok) {
        router.replace("/dashboard");
        return;
      }
      if (result.status === 401) {
        clearToken();
      }
      if (active) setEntryState("ready");
    }

    checkEntryRoute();

    return () => {
      active = false;
    };
  }, [notify, router, t]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    const nextFieldError: { email?: string; password?: string } = {};
    const normalizedEmail = email.trim();
    if (!normalizedEmail.includes("@")) {
      nextFieldError.email = t("public.auth.emailInvalid");
    }
    if (password.trim().length < 8) {
      nextFieldError.password = t("public.auth.passwordMin");
    }
    if (Object.keys(nextFieldError).length > 0) {
      setFieldError(nextFieldError);
      return;
    }
    setFieldError({});
    try {
      const data = await apiFetch<AuthOut>("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email: normalizedEmail, password }),
      });
      saveToken(data.access_token);
      notify({
        tone: "success",
        title: t("public.auth.registerSuccess"),
        description: t("shared.notifications.registerSuccessBody"),
      });
      router.push(returnUrl);
    } catch (error) {
      const message = error instanceof Error ? error.message : t("public.auth.registerError");
      setError(message);
      notify({
        tone: "error",
        title: t("shared.notices.error"),
        description: message,
      });
    }
  }

  if (entryState === "checking") {
    return (
      <main className="shell" id="main-content">
        <SkeletonForm className="air-loader-section" ariaLabel={t("public.auth.registerLoading")} />
      </main>
    );
  }

  return (
    <main className="shell glass-signin-shell" id="main-content">
      <div className="glass-signin-topbar">
        <button className="btn-ghost" type="button" onClick={() => router.push("/")}>
          {t("shared.actions.back")}
        </button>
      </div>
      <GlassSignInCard
        variant="register"
        email={email}
        password={password}
        error={error}
        fieldError={fieldError}
        secondaryHref="/login"
        secondaryIntro={t("public.auth.registerSwitchIntro")}
        secondaryLabel={t("public.auth.registerSwitchAction")}
        t={t}
        onEmailChange={setEmail}
        onPasswordChange={setPassword}
        onSubmit={onSubmit}
      />
    </main>
  );
}

export default function RegisterPage() {
  const { t } = useI18n();
  return (
    <Suspense
      fallback={
        <main className="shell" id="main-content">
          <SkeletonForm className="air-loader-section" ariaLabel={t("public.auth.registerLoading")} />
        </main>
      }
    >
      <RegisterContent />
    </Suspense>
  );
}
