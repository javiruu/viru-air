"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useMemo, useState } from "react";

import { GlassSignInCard } from "@/components/components/forms/glass-sign-in";
import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { apiFetchWithStatus } from "@/modules/shared/api";
import { clearToken, hasToken, saveAuthTokens } from "@/modules/shared/auth";
import { isDashboardDemoAccessEnabled, signInDashboardDemoAccount } from "@/modules/shared/dashboard-demo-session";
import { submitLogin } from "@/modules/shared/login-submit";
import { resolvePostAuthUrl } from "@/modules/shared/navigation";
import { SkeletonForm } from "@/modules/shared/Skeleton";
import { useI18n } from "@/i18n";

function LoginContent() {
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
    if (!password.trim()) {
      nextFieldError.password = t("public.auth.passwordRequired");
    }
    if (Object.keys(nextFieldError).length > 0) {
      setFieldError(nextFieldError);
      return;
    }
    setFieldError({});
    const result = await submitLogin(normalizedEmail, password);
    if (result.kind === "success") {
      saveAuthTokens(result.data);
      notify({
        tone: "success",
        title: t("public.auth.loginSuccess"),
        description: t("shared.notifications.loginSuccessBody"),
      });
      router.push(returnUrl);
      return;
    }

    const nextError = t(
      result.kind === "invalid_credentials"
        ? "public.auth.loginError"
        : result.kind === "network_error"
          ? "public.auth.loginNetworkError"
          : "public.auth.loginServerError",
    );
    setError(nextError);
    notify({
      tone: "error",
      title: t("shared.notices.error"),
      description: nextError,
    });
  }

  if (entryState === "checking") {
    return (
      <main className="shell" id="main-content">
        <SkeletonForm className="air-loader-section" ariaLabel={t("public.auth.loginLoading")} />
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
        email={email}
        password={password}
        error={error}
        fieldError={fieldError}
        secondaryHref="/register"
        secondaryIntro={t("public.auth.loginSwitchIntro")}
        secondaryLabel={t("public.auth.loginSwitchAction")}
        t={t}
        onEmailChange={setEmail}
        onPasswordChange={setPassword}
        onForgotPassword={() => router.push("/forgot-password")}
        onSubmit={onSubmit}
      />
    </main>
  );
}

export default function LoginPage() {
  const { t } = useI18n();
  return (
    <Suspense
      fallback={
        <main className="shell" id="main-content">
          <SkeletonForm className="air-loader-section" ariaLabel={t("public.auth.loginLoading")} />
        </main>
      }
    >
      <LoginContent />
    </Suspense>
  );
}
