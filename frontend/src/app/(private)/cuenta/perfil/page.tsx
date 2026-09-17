"use client";

import { type FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import {
  type GlassProfileData,
  type GlassProfileSession,
  GlassProfileSettingsCard,
} from "@/components/components/forms/glass-profile-settings";
import { useI18n } from "@/i18n";

import {
  getProfileApiV1AccountProfileGet,
  updateProfileApiV1AccountProfilePut,
  getSessionsApiV1AccountSessionsGet,
  closeAllSessionsApiV1AccountSessionsCloseAllPost,
  deleteAccountApiV1AccountDelete,
} from "@/api/generated/account/account";

const ACCOUNT_SESSIONS_PAGE_SIZE = 200;

async function fetchAllAccountSessions(): Promise<GlassProfileSession[]> {
  const sessions: GlassProfileSession[] = [];
  let offset = 0;

  while (true) {
    const page = (await getSessionsApiV1AccountSessionsGet({
      limit: ACCOUNT_SESSIONS_PAGE_SIZE,
      offset,
    })) as unknown as { items: GlassProfileSession[] };
    const items = Array.isArray(page.items) ? page.items : [];
    sessions.push(...(items as unknown as GlassProfileSession[]));
    if (items.length < ACCOUNT_SESSIONS_PAGE_SIZE) return sessions;
    offset += items.length;
  }
}

export default function PerfilPage() {
  const router = useRouter();
  const { t, localeTag } = useI18n();
  const { notify } = useNotificationCenter();
  const queryClient = useQueryClient();

  const [profile, setProfile] = useState<GlassProfileData | null>(null);
  const [sessions, setSessions] = useState<GlassProfileSession[]>([]);
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");

  const profileQuery = useQuery({
    queryKey: ["accountProfile"],
    queryFn: () => getProfileApiV1AccountProfileGet(),
  });

  const sessionsQuery = useQuery({
    queryKey: ["accountSessions"],
    queryFn: fetchAllAccountSessions,
  });

  useEffect(() => {
    if (profileQuery.data) {
      setProfile(profileQuery.data as unknown as GlassProfileData);
    }
  }, [profileQuery.data]);

  useEffect(() => {
    if (sessionsQuery.data) {
      setSessions(sessionsQuery.data);
    }
  }, [sessionsQuery.data]);

  useEffect(() => {
    if (profileQuery.isError || sessionsQuery.isError) {
      notify({ tone: "error", title: t("account.profile.updateError"), durationMs: 3200 });
    }
  }, [profileQuery.isError, sessionsQuery.isError, notify, t]);

  const updateProfileMutation = useMutation({
    mutationFn: (data: { display_name: string; avatar_url: string }) =>
      updateProfileApiV1AccountProfilePut(data),
    onSuccess: (updatedProfile) => {
      queryClient.setQueryData(["accountProfile"], updatedProfile);
      setProfile(updatedProfile as unknown as GlassProfileData);
      notify({ tone: "success", title: t("account.profile.updateSuccess"), durationMs: 3200 });
    },
    onError: () => {
      notify({ tone: "error", title: t("account.profile.updateError"), durationMs: 3200 });
    },
  });

  const closeSessionsMutation = useMutation({
    mutationFn: () => closeAllSessionsApiV1AccountSessionsCloseAllPost(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accountSessions"] });
      setSessions((prev) => prev.map((item) => ({ ...item, is_active: false })));
      notify({ tone: "success", title: t("account.profile.closeAllSuccess"), durationMs: 3200 });
    },
    onError: () => {
      notify({ tone: "error", title: t("account.profile.closeAllError"), durationMs: 3200 });
    },
  });

  const deleteAccountMutation = useMutation({
    mutationFn: () => deleteAccountApiV1AccountDelete(),
    onSuccess: () => {
      /* TODO: migrate to Supabase SSR */
      router.push("/");
    },
    onError: () => {
      notify({ tone: "error", title: t("account.profile.deleteError"), durationMs: 3200 });
    },
  });

  function updateField(key: "display_name" | "avatar_url", value: string) {
    if (!profile) return;
    setProfile({ ...profile, [key]: value });
  }

  function onSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!profile) return;
    updateProfileMutation.mutate({
      display_name: profile.display_name,
      avatar_url: profile.avatar_url || "",
    });
  }

  function onCloseAllSessions() {
    closeSessionsMutation.mutate();
  }

  function onDeleteAccount() {
    const confirmKeyword = t("account.profile.confirmKeyword");
    if (confirmText.trim().toUpperCase() !== confirmKeyword) return;
    deleteAccountMutation.mutate();
  }

  return (
    <GlassProfileSettingsCard
      profile={profile}
      sessions={sessions}
      saving={updateProfileMutation.isPending}
      closingSessions={closeSessionsMutation.isPending}
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
