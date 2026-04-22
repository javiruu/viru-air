"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import AirLoader from "@/modules/shared/AirLoader";
import { useI18n } from "@/i18n";
import { apiFetch } from "@/modules/shared/api";
import { clearToken } from "@/modules/shared/auth";

type Profile = {
  display_name: string;
  email: string;
  avatar_url: string | null;
  status: string;
  created_at: string;
};

type SessionItem = {
  id: string;
  device: string;
  ip: string | null;
  last_seen: string;
  created_at: string;
  is_active: boolean;
};

type ToastState = { tone: "success" | "error"; message: string } | null;

function getInitials(profile: Profile | null): string {
  const source = profile?.display_name?.trim() || profile?.email?.trim() || "US";
  const parts = source.split(/[\s.@_-]+/).filter(Boolean);
  if (parts.length === 0) return "US";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
}

export default function PerfilPage() {
  const router = useRouter();
  const { t, localeTag } = useI18n();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [saving, setSaving] = useState(false);
  const [closingSessions, setClosingSessions] = useState(false);
  const [toast, setToast] = useState<ToastState>(null);
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");

  useEffect(() => {
    Promise.all([
      apiFetch<Profile>("/account/profile"),
      apiFetch<{ items: SessionItem[] }>("/account/sessions"),
    ])
      .then(([profileData, sessionsData]) => {
        setProfile(profileData);
        setSessions(sessionsData.items || []);
      })
      .catch(() => setToast({ tone: "error", message: t("account.profile.updateError") }));
  }, [t]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 3200);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const statusClass = useMemo(() => {
    if (!profile?.status) return "status-degraded";
    return profile.status.toLowerCase().includes("activa") ? "status-ok" : "status-degraded";
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

  const initials = useMemo(() => getInitials(profile), [profile]);
  const confirmKeyword = t("account.profile.confirmKeyword");

  function updateField(key: "display_name" | "avatar_url", value: string) {
    if (!profile) return;
    setProfile({ ...profile, [key]: value });
  }

  async function onSave(event: FormEvent) {
    event.preventDefault();
    if (!profile) return;
    setSaving(true);
    try {
      const payload = {
        display_name: profile.display_name,
        avatar_url: profile.avatar_url || "",
      };
      const updated = await apiFetch<Profile>("/account/profile", {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      setProfile(updated);
      setToast({ tone: "success", message: t("account.profile.updateSuccess") });
    } catch {
      setToast({ tone: "error", message: t("account.profile.updateError") });
    } finally {
      setSaving(false);
    }
  }

  async function onCloseAllSessions() {
    setClosingSessions(true);
    try {
      await apiFetch<{ status: string }>("/account/sessions/close_all", { method: "POST" });
      setSessions((prev) => prev.map((item) => ({ ...item, is_active: false })));
      setToast({ tone: "success", message: t("account.profile.closeAllSuccess") });
    } catch {
      setToast({ tone: "error", message: t("account.profile.closeAllError") });
    } finally {
      setClosingSessions(false);
    }
  }

  async function onDeleteAccount() {
    if (confirmText.trim().toUpperCase() !== confirmKeyword) return;
    try {
      await apiFetch<{ status: string }>("/account", { method: "DELETE" });
      clearToken();
      router.push("/");
    } catch {
      setToast({ tone: "error", message: t("account.profile.deleteError") });
    }
  }

  if (!profile) {
    return (
      <main className="shell account-profile-shell" id="main-content">
        <div className="page-header">
          <button className="btn-ghost" type="button" onClick={() => router.push("/dashboard")}>
            {t("shared.actions.back")}
          </button>
          <div className="page-title">
            <h1>{t("account.profile.title")}</h1>
            <p>{t("account.profile.subtitle")}</p>
          </div>
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
      <div className="page-header">
        <button className="btn-ghost" type="button" onClick={() => router.push("/dashboard")}>
          {t("shared.actions.back")}
        </button>
        <div className="page-title">
          <h1>{t("account.profile.title")}</h1>
          <p>{t("account.profile.pageSubtitle")}</p>
        </div>
      </div>

      <section className="account-profile-glass">
        <div className="account-profile-orb account-profile-orb-primary" aria-hidden="true" />
        <div className="account-profile-orb account-profile-orb-secondary" aria-hidden="true" />

        <div className="account-profile-grid">
          <div className="account-profile-main">
            <section className="account-profile-hero">
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
                </div>

                <div className="account-profile-meta">
                  <div className="account-profile-meta-line">
                    <strong>{profile.email}</strong>
                    <span className={`status-badge ${statusClass}`}>{profile.status}</span>
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
                      <strong>
                        {sessions[0]?.last_seen
                          ? new Date(sessions[0].last_seen).toLocaleDateString(localeTag, {
                              month: "short",
                              day: "2-digit",
                            })
                          : "--"}
                      </strong>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section className="account-profile-panel">
              <div className="account-profile-panel-header">
                <div>
                  <span className="account-profile-kicker">{t("account.profile.identityTitle")}</span>
                  <h3>{t("account.profile.pageSubtitle")}</h3>
                </div>
                <p>{t("account.profile.identityHint")}</p>
              </div>

              <form className="account-profile-form" onSubmit={onSave}>
                <label className="account-profile-field">
                  <span>{t("account.profile.displayNameLabel")}</span>
                  <input
                    type="text"
                    name="display_name"
                    value={profile.display_name}
                    onChange={(event) => updateField("display_name", event.target.value)}
                  />
                </label>

                <label className="account-profile-field">
                  <span>{t("account.profile.avatarLabel")}</span>
                  <input
                    type="url"
                    name="avatar_url"
                    value={profile.avatar_url || ""}
                    onChange={(event) => updateField("avatar_url", event.target.value)}
                  />
                </label>

                <label className="account-profile-field">
                  <span>{t("account.profile.emailLabel")}</span>
                  <input type="email" name="email" value={profile.email} readOnly />
                </label>

                <label className="account-profile-field">
                  <span>{t("account.profile.createdLabel")}</span>
                  <input type="text" value={accountAgeLabel} readOnly />
                </label>

                <div className="account-profile-actions">
                  <button type="submit" className="btn-primary" disabled={saving}>
                    {saving ? t("account.profile.saving") : t("account.profile.saveAction")}
                  </button>
                </div>
              </form>
            </section>
          </div>

          <aside className="account-profile-side">
            <section className="account-profile-panel account-profile-panel-soft">
              <div className="account-profile-panel-header">
                <div>
                  <span className="account-profile-kicker">{t("account.profile.sessionsTitle")}</span>
                  <h3>{t("account.profile.sessionsTitle")}</h3>
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
                        <strong>{session.device}</strong>
                        <p>
                          {t("account.profile.lastAccess")}: {new Date(session.last_seen).toLocaleString(localeTag)}
                        </p>
                        {session.ip ? <span>{session.ip}</span> : null}
                      </div>
                      <span className={`status-badge ${session.is_active ? "status-ok" : "status-degraded"}`}>
                        {session.is_active ? t("account.profile.sessionActive") : t("account.profile.sessionClosed")}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              <div className="account-profile-actions">
                <button type="button" className="btn-ghost" onClick={onCloseAllSessions} disabled={closingSessions}>
                  {closingSessions ? t("account.profile.closingSessions") : t("account.profile.closeAllSessions")}
                </button>
              </div>
            </section>

            <section className="account-profile-panel account-profile-danger">
              <div className="account-profile-panel-header">
                <div>
                  <span className="account-profile-kicker">{t("account.profile.dangerTitle")}</span>
                  <h3>{t("account.profile.dangerTitle")}</h3>
                </div>
                <p>{t("account.profile.dangerHint")}</p>
              </div>

              <p className="account-profile-danger-copy">{t("account.profile.deleteNote")}</p>

              <div className="account-profile-actions">
                <button type="button" className="btn-danger" onClick={() => setConfirmDeleteOpen(true)}>
                  {t("account.profile.deleteAction")}
                </button>
              </div>
            </section>
          </aside>
        </div>
      </section>

      {confirmDeleteOpen ? (
        <div className="modal-overlay" onClick={() => setConfirmDeleteOpen(false)}>
          <section
            className="modal-card account-profile-delete-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-account-title"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-header">
              <div>
                <h2 id="delete-account-title">{t("account.profile.confirmTitle")}</h2>
                <p className="panel-note">{t("account.profile.confirmHint", { keyword: confirmKeyword })}</p>
              </div>
              <button
                className="modal-close"
                type="button"
                onClick={() => setConfirmDeleteOpen(false)}
                aria-label={t("account.profile.confirmClose")}
              >
                X
              </button>
            </div>
            <label className="field" htmlFor="confirm-delete">
              {t("account.profile.confirmLabel")}
              <input
                id="confirm-delete"
                type="text"
                value={confirmText}
                onChange={(event) => setConfirmText(event.target.value)}
              />
            </label>
            <div className="cta-row">
              <button type="button" className="btn-ghost" onClick={() => setConfirmDeleteOpen(false)}>
                {t("account.profile.confirmCancel")}
              </button>
              <button type="button" className="btn-danger" onClick={onDeleteAccount}>
                {t("account.profile.confirmDelete")}
              </button>
            </div>
          </section>
        </div>
      ) : null}

      {toast ? (
        <div
          className={`toast ${toast.tone === "success" ? "notice-success" : "notice-error"}`}
          role="status"
          aria-live="polite"
        >
          {toast.message}
        </div>
      ) : null}
    </main>
  );
}
