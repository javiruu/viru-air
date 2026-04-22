"use client";

import { FormEvent, ReactNode, useMemo } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowLeft,
  BadgeCheck,
  CalendarClock,
  Camera,
  LogOut,
  Mail,
  Monitor,
  Save,
  ShieldCheck,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";

import AirLoader from "@/modules/shared/AirLoader";

export type GlassProfileData = {
  display_name: string;
  email: string;
  avatar_url: string | null;
  status: string;
  created_at: string;
};

export type GlassProfileSession = {
  id: string;
  device: string;
  ip: string | null;
  last_seen: string;
  created_at: string;
  is_active: boolean;
};

export type GlassProfileToastState = { tone: "success" | "error"; message: string } | null;

type TranslateFn = (key: string, params?: Record<string, string>) => string;

type GlassProfileSettingsCardProps = {
  profile: GlassProfileData | null;
  sessions: GlassProfileSession[];
  saving: boolean;
  closingSessions: boolean;
  toast: GlassProfileToastState;
  confirmDeleteOpen: boolean;
  confirmText: string;
  localeTag: string;
  t: TranslateFn;
  onBack: () => void;
  onFieldChange: (key: "display_name" | "avatar_url", value: string) => void;
  onSave: (event: FormEvent<HTMLFormElement>) => void;
  onCloseAllSessions: () => void;
  onOpenDelete: () => void;
  onCloseDelete: () => void;
  onConfirmTextChange: (value: string) => void;
  onDeleteAccount: () => void;
};

function getInitials(profile: GlassProfileData | null): string {
  const source = profile?.display_name?.trim() || profile?.email?.trim() || "US";
  const parts = source.split(/[\s.@_-]+/).filter(Boolean);
  if (parts.length === 0) return "US";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
}

function GlassInfoField({
  icon,
  label,
  children,
}: {
  icon: ReactNode;
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="account-profile-field">
      <span className="account-profile-field-head">
        <span className="account-profile-field-icon" aria-hidden="true">
          {icon}
        </span>
        <span>{label}</span>
      </span>
      {children}
    </label>
  );
}

export function GlassProfileSettingsCard({
  profile,
  sessions,
  saving,
  closingSessions,
  toast,
  confirmDeleteOpen,
  confirmText,
  localeTag,
  t,
  onBack,
  onFieldChange,
  onSave,
  onCloseAllSessions,
  onOpenDelete,
  onCloseDelete,
  onConfirmTextChange,
  onDeleteAccount,
}: GlassProfileSettingsCardProps) {
  const statusClass = useMemo(() => {
    if (!profile?.status) return "status-degraded";
    const normalized = profile.status.toLowerCase();
    return normalized.includes("activa") || normalized.includes("active") ? "status-ok" : "status-degraded";
  }, [profile?.status]);

  const formattedCreatedAt = useMemo(() => {
    if (!profile?.created_at) return "--";
    return new Date(profile.created_at).toLocaleDateString(localeTag, {
      year: "numeric",
      month: "short",
      day: "2-digit",
    });
  }, [profile?.created_at, localeTag]);

  const accountAgeLabel = useMemo(() => {
    if (!profile?.created_at) return "--";
    return new Date(profile.created_at).toLocaleString(localeTag, {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  }, [profile?.created_at, localeTag]);

  const lastAccessLabel = useMemo(() => {
    if (!sessions[0]?.last_seen) return "--";
    return new Date(sessions[0].last_seen).toLocaleDateString(localeTag, {
      month: "short",
      day: "2-digit",
    });
  }, [localeTag, sessions]);

  const initials = useMemo(() => getInitials(profile), [profile]);
  const confirmKeyword = t("account.profile.confirmKeyword");

  if (!profile) {
    return (
      <main className="shell account-profile-shell" id="main-content">
        <div className="account-profile-topbar">
          <button className="account-profile-navlink" type="button" onClick={onBack}>
            <ArrowLeft size={16} />
            <span>{t("shared.actions.back")}</span>
          </button>
        </div>

        <section className="account-profile-glass account-profile-loading">
          <div className="account-profile-loading-copy">
            <span className="account-profile-kicker">{t("account.profile.identityTitle")}</span>
            <h2>{t("account.profile.pageSubtitle")}</h2>
            <p>{t("shared.states.loading")}</p>
          </div>
          <div className="air-loader-section">
            <AirLoader size={0.9} />
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="shell account-profile-shell" id="main-content">
      <motion.div
        className="account-profile-topbar"
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: "easeOut" }}
      >
        <button className="account-profile-navlink" type="button" onClick={onBack}>
          <ArrowLeft size={16} />
          <span>{t("shared.actions.back")}</span>
        </button>
        <div className="account-profile-heading">
          <div className="account-profile-heading-row">
            <span className="account-profile-kicker">UI TripleD Adaptation</span>
            <span className={`account-profile-status ${statusClass}`}>
              <BadgeCheck size={14} />
              <span>{profile.status}</span>
            </span>
          </div>
          <h1>{t("account.profile.title")}</h1>
          <p>{t("account.profile.pageSubtitle")}</p>
        </div>
      </motion.div>

      <motion.section
        className="account-profile-glass"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.42, ease: "easeOut" }}
      >
        <div className="account-profile-orb account-profile-orb-primary" aria-hidden="true" />
        <div className="account-profile-orb account-profile-orb-secondary" aria-hidden="true" />

        <div className="account-profile-grid">
          <div className="account-profile-main">
            <motion.section
              className="account-profile-hero"
              initial={{ opacity: 0, scale: 0.985 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.32, ease: "easeOut", delay: 0.05 }}
            >
              <div className="account-profile-hero-copy">
                <span className="account-profile-kicker">{t("account.profile.identityTitle")}</span>
                <h2>{profile.display_name || profile.email}</h2>
                <p>{t("account.profile.subtitle")}</p>
              </div>

              <div className="account-profile-identity">
                <div className="account-profile-avatar-shell">
                  {profile.avatar_url ? (
                    <>
                      {/* The avatar URL is user-provided and not whitelisted for next/image. */}
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        className="account-profile-avatar"
                        src={profile.avatar_url}
                        alt={profile.display_name || profile.email}
                      />
                    </>
                  ) : (
                    <div className="account-profile-avatar account-profile-avatar-fallback" aria-hidden="true">
                      {initials}
                    </div>
                  )}

                  <div className="account-profile-avatar-badge" aria-hidden="true">
                    <Camera size={16} />
                  </div>
                </div>

                <div className="account-profile-meta">
                  <div className="account-profile-meta-line">
                    <strong>{profile.email}</strong>
                    <div className="account-profile-meta-pillset">
                      <span className={`account-profile-status ${statusClass}`}>
                        <ShieldCheck size={14} />
                        <span>{profile.status}</span>
                      </span>
                      <span className="account-profile-status account-profile-status-neutral">
                        <Sparkles size={14} />
                        <span>{t("account.profile.createdAt")}</span>
                      </span>
                    </div>
                  </div>

                  <div className="account-profile-meta-grid">
                    <div className="account-profile-meta-card">
                      <span>{t("account.profile.createdLabel")}</span>
                      <strong>{formattedCreatedAt}</strong>
                    </div>
                    <div className="account-profile-meta-card">
                      <span>{t("account.profile.sessionsTitle")}</span>
                      <strong>{sessions.length}</strong>
                    </div>
                    <div className="account-profile-meta-card">
                      <span>{t("account.profile.lastAccess")}</span>
                      <strong>{lastAccessLabel}</strong>
                    </div>
                  </div>

                  <div className="account-profile-banner">
                    <span className="account-profile-banner-label">Glass Profile Settings Card</span>
                    <p>
                      Profile identity, recent sessions, and destructive actions are now grouped inside a single
                      reusable glass settings component instead of living inline in the route.
                    </p>
                  </div>
                </div>
              </div>
            </motion.section>

            <motion.section
              className="account-profile-panel"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, ease: "easeOut", delay: 0.12 }}
            >
              <div className="account-profile-panel-header">
                <div className="account-profile-panel-title">
                  <span className="account-profile-panel-icon" aria-hidden="true">
                    <Sparkles size={18} />
                  </span>
                  <div>
                    <span className="account-profile-kicker">{t("account.profile.identityTitle")}</span>
                    <h3>{t("account.profile.pageSubtitle")}</h3>
                  </div>
                </div>
                <p>{t("account.profile.identityHint")}</p>
              </div>

              <form className="account-profile-form" onSubmit={onSave}>
                <GlassInfoField icon={<Sparkles size={15} />} label={t("account.profile.displayNameLabel")}>
                  <input
                    type="text"
                    name="display_name"
                    value={profile.display_name}
                    onChange={(event) => onFieldChange("display_name", event.target.value)}
                  />
                </GlassInfoField>

                <GlassInfoField icon={<Camera size={15} />} label={t("account.profile.avatarLabel")}>
                  <input
                    type="url"
                    name="avatar_url"
                    value={profile.avatar_url || ""}
                    onChange={(event) => onFieldChange("avatar_url", event.target.value)}
                  />
                </GlassInfoField>

                <GlassInfoField icon={<Mail size={15} />} label={t("account.profile.emailLabel")}>
                  <input type="email" name="email" value={profile.email} readOnly />
                </GlassInfoField>

                <GlassInfoField icon={<CalendarClock size={15} />} label={t("account.profile.createdLabel")}>
                  <input type="text" value={accountAgeLabel} readOnly />
                </GlassInfoField>

                <div className="account-profile-actions">
                  <button
                    type="submit"
                    className="account-profile-button account-profile-button-primary"
                    disabled={saving}
                  >
                    <Save size={16} />
                    <span>{saving ? t("account.profile.saving") : t("account.profile.saveAction")}</span>
                  </button>
                </div>
              </form>
            </motion.section>
          </div>

          <aside className="account-profile-side">
            <motion.section
              className="account-profile-panel account-profile-panel-soft"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, ease: "easeOut", delay: 0.18 }}
            >
              <div className="account-profile-panel-header">
                <div className="account-profile-panel-title">
                  <span className="account-profile-panel-icon" aria-hidden="true">
                    <Monitor size={18} />
                  </span>
                  <div>
                    <span className="account-profile-kicker">{t("account.profile.sessionsTitle")}</span>
                    <h3>{t("account.profile.sessionsTitle")}</h3>
                  </div>
                </div>
                <p>{t("account.profile.sessionsHint")}</p>
              </div>

              {sessions.length === 0 ? (
                <p className="account-profile-empty">{t("account.profile.sessionsEmpty")}</p>
              ) : (
                <div className="account-profile-session-list">
                  {sessions.map((session) => (
                    <div key={session.id} className="account-profile-session-row">
                      <div className="account-profile-session-copy">
                        <div className="account-profile-session-label">
                          <span className="account-profile-session-icon" aria-hidden="true">
                            <Monitor size={15} />
                          </span>
                          <strong>{session.device}</strong>
                        </div>
                        <p>
                          {t("account.profile.lastAccess")}: {new Date(session.last_seen).toLocaleString(localeTag)}
                        </p>
                        {session.ip ? <span>{session.ip}</span> : null}
                      </div>
                      <span className={`account-profile-status ${session.is_active ? "status-ok" : "status-degraded"}`}>
                        {session.is_active ? <BadgeCheck size={14} /> : <LogOut size={14} />}
                        <span>
                          {session.is_active ? t("account.profile.sessionActive") : t("account.profile.sessionClosed")}
                        </span>
                      </span>
                    </div>
                  ))}
                </div>
              )}

              <div className="account-profile-actions">
                <button
                  type="button"
                  className="account-profile-button account-profile-button-secondary"
                  onClick={onCloseAllSessions}
                  disabled={closingSessions}
                >
                  <LogOut size={16} />
                  <span>
                    {closingSessions ? t("account.profile.closingSessions") : t("account.profile.closeAllSessions")}
                  </span>
                </button>
              </div>
            </motion.section>

            <motion.section
              className="account-profile-panel account-profile-danger"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, ease: "easeOut", delay: 0.24 }}
            >
              <div className="account-profile-panel-header">
                <div className="account-profile-panel-title">
                  <span className="account-profile-panel-icon account-profile-panel-icon-danger" aria-hidden="true">
                    <AlertTriangle size={18} />
                  </span>
                  <div>
                    <span className="account-profile-kicker">{t("account.profile.dangerTitle")}</span>
                    <h3>{t("account.profile.dangerTitle")}</h3>
                  </div>
                </div>
                <p>{t("account.profile.dangerHint")}</p>
              </div>

              <p className="account-profile-danger-copy">{t("account.profile.deleteNote")}</p>

              <div className="account-profile-actions">
                <button
                  type="button"
                  className="account-profile-button account-profile-button-danger"
                  onClick={onOpenDelete}
                >
                  <Trash2 size={16} />
                  <span>{t("account.profile.deleteAction")}</span>
                </button>
              </div>
            </motion.section>
          </aside>
        </div>
      </motion.section>

      <AnimatePresence>
        {confirmDeleteOpen ? (
          <motion.div
            className="modal-overlay"
            onClick={onCloseDelete}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.section
              className="modal-card account-profile-delete-modal"
              role="dialog"
              aria-modal="true"
              aria-labelledby="delete-account-title"
              onClick={(event) => event.stopPropagation()}
              initial={{ opacity: 0, y: 20, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 12, scale: 0.98 }}
              transition={{ duration: 0.22, ease: "easeOut" }}
            >
              <div className="modal-header">
                <div>
                  <h2 id="delete-account-title">{t("account.profile.confirmTitle")}</h2>
                  <p className="panel-note">{t("account.profile.confirmHint", { keyword: confirmKeyword })}</p>
                </div>
                <button
                  className="modal-close"
                  type="button"
                  onClick={onCloseDelete}
                  aria-label={t("account.profile.confirmClose")}
                >
                  <X size={16} />
                </button>
              </div>
              <label className="field" htmlFor="confirm-delete">
                {t("account.profile.confirmLabel")}
                <input
                  id="confirm-delete"
                  type="text"
                  value={confirmText}
                  onChange={(event) => onConfirmTextChange(event.target.value)}
                />
              </label>
              <div className="cta-row">
                <button
                  type="button"
                  className="account-profile-button account-profile-button-secondary"
                  onClick={onCloseDelete}
                >
                  {t("account.profile.confirmCancel")}
                </button>
                <button
                  type="button"
                  className="account-profile-button account-profile-button-danger"
                  onClick={onDeleteAccount}
                >
                  {t("account.profile.confirmDelete")}
                </button>
              </div>
            </motion.section>
          </motion.div>
        ) : null}
      </AnimatePresence>

      <AnimatePresence>
        {toast ? (
          <motion.div
            className={`toast ${toast.tone === "success" ? "notice-success" : "notice-error"}`}
            role="status"
            aria-live="polite"
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 12 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
          >
            {toast.message}
          </motion.div>
        ) : null}
      </AnimatePresence>
    </main>
  );
}
