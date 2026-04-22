"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";

import { useI18n } from "@/i18n";
import { apiFetch } from "@/modules/shared/api";

type ToastState = { tone: "success" | "error"; message: string } | null;

export default function SoporteContactoClient() {
  const { t } = useI18n();
  const [message, setMessage] = useState("");
  const [attachmentUrl, setAttachmentUrl] = useState("");
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
      setToast({ tone: "error", message: t("support.contact.validation") });
      return;
    }
    setSaving(true);
    try {
      await apiFetch<{ status: string }>("/support/feedback", {
        method: "POST",
        body: JSON.stringify({
          feedback_type: "general",
          message: message.trim(),
          attachment_url: attachmentUrl || null,
        }),
      });
      setMessage("");
      setAttachmentUrl("");
      setToast({ tone: "success", message: t("support.contact.success") });
    } catch {
      setToast({ tone: "error", message: t("support.contact.error") });
    } finally {
      setSaving(false);
    }
  }

  const asideCards = [
    {
      title: t("support.contact.asideCards.oneTitle"),
      body: t("support.contact.asideCards.oneBody"),
      icon: "fa-clipboard-list",
    },
    {
      title: t("support.contact.asideCards.twoTitle"),
      body: t("support.contact.asideCards.twoBody"),
      icon: "fa-link",
    },
    {
      title: t("support.contact.asideCards.threeTitle"),
      body: t("support.contact.asideCards.threeBody"),
      icon: "fa-circle-check",
    },
  ];

  const heroPoints = [
    t("support.contact.heroPoints.one"),
    t("support.contact.heroPoints.two"),
    t("support.contact.heroPoints.three"),
  ];

  return (
    <main className="shell support-contact-page" id="main-content">
      <div className="page-header">
        <div className="page-title">
          <h1>{t("support.contact.title")}</h1>
          <p>{t("support.contact.subtitle")}</p>
        </div>
        <div className="row-actions">
          <Link className="btn-ghost" href="/soporte/ayuda">
            {t("account.menu.help")}
          </Link>
          <Link className="btn-primary" href="/dashboard">
            {t("shared.actions.back")}
          </Link>
        </div>
      </div>

      <section className="support-contact-hero panel">
        <div className="support-contact-hero-copy">
          <span className="support-contact-eyebrow">{t("support.contact.eyebrow")}</span>
          <div className="support-contact-hero-header">
            <div>
              <h2>{t("support.contact.heroTitle")}</h2>
              <p>{t("support.contact.heroBody")}</p>
            </div>
            <span className="status-badge status-ok">{t("support.contact.badge")}</span>
          </div>
          <div className="support-contact-points">
            {heroPoints.map((point) => (
              <article key={point} className="support-contact-point">
                <span className="support-contact-point-icon" aria-hidden="true">
                  <i className="fa-solid fa-check"></i>
                </span>
                <p>{point}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <div className="support-contact-layout">
        <section className="panel support-contact-form-panel">
          <div className="panel-header support-contact-form-header">
            <div>
              <h2>{t("support.contact.panelTitle")}</h2>
              <p className="panel-subtitle">{t("support.contact.panelSubtitle")}</p>
            </div>
            <span className="status-badge">{t("support.contact.title")}</span>
          </div>

          <form className="form support-contact-form" onSubmit={onSubmit}>
            <label>
              {t("support.contact.messageLabel")}
              <textarea
                name="message"
                rows={8}
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder={t("support.contact.messagePlaceholder")}
              />
            </label>
            <label>
              {t("support.contact.attachmentLabel")}
              <input
                type="url"
                name="attachment_url"
                value={attachmentUrl}
                onChange={(event) => setAttachmentUrl(event.target.value)}
                placeholder={t("support.contact.attachmentPlaceholder")}
              />
            </label>
            <div className="row-actions support-contact-actions">
              <button type="submit" className="btn-primary" disabled={saving}>
                {saving ? t("support.contact.sending") : t("support.contact.submit")}
              </button>
              <span className="panel-note">{t("support.contact.note")}</span>
            </div>
          </form>
        </section>

        <aside className="panel panel-soft support-contact-aside">
          <div className="support-contact-aside-copy">
            <h2 className="panel-title">{t("support.contact.asideTitle")}</h2>
            <p className="panel-subtitle">{t("support.contact.asideBody")}</p>
          </div>
          <div className="support-contact-aside-cards">
            {asideCards.map((card) => (
              <article key={card.title} className="support-contact-aside-card card">
                <span className="support-contact-aside-icon" aria-hidden="true">
                  <i className={`fa-solid ${card.icon}`}></i>
                </span>
                <div>
                  <h3>{card.title}</h3>
                  <p>{card.body}</p>
                </div>
              </article>
            ))}
          </div>
        </aside>
      </div>

      {toast ? (
        <div className={`toast ${toast.tone === "success" ? "notice-success" : "notice-error"}`} role="status" aria-live="polite">
          {toast.message}
        </div>
      ) : null}
    </main>
  );
}
