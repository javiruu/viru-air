"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import AirLoader from "@/modules/shared/AirLoader";
import { apiFetch } from "@/modules/shared/api";
import { useI18n } from "@/i18n";

type SecurityEvent = {
  event_type: string;
  ip: string | null;
  created_at: string;
};

export default function SeguridadPage() {
  const router = useRouter();
  const { t, localeTag } = useI18n();
  const { notify } = useNotificationCenter();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<{ items: SecurityEvent[] }>("/account/security/activity")
      .then((data) => setEvents(data.items || []))
      .catch(() => setEvents([]))
      .finally(() => setLoading(false));
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      await apiFetch<{ status: string }>("/account/security/password", {
        method: "POST",
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });
      setCurrentPassword("");
      setNewPassword("");
      notify({ tone: "success", title: t("account.security.passwordSuccess"), durationMs: 3200 });
    } catch {
      notify({ tone: "error", title: t("account.security.passwordError"), durationMs: 3200 });
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="shell" id="main-content">
      <div className="page-header">
        <button className="btn-ghost" type="button" onClick={() => router.push("/dashboard")}>
          {t("shared.actions.back")}
        </button>
        <div className="page-title">
          <h1>{t("account.security.title")}</h1>
          <p>{t("account.security.pageSubtitle")}</p>
        </div>
      </div>

      <div className="split">
        <section className="panel">
          <div className="panel-header">
            <h2>{t("account.security.passwordTitle")}</h2>
            <span className="muted">{t("account.security.passwordHint")}</span>
          </div>
          <form className="form" onSubmit={onSubmit}>
            <label>
              {t("account.security.passwordCurrent")}
              <input
                type="password"
                name="current_password"
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
              />
            </label>
            <label>
              {t("account.security.passwordNew")}
              <input
                type="password"
                name="new_password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
              />
            </label>
            <div className="row-actions">
              <button type="submit" className="btn-primary" disabled={saving || !currentPassword || !newPassword}>
                {saving ? t("account.security.passwordSaving") : t("account.security.passwordAction")}
              </button>
            </div>
          </form>
        </section>

        <section className="panel panel-soft">
          <div className="panel-header">
            <h2>{t("account.security.twoFaTitle")}</h2>
            <span className="muted">{t("account.security.twoFaHint")}</span>
          </div>
          <p className="panel-note">{t("account.security.twoFaNote")}</p>
          <button
            type="button"
            className="btn-secondary"
            onClick={() =>
              router.push(
                `/soporte/feedback?type=idea&message=${encodeURIComponent(
                  t("account.security.twoFaRequestMessage"),
                )}`,
              )
            }
          >
            {t("account.security.twoFaAction")}
          </button>
        </section>
      </div>

      <section className="panel panel-soft">
        <div className="panel-header">
          <h2>{t("account.security.activityTitle")}</h2>
          <span className="muted">{t("account.security.activityHint")}</span>
        </div>
        {loading ? (
          <div className="air-loader-section">
            <AirLoader size={0.7} />
            <p className="muted">{t("account.security.activityLoading")}</p>
          </div>
        ) : events.length === 0 ? (
          <p className="panel-note">{t("account.security.activityEmpty")}</p>
        ) : (
          <div className="panel-list">
            {events.map((item, idx) => (
              <div key={`${item.event_type}-${idx}`} className="panel-list-row">
                <div>
                  <strong>{item.event_type.replace(/_/g, " ")}</strong>
                  <p className="panel-note">{new Date(item.created_at).toLocaleString(localeTag)}</p>
                </div>
                <div>
                  <span className="muted">{item.ip || t("account.security.activityIpMissing")}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
