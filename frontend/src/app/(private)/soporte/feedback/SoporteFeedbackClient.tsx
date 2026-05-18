"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { apiFetch } from "@/modules/shared/api";
import { useI18n } from "@/i18n";

type Props = {
  initialFeedbackType: "bug" | "idea" | "general";
  initialMessage: string;
  initialAttachmentUrl: string;
};

export default function SoporteFeedbackClient({
  initialFeedbackType,
  initialMessage,
  initialAttachmentUrl,
}: Props) {
  const router = useRouter();
  const { t } = useI18n();
  const { notify } = useNotificationCenter();
  const [feedbackType, setFeedbackType] = useState<Props["initialFeedbackType"]>(initialFeedbackType);
  const [message, setMessage] = useState(initialMessage);
  const [attachmentUrl, setAttachmentUrl] = useState(initialAttachmentUrl);
  const [saving, setSaving] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!message.trim()) {
      notify({ tone: "error", title: t("support.feedback.validation"), durationMs: 3200 });
      return;
    }
    setSaving(true);
    try {
      await apiFetch<{ status: string }>("/support/feedback", {
        method: "POST",
        body: JSON.stringify({
          feedback_type: feedbackType,
          message,
          attachment_url: attachmentUrl || null,
        }),
      });
      setMessage("");
      setAttachmentUrl("");
      notify({ tone: "success", title: t("support.feedback.success"), durationMs: 3200 });
    } catch {
      notify({ tone: "error", title: t("support.feedback.error"), durationMs: 3200 });
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
          <h1>{t("support.feedback.title")}</h1>
          <p>{t("support.feedback.pageSubtitle")}</p>
        </div>
      </div>

      <section className="panel">
        <div className="panel-header">
          <h2>{t("support.feedback.sectionTitle")}</h2>
          <span className="muted">{t("support.feedback.sectionHint")}</span>
        </div>
        <form className="form" onSubmit={onSubmit}>
          <label>
            {t("support.feedback.typeLabel")}
            <select value={feedbackType} onChange={(event) => setFeedbackType(event.target.value as Props["initialFeedbackType"])}>
              <option value="bug">{t("support.feedback.typeBug")}</option>
              <option value="idea">{t("support.feedback.typeIdea")}</option>
              <option value="general">{t("support.feedback.typeGeneral")}</option>
            </select>
          </label>
          <label>
            {t("support.feedback.messageLabel")}
            <textarea
              name="message"
              rows={6}
              value={message}
              onChange={(event) => setMessage(event.target.value)}
            />
          </label>
          <label>
            {t("support.feedback.attachmentLabel")}
            <input
              type="url"
              name="attachment_url"
              value={attachmentUrl}
              onChange={(event) => setAttachmentUrl(event.target.value)}
            />
          </label>
          <div className="row-actions">
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? t("support.feedback.sending") : t("support.feedback.submit")}
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}
