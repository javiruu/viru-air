"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import {
  GlassProfileData,
  GlassProfileSession,
  GlassProfileSettingsCard,
} from "@/components/components/forms/glass-profile-settings";
import { useI18n } from "@/i18n";
import { apiFetch } from "@/modules/shared/api";
import { clearToken } from "@/modules/shared/auth";

export default function PerfilPage() {
  const router = useRouter();
  const { t, localeTag } = useI18n();
  const { notify } = useNotificationCenter();
  const [profile, setProfile] = useState<GlassProfileData | null>(null);
  const [sessions, setSessions] = useState<GlassProfileSession[]>([]);
  const [saving, setSaving] = useState(false);
  const [closingSessions, setClosingSessions] = useState(false);
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
      .catch(() => notify({ tone: "error", title: t("account.profile.updateError"), durationMs: 3200 }));
  }, [notify, t]);

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
      notify({ tone: "success", title: t("account.profile.updateSuccess"), durationMs: 3200 });
    } catch {
      notify({ tone: "error", title: t("account.profile.updateError"), durationMs: 3200 });
    } finally {
      setSaving(false);
    }
  }

  async function onCloseAllSessions() {
    setClosingSessions(true);
    try {
      await apiFetch<{ status: string }>("/account/sessions/close_all", { method: "POST" });
      setSessions((prev) => prev.map((item) => ({ ...item, is_active: false })));
      notify({ tone: "success", title: t("account.profile.closeAllSuccess"), durationMs: 3200 });
    } catch {
      notify({ tone: "error", title: t("account.profile.closeAllError"), durationMs: 3200 });
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
      notify({ tone: "error", title: t("account.profile.deleteError"), durationMs: 3200 });
    }
  }

  return (
    <GlassProfileSettingsCard
      profile={profile}
      sessions={sessions}
      saving={saving}
      closingSessions={closingSessions}
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
