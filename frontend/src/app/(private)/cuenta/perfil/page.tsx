"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  GlassProfileData,
  GlassProfileSession,
  GlassProfileSettingsCard,
  GlassProfileToastState,
} from "@/components/components/forms/glass-profile-settings";
import { useI18n } from "@/i18n";
import { apiFetch } from "@/modules/shared/api";
import { clearToken } from "@/modules/shared/auth";

export default function PerfilPage() {
  const router = useRouter();
  const { t, localeTag } = useI18n();
  const [profile, setProfile] = useState<GlassProfileData | null>(null);
  const [sessions, setSessions] = useState<GlassProfileSession[]>([]);
  const [saving, setSaving] = useState(false);
  const [closingSessions, setClosingSessions] = useState(false);
  const [toast, setToast] = useState<GlassProfileToastState>(null);
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");

  useEffect(() => {
    Promise.all([
      apiFetch<GlassProfileData>("/account/profile"),
      apiFetch<{ items: GlassProfileSession[] }>("/account/sessions"),
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

  function updateField(key: "display_name" | "avatar_url", value: string) {
    if (!profile) return;
    setProfile({ ...profile, [key]: value });
  }

  async function onSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!profile) return;
    setSaving(true);
    try {
      const updated = await apiFetch<GlassProfileData>("/account/profile", {
        method: "PUT",
        body: JSON.stringify({
          display_name: profile.display_name,
          avatar_url: profile.avatar_url || "",
        }),
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
    const confirmKeyword = t("account.profile.confirmKeyword");
    if (confirmText.trim().toUpperCase() !== confirmKeyword) return;
    try {
      await apiFetch<{ status: string }>("/account", { method: "DELETE" });
      clearToken();
      router.push("/");
    } catch {
      setToast({ tone: "error", message: t("account.profile.deleteError") });
    }
  }

  return (
    <GlassProfileSettingsCard
      profile={profile}
      sessions={sessions}
      saving={saving}
      closingSessions={closingSessions}
      toast={toast}
      confirmDeleteOpen={confirmDeleteOpen}
      confirmText={confirmText}
      localeTag={localeTag}
      t={t}
      onBack={() => router.push("/dashboard")}
      onFieldChange={updateField}
      onSave={onSave}
      onCloseAllSessions={onCloseAllSessions}
      onOpenDelete={() => setConfirmDeleteOpen(true)}
      onCloseDelete={() => setConfirmDeleteOpen(false)}
      onConfirmTextChange={setConfirmText}
      onDeleteAccount={onDeleteAccount}
    />
  );
}
