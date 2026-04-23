"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useMemo, useState } from "react";

import { GlassSignInCard } from "@/components/components/forms/glass-sign-in";
import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { apiFetch, apiFetchWithStatus } from "@/modules/shared/api";
import { AuthOut, clearToken, hasToken, saveToken } from "@/modules/shared/auth";
import { resolvePostAuthUrl } from "@/modules/shared/navigation";
import ThemeToggle from "@/modules/shared/ThemeToggle";
import AirLoader from "@/modules/shared/AirLoader";
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

  const returnUrl = useMemo(() => {
    return resolvePostAuthUrl(searchParams?.get("returnUrl"));
  }, [searchParams]);

  useEffect(() => {
    let active = true;
    if (!hasToken()) return;

    apiFetchWithStatus<{ id: string }>("/auth/me").then((result) => {
      if (!active) return;
      if (result.ok) {
        router.replace("/dashboard");
        return;
      }
      if (result.status === 401) {
        clearToken();
      }
    });

    return () => {
      active = false;
    };
  }, [router]);

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
    try {
      const data = await apiFetch<AuthOut>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: normalizedEmail, password }),
      });
      saveToken(data.access_token);
      notify({
        tone: "success",
        title: t("public.auth.loginSuccess"),
        description: t("shared.notifications.loginSuccessBody"),
      });
      router.push(returnUrl);
    } catch (error) {
      const message = error instanceof Error ? error.message : "";
      const networkLike =
        message.includes("Failed to fetch") ||
        message.includes("NetworkError") ||
        message.includes("ERR_FAILED") ||
        message.includes("CORS");
      const nextError = t(networkLike ? "public.auth.loginNetworkError" : "public.auth.loginError");
      setError(nextError);
      notify({
        tone: "error",
        title: t("shared.notices.error"),
        description: nextError,
      });
    }
  }

  return (
    <main className="shell glass-signin-shell" id="main-content">
      <div className="glass-signin-topbar">
        <button className="btn-ghost" type="button" onClick={() => router.push("/")}>
          {t("shared.actions.back")}
        </button>
        <ThemeToggle />
      </div>
      <GlassSignInCard
        email={email}
        password={password}
        error={error}
        fieldError={fieldError}
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
          <section className="panel panel-soft air-loader-section">
            <AirLoader size={0.85} />
            <p className="muted">{t("public.auth.loginLoading")}</p>
          </section>
        </main>
      }
    >
      <LoginContent />
    </Suspense>
  );
}
