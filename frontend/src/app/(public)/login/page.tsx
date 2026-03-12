"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useMemo, useState } from "react";

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
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [fieldError, setFieldError] = useState<{ email?: string; password?: string }>({});
  const [logoutNotice, setLogoutNotice] = useState(false);

  const returnUrl = useMemo(() => {
    return resolvePostAuthUrl(searchParams?.get("returnUrl"));
  }, [searchParams]);

  useEffect(() => {
    const flag = window.localStorage.getItem("viru-logout-notice");
    if (flag) {
      setLogoutNotice(true);
      window.localStorage.removeItem("viru-logout-notice");
    }
  }, []);

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
      router.push(returnUrl);
    } catch (error) {
      const message = error instanceof Error ? error.message : "";
      const networkLike =
        message.includes("Failed to fetch") ||
        message.includes("NetworkError") ||
        message.includes("ERR_FAILED") ||
        message.includes("CORS");
      setError(t(networkLike ? "public.auth.loginNetworkError" : "public.auth.loginError"));
    }
  }

  return (
    <main className="shell" id="main-content">
      {logoutNotice ? (
        <div className="toast notice-success" role="status" aria-live="polite">
          <strong>{t("public.auth.loginLogoutTitle")}</strong>
          <span>{t("public.auth.loginLogoutBody")}</span>
          <div className="toast-actions">
            <button className="btn-ghost" type="button" onClick={() => setLogoutNotice(false)}>
              {t("public.auth.loginLogoutCta")}
            </button>
          </div>
        </div>
      ) : null}
      <div className="page-header">
        <button className="btn-ghost" type="button" onClick={() => router.push("/")}>
          {t("shared.actions.back")}
        </button>
        <div className="page-title">
          <h1>{t("public.auth.loginPageTitle")}</h1>
          <p>{t("public.auth.loginTagline")}</p>
        </div>
        <div className="page-actions">
          <ThemeToggle />
        </div>
      </div>
      <section className="auth-grid">
        <div className="stack-lg">
          <div>
            <h2>{t("public.auth.loginWelcome")}</h2>
            <p>{t("public.auth.loginWelcomeBody")}</p>
          </div>
          <div className="marketing-card">
            <div className="login-loader">
              <span>Viru</span>
              <div className="login-words">
                <span className="login-word">{t("public.auth.loginWordTrack")}</span>
                <span className="login-word">{t("public.auth.loginWordAlerts")}</span>
                <span className="login-word">{t("public.auth.loginWordCompare")}</span>
                <span className="login-word">{t("public.auth.loginWordDrops")}</span>
                <span className="login-word">{t("public.auth.loginWordTravel")}</span>
              </div>
            </div>
            <p className="muted">{t("public.auth.loginMarketingMuted")}</p>
          </div>
        </div>
        <form className="panel form" onSubmit={onSubmit}>
          <label>
            {t("public.auth.loginEmail")}
            <input
              name="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              placeholder="tu@email.com"
            />
            {fieldError.email ? <small className="field-error">{fieldError.email}</small> : null}
          </label>
          <label>
            {t("public.auth.loginPassword")}
            <input
              name="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              placeholder={t("public.auth.passwordPlaceholder")}
            />
            {fieldError.password ? <small className="field-error">{fieldError.password}</small> : null}
          </label>
          {error ? (
            <div className="notice notice-error" role="status" aria-live="polite">
              {error}
            </div>
          ) : null}
          <button type="submit" className="btn-primary">{t("public.auth.loginAction")}</button>
        </form>
      </section>
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
