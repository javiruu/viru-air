"use client";

import { FormEvent } from "react";
import { motion, useReducedMotion } from "framer-motion";

type TranslateFn = (key: string, params?: Record<string, string>) => string;

type GlassForgotPasswordCardProps = {
  email: string;
  error: string;
  done: boolean;
  submitting?: boolean;
  t: TranslateFn;
  onEmailChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onBackToLogin: () => void;
};

export function GlassForgotPasswordCard({
  email,
  error,
  done,
  submitting = false,
  t,
  onEmailChange,
  onSubmit,
  onBackToLogin,
}: GlassForgotPasswordCardProps) {
  const shouldReduceMotion = useReducedMotion();

  return (
    <motion.section
      initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.45,
        ease: shouldReduceMotion ? "linear" : [0.16, 1, 0.3, 1],
      }}
      className="glass-forgot-card"
      role="region"
      aria-labelledby="glass-forgot-title"
    >
      <div className="glass-signin-head">
        <span className="glass-signin-chip">{t("public.auth.forgotTitle")}</span>
        <h1 id="glass-forgot-title">{t("public.auth.forgotPageTitle")}</h1>
        <p>{t("public.auth.forgotTagline")}</p>
      </div>

      <form className="glass-signin-form" onSubmit={onSubmit}>
        <label>
          {t("public.auth.forgotEmailLabel")}
          <input
            name="email"
            autoComplete="email"
            value={email}
            onChange={(event) => onEmailChange(event.target.value)}
            type="email"
            placeholder={t("public.auth.emailPlaceholder")}
          />
        </label>

        {error ? (
          <div className="notice notice-error" role="status" aria-live="polite">
            {error}
          </div>
        ) : null}

        {done ? (
          <div className="notice notice-success" role="status" aria-live="polite">
            {t("public.auth.forgotSuccess")}
          </div>
        ) : null}

        <button type="submit" className="btn-primary glass-signin-submit" disabled={submitting}>
          {submitting ? t("shared.states.loading") : t("public.auth.forgotAction")}
        </button>
      </form>

      <div className="glass-forgot-footer">
        <button type="button" className="btn-ghost" onClick={onBackToLogin}>
          {t("public.auth.forgotBackToLogin")}
        </button>
      </div>
    </motion.section>
  );
}
