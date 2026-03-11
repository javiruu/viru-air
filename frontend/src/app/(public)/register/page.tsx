"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useMemo, useState } from "react";

import { apiFetch, apiFetchWithStatus } from "@/modules/shared/api";
import { AuthOut, clearToken, hasToken, saveToken } from "@/modules/shared/auth";
import { resolvePostAuthUrl } from "@/modules/shared/navigation";
import ThemeToggle from "@/modules/shared/ThemeToggle";
import AirLoader from "@/modules/shared/AirLoader";
import { useI18n } from "@/i18n";

function RegisterContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { t } = useI18n();
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
      router.push(returnUrl);
    } catch {
      setError(t("public.auth.registerError"));
    }
  }

  return (
    <main className="shell" id="main-content">
      <div className="page-header">
        <button className="btn-ghost" type="button" onClick={() => router.push("/login")}>
          {t("shared.actions.back")}
        </button>
        <div className="page-title">
          <h1>{t("public.auth.registerPageTitle")}</h1>
          <p>{t("public.auth.registerTagline")}</p>
        </div>
        <div className="page-actions">
          <ThemeToggle />
        </div>
      </div>
      <section className="auth-grid">
        <div className="stack-lg">
          <h2>{t("public.auth.registerIntroTitle")}</h2>
          <p>{t("public.auth.registerIntroBody")}</p>
        </div>
        <form className="panel form" onSubmit={onSubmit}>
          <label>
            {t("public.auth.registerEmail")}
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
            {t("public.auth.registerPassword")}
            <input
              name="password"
              autoComplete="new-password"
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
          <button type="submit" className="btn-primary">{t("public.auth.registerAction")}</button>
        </form>
      </section>
    </main>
  );
}

export default function RegisterPage() {
  const { t } = useI18n();
  return (
    <Suspense
      fallback={
        <main className="shell" id="main-content">
          <section className="panel panel-soft air-loader-section">
            <AirLoader size={0.85} />
            <p className="muted">{t("public.auth.registerLoading")}</p>
          </section>
        </main>
      }
    >
      <RegisterContent />
    </Suspense>
  );
}
