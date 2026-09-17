"use client";

import { createClient } from "@/lib/supabase/client";

import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, Suspense, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { registerApiV1AuthRegisterPost } from "@/api/generated/auth/auth";
import { GlassSignInCard } from "@/components/components/forms/glass-sign-in";
import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import type { AuthOut } from "@/modules/shared/auth";
import {
  isDashboardDemoAccessEnabled,
  signInDashboardDemoAccount,
} from "@/modules/shared/dashboard-demo-session";
import { resolvePostAuthUrl } from "@/modules/shared/navigation";
import { BoneyardForm } from "@/modules/shared/BoneyardLoad";
import { useI18n } from "@/i18n/shell";

function RegisterContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { t } = useI18n();
  const { notify } = useNotificationCenter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [fieldError, setFieldError] = useState<{ email?: string; password?: string }>({});
  const supabase = createClient();
  const [entryState, setEntryState] = useState<"checking" | "ready">("checking");

  const returnUrl = useMemo(() => {
    return resolvePostAuthUrl(searchParams?.get("returnUrl"));
  }, [searchParams]);

  useEffect(() => {
    let active = true;
    async function checkEntryRoute() {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) {
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

      const { data: { user }, error } = await supabase.auth.getUser();
      if (!active) return;
      if (user) {
        router.replace("/dashboard");
        return;
      }
      if (error?.status === 401) {
        await supabase.auth.signOut();
      }
      if (active) setEntryState("ready");
    }

    checkEntryRoute();

    return () => {
      active = false;
    };
  }, [notify, router, t, supabase.auth]);

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
      const res = await registerApiV1AuthRegisterPost({ email: normalizedEmail, password });
      const data: AuthOut =
        (res as unknown as { data: AuthOut })?.data ?? (res as unknown as AuthOut);
      await supabase.auth.setSession({ access_token: data.access_token, refresh_token: data.refresh_token || "" });;
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
        <BoneyardForm
          name="register-session-load"
          className="air-loader-section"
          ariaLabel={t("public.auth.registerLoading")}
        />
      </main>
    );
  }

  return (
    <main className="shell glass-signin-shell" id="main-content">
      <div className="glass-signin-topbar">
        <Button
          variant="ghost"
          className="btn-ghost"
          type="button"
          onClick={() => router.push("/")}
        >
          {t("shared.actions.back")}
        </Button>
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
          <BoneyardForm
            name="register-session-load"
            className="air-loader-section"
            ariaLabel={t("public.auth.registerLoading")}
          />
        </main>
      }
    >
      <RegisterContent />
    </Suspense>
  );
}
