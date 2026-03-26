"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import AirLoader from "@/modules/shared/AirLoader";
import { apiFetch } from "@/modules/shared/api";
import { clearToken } from "@/modules/shared/auth";
import { useI18n } from "@/i18n";

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
      <main className="shell" id="main-content">
        <div className="page-header">
          <button className="btn-ghost" type="button" onClick={() => router.push("/dashboard")}>
            {t("shared.actions.back")}
          </button>
          <div className="page-title">
            <h1>{t("account.profile.title")}</h1>
            <p>{t("account.profile.subtitle")}</p>
          </div>
        </div>
        <section className="panel panel-soft air-loader-section">
          <AirLoader size={0.85} />
          <p className="muted">{t("shared.states.loading")}</p>
        </section>
      </main>
    );
  }

  return (
    <main className="shell" id="main-content">
      <div className="page-header">
        <button className="btn-ghost" type="button" onClick={() => router.push("/dashboard")}>
          {t("shared.actions.back")}
        </button>
        <div className="page-title">
          <h1>{t("account.profile.title")}</h1>
          <p>{t("account.profile.pageSubtitle")}</p>
        </div>
      </div>

      <div className="split">
        <section className="panel">
          <div className="panel-header">
            <h2>{t("account.profile.identityTitle")}</h2>
            <span className={`status-badge ${statusClass}`}>{profile.status}</span>
          </div>
          <form className="form" onSubmit={onSave}>
            <label>
              {t("account.profile.displayNameLabel")}
              <input
                type="text"
                name="display_name"
                value={profile.display_name}
                onChange={(event) => updateField("display_name", event.target.value)}
              />
            </label>
            <label>
              {t("account.profile.avatarLabel")}
              <input
                type="url"
                name="avatar_url"
                value={profile.avatar_url || ""}
                onChange={(event) => updateField("avatar_url", event.target.value)}
              />
            </label>
            <label>
              {t("account.profile.emailLabel")}
              <input type="email" name="email" value={profile.email} readOnly />
            </label>
            <label>
              {t("account.profile.createdLabel")}
              <input type="text" value={formattedCreatedAt} readOnly />
            </label>
            <div className="row-actions">
              <button type="submit" className="btn-primary" disabled={saving}>
                {saving ? t("account.profile.saving") : t("account.profile.saveAction")}
              </button>
            </div>
          </form>
        </section>

        <section className="panel panel-soft">
          <div className="panel-header">
            <h2>{t("account.profile.sessionsTitle")}</h2>
            <span className="muted">{t("account.profile.sessionsHint")}</span>
          </div>
          {sessions.length === 0 ? (
            <p className="panel-note">{t("account.profile.sessionsEmpty")}</p>
          ) : (
            <div className="panel-list">
              {sessions.map((session) => (
                <div key={session.id} className="panel-list-row">
                  <div>
                    <strong>{session.device}</strong>
                    <p className="panel-note">
                      {t("account.profile.lastAccess")}: {new Date(session.last_seen).toLocaleString(localeTag)}
                    </p>
                  </div>
                  <div>
                    <span className={`status-badge ${session.is_active ? "status-ok" : "status-degraded"}`}>
                      {session.is_active ? t("account.profile.sessionActive") : t("account.profile.sessionClosed")}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
          <div className="row-actions">
            <button type="button" className="btn-ghost" onClick={onCloseAllSessions} disabled={closingSessions}>
              {closingSessions ? t("account.profile.closingSessions") : t("account.profile.closeAllSessions")}
            </button>
          </div>
        </section>
      </div>

      <section className="panel panel-soft">
        <div className="panel-header">
          <h2>{t("account.profile.dangerTitle")}</h2>
          <span className="muted">{t("account.profile.dangerHint")}</span>
        </div>
        <p className="panel-note">{t("account.profile.deleteNote")}</p>
        <div className="row-actions">
          <button type="button" className="btn-danger" onClick={() => setConfirmDeleteOpen(true)}>
            {t("account.profile.deleteAction")}
          </button>
        </div>
      </section>

      {confirmDeleteOpen ? (
        <div className="modal-overlay" onClick={() => setConfirmDeleteOpen(false)}>
          <section
            className="modal-card"
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
        <div className={`toast ${toast.tone === "success" ? "notice-success" : "notice-error"}`} role="status" aria-live="polite">
          {toast.message}
        </div>
      ) : null}
    </main>
  );
}
