"use client";

import { FormEvent } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { BadgeCheck, ShieldCheck, Sparkles } from "lucide-react";

type TranslateFn = (key: string, params?: Record<string, string>) => string;

type GlassSignInCardProps = {
  email: string;
  password: string;
  error: string;
  fieldError: { email?: string; password?: string };
  submitting?: boolean;
  t: TranslateFn;
  onEmailChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

const socialProviders = [
  { name: "Google", icon: Sparkles },
  { name: "Twitter", icon: ShieldCheck },
  { name: "GitHub", icon: BadgeCheck },
];

export function GlassSignInCard({
  email,
  password,
  error,
  fieldError,
  submitting = false,
  t,
  onEmailChange,
  onPasswordChange,
  onSubmit,
}: GlassSignInCardProps) {
  const shouldReduceMotion = useReducedMotion();

  return (
    <motion.section
      initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.45,
        ease: shouldReduceMotion ? "linear" : [0.16, 1, 0.3, 1],
      }}
      className="glass-signin-card"
      role="region"
      aria-labelledby="glass-signin-title"
    >
      <div className="glass-signin-head">
        <span className="glass-signin-chip">{t("public.auth.loginTitle")}</span>
        <h1 id="glass-signin-title">{t("public.auth.loginPageTitle")}</h1>
        <p>{t("public.auth.loginTagline")}</p>
      </div>

      <div className="glass-signin-social">
        {socialProviders.map((provider) => (
          <button
            key={provider.name}
            type="button"
            className="glass-signin-social-btn"
            aria-label={`${t("public.auth.loginSocialContinue")} ${provider.name}`}
          >
            <provider.icon size={16} aria-hidden="true" />
            <span>{provider.name}</span>
          </button>
        ))}
      </div>

      <div className="glass-signin-divider" aria-hidden="true">
        <span>{t("public.auth.loginOr")}</span>
      </div>

      <form className="glass-signin-form" onSubmit={onSubmit}>
        <label>
          {t("public.auth.loginEmail")}
          <input
            name="email"
            autoComplete="email"
            value={email}
            onChange={(event) => onEmailChange(event.target.value)}
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
            onChange={(event) => onPasswordChange(event.target.value)}
            type="password"
            placeholder={t("public.auth.passwordPlaceholder")}
          />
          {fieldError.password ? <small className="field-error">{fieldError.password}</small> : null}
        </label>

        <div className="glass-signin-subline">
          <label className="glass-signin-remember">
            <input type="checkbox" name="remember" />
            <span>{t("public.auth.loginRememberMe")}</span>
          </label>
          <button type="button" className="glass-signin-forgot">
            {t("public.auth.loginForgotPassword")}
          </button>
        </div>

        {error ? (
          <div className="notice notice-error" role="status" aria-live="polite">
            {error}
          </div>
        ) : null}

        <button type="submit" className="btn-primary glass-signin-submit" disabled={submitting}>
          {submitting ? t("shared.states.loading") : t("public.auth.loginAction")}
        </button>
      </form>

      <p className="glass-signin-legal">{t("public.auth.loginTermsNote")}</p>
    </motion.section>
  );
}
