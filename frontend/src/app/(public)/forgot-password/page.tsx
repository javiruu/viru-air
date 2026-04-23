"use client";

import { FormEvent, Suspense, useState } from "react";
import { useRouter } from "next/navigation";

import { GlassForgotPasswordCard } from "@/components/components/forms/glass-forgot-password";
import ThemeToggle from "@/modules/shared/ThemeToggle";
import AirLoader from "@/modules/shared/AirLoader";
import { useI18n } from "@/i18n";

function ForgotPasswordContent() {
  const router = useRouter();
  const { t } = useI18n();

  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setDone(false);

    const normalizedEmail = email.trim();
    if (!normalizedEmail.includes("@")) {
      setError(t("public.auth.emailInvalid"));
      return;
    }

    setSubmitting(true);
    try {
      // Backend reset endpoint is not yet available; keep response generic for security.
      await new Promise((resolve) => setTimeout(resolve, 420));
      setDone(true);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="shell glass-signin-shell" id="main-content">
      <div className="glass-signin-topbar">
        <button className="btn-ghost" type="button" onClick={() => router.push("/login")}>
          {t("shared.actions.back")}
        </button>
        <ThemeToggle />
      </div>
      <GlassForgotPasswordCard
        email={email}
        error={error}
        done={done}
        submitting={submitting}
        t={t}
        onEmailChange={setEmail}
        onSubmit={onSubmit}
        onBackToLogin={() => router.push("/login")}
      />
    </main>
  );
}

export default function ForgotPasswordPage() {
  const { t } = useI18n();
  return (
    <Suspense
      fallback={
        <main className="shell" id="main-content">
          <section className="panel panel-soft air-loader-section">
            <AirLoader size={0.85} />
            <p className="muted">{t("public.auth.forgotLoading")}</p>
          </section>
        </main>
      }
    >
      <ForgotPasswordContent />
    </Suspense>
  );
}
