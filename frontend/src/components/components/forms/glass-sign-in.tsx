"use client";

import { FormEvent } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { BadgeCheck, ShieldCheck, Sparkles } from "lucide-react";

type TranslateFn = (key: string, params?: Record<string, string>) => string;

type GlassSignInCardProps = {
  variant?: "login" | "register";
  email: string;
  password: string;
  error: string;
  fieldError: { email?: string; password?: string };
  submitting?: boolean;
  t: TranslateFn;
  onEmailChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onForgotPassword?: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

const socialProviders = [
  { name: "Google", icon: Sparkles },
  { name: "Twitter", icon: ShieldCheck },
  { name: "GitHub", icon: BadgeCheck },
];

export function GlassSignInCard({
  variant = "login",
  email,
  password,
  error,
  fieldError,
  submitting = false,
  t,
  onEmailChange,
  onPasswordChange,
  onForgotPassword,
  onSubmit,
}: GlassSignInCardProps) {
  const shouldReduceMotion = useReducedMotion();
  const isRegister = variant === "register";
  const chipText = t(isRegister ? "public.auth.registerTitle" : "public.auth.loginTitle");
  const titleText = t(isRegister ? "public.auth.registerPageTitle" : "public.auth.loginPageTitle");
  const taglineText = t(isRegister ? "public.auth.registerTagline" : "public.auth.loginTagline");
  const emailLabel = t(isRegister ? "public.auth.registerEmail" : "public.auth.loginEmail");
  const passwordLabel = t(isRegister ? "public.auth.registerPassword" : "public.auth.loginPassword");
  const submitText = t(isRegister ? "public.auth.registerAction" : "public.auth.loginAction");

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
        <span className="glass-signin-chip">{chipText}</span>
        <h1 id="glass-signin-title">{titleText}</h1>
        <p>{taglineText}</p>
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
          {emailLabel}
          <input
            name="email"
            autoComplete="email"
            value={email}
            onChange={(event) => onEmailChange(event.target.value)}
            type="email"
            placeholder={t("public.auth.emailPlaceholder")}
          />
          {fieldError.email ? <small className="field-error">{fieldError.email}</small> : null}
        </label>

        <label>
          {passwordLabel}
          <input
            name="password"
            autoComplete={isRegister ? "new-password" : "current-password"}
            value={password}
            onChange={(event) => onPasswordChange(event.target.value)}
            type="password"
            placeholder={t("public.auth.passwordPlaceholder")}
          />
          {fieldError.password ? <small className="field-error">{fieldError.password}</small> : null}
        </label>

        {!isRegister ? (
          <div className="glass-signin-subline">
            <label className="glass-signin-remember" htmlFor="remember-session">
              <input id="remember-session" type="checkbox" name="remember" defaultChecked />
              <span className="glass-signin-remember-copy">
                <strong>{t("public.auth.loginRememberMe")}</strong>
                <small>{t("public.auth.loginRememberMeHint")}</small>
              </span>
            </label>
            <button type="button" className="glass-signin-forgot" onClick={onForgotPassword}>
              {t("public.auth.loginForgotPassword")}
            </button>
          </div>
        ) : null}

        {error ? (
          <div className="notice notice-error" role="status" aria-live="polite">
            {error}
          </div>
        ) : null}

        <button type="submit" className="btn-primary glass-signin-submit" disabled={submitting}>
          {submitting ? t("shared.states.loading") : submitText}
        </button>
      </form>

      <p className="glass-signin-legal">{t("public.auth.loginTermsNote")}</p>
    </motion.section>
  );
}
