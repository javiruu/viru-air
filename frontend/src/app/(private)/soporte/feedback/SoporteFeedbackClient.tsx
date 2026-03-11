"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "@/modules/shared/api";
import { useI18n } from "@/i18n";

type ToastState = { tone: "success" | "error"; message: string } | null;

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
  const [feedbackType, setFeedbackType] = useState<Props["initialFeedbackType"]>(initialFeedbackType);
  const [message, setMessage] = useState(initialMessage);
  const [attachmentUrl, setAttachmentUrl] = useState(initialAttachmentUrl);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<ToastState>(null);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 3200);
    return () => window.clearTimeout(timer);
  }, [toast]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!message.trim()) {
      setToast({ tone: "error", message: t("support.feedback.validation") });
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
      setToast({ tone: "success", message: t("support.feedback.success") });
    } catch {
      setToast({ tone: "error", message: t("support.feedback.error") });
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

      {toast ? (
        <div className={`toast ${toast.tone === "success" ? "notice-success" : "notice-error"}`} role="status" aria-live="polite">
          {toast.message}
        </div>
      ) : null}
    </main>
  );
}
