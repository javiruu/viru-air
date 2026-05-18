"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { useI18n } from "@/i18n";
import { apiFetch, apiFetchWithStatus } from "@/modules/shared/api";
type Me = { id: string; email: string; locale: string; is_admin: boolean };

function isValidOptionalUrl(value: string): boolean {
  if (!value.trim()) return true;
  try {
    const parsed = new URL(value);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

function getCounterTone(length: number): "short" | "ready" | "rich" {
  if (length >= 220) return "rich";
  if (length >= 40) return "ready";
  return "short";
}

export default function SoporteContactoClient() {
  const { t } = useI18n();
  const { notify } = useNotificationCenter();
  const [me, setMe] = useState<Me | null>(null);
  const [message, setMessage] = useState("");
  const [attachmentUrl, setAttachmentUrl] = useState("");
  const [saving, setSaving] = useState(false);
  const [messageError, setMessageError] = useState("");
  const [attachmentError, setAttachmentError] = useState("");

  useEffect(() => {
    apiFetchWithStatus<Me>("/auth/me").then((result) => {
      if (result.ok) {
        setMe(result.data);
      }
    });
  }, []);

  const trimmedLength = message.trim().length;
  const counterTone = useMemo(() => getCounterTone(trimmedLength), [trimmedLength]);
  const counterStateLabel =
    counterTone === "rich"
      ? t("support.contact.counterStateRich")
      : counterTone === "ready"
        ? t("support.contact.counterStateReady")
        : t("support.contact.counterStateShort");

  function validateForm(): boolean {
    const nextMessageError =
      trimmedLength < 20 ? t(trimmedLength === 0 ? "support.contact.validation" : "support.contact.messageMin") : "";
    const nextAttachmentError = isValidOptionalUrl(attachmentUrl) ? "" : t("support.contact.attachmentInvalid");
    setMessageError(nextMessageError);
    setAttachmentError(nextAttachmentError);
    return !nextMessageError && !nextAttachmentError;
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!validateForm()) {
      notify({
        tone: "error",
        title: trimmedLength === 0 ? t("support.contact.validation") : t("support.contact.error"),
        durationMs: 3200,
      });
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
      setMessageError("");
      setAttachmentError("");
      notify({ tone: "success", title: t("support.contact.success"), durationMs: 3200 });
    } catch {
      notify({ tone: "error", title: t("support.contact.error"), durationMs: 3200 });
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

  const checklistItems = [
    t("support.contact.checklistItems.one"),
    t("support.contact.checklistItems.two"),
    t("support.contact.checklistItems.three"),
  ];

  const signedInLabel = me?.email || me?.id || "user@viru.local";

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
        <div className="support-contact-orb support-contact-orb-primary" aria-hidden="true" />
        <div className="support-contact-orb support-contact-orb-secondary" aria-hidden="true" />
        <div className="support-contact-hero-copy">
          <span className="support-contact-eyebrow">{t("support.contact.eyebrow")}</span>
          <div className="support-contact-hero-header">
            <div>
              <h2>{t("support.contact.heroTitle")}</h2>
              <p>{t("support.contact.heroBody")}</p>
            </div>
            <span className="status-badge status-ok">{t("support.contact.badge")}</span>
          </div>
          <div className="support-contact-signal-strip" aria-hidden="true">
            <span />
            <span />
            <span />
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
              <span className="support-contact-form-kicker">{t("support.contact.formKicker")}</span>
              <h2>{t("support.contact.panelTitle")}</h2>
              <p className="panel-subtitle">{t("support.contact.panelSubtitle")}</p>
            </div>
            <span className="status-badge">{t("support.contact.title")}</span>
          </div>

          <div className="support-contact-account-row">
            <div className="support-contact-account-chip">
              <span>{t("support.contact.signedInAs")}</span>
              <strong>{signedInLabel}</strong>
            </div>
            <p className="support-contact-response-note">{t("support.contact.responseWindow")}</p>
          </div>

          <form className="form support-contact-form" onSubmit={onSubmit}>
            <label className={`support-contact-field ${messageError ? "is-invalid" : ""}`}>
              <span className="support-contact-label-row">
                <span>{t("support.contact.messageLabel")}</span>
                <span className={`support-contact-counter support-contact-counter-${counterTone}`}>
                  {t("support.contact.counterLabel")}: {message.length} - {counterStateLabel}
                </span>
              </span>
              <textarea
                name="message"
                rows={8}
                value={message}
                onChange={(event) => {
                  setMessage(event.target.value);
                  if (messageError) {
                    setMessageError("");
                  }
                }}
                placeholder={t("support.contact.messagePlaceholder")}
                aria-invalid={messageError ? "true" : "false"}
                aria-describedby="support-contact-message-help support-contact-message-error"
              />
              <small id="support-contact-message-help" className="support-contact-field-hint">
                {t("support.contact.messageHint")}
              </small>
              {messageError ? (
                <small id="support-contact-message-error" className="field-error support-contact-field-error">
                  {messageError}
                </small>
              ) : null}
            </label>

            <label className={`support-contact-field ${attachmentError ? "is-invalid" : ""}`}>
              <span>{t("support.contact.attachmentLabel")}</span>
              <input
                type="url"
                name="attachment_url"
                value={attachmentUrl}
                onChange={(event) => {
                  setAttachmentUrl(event.target.value);
                  if (attachmentError) {
                    setAttachmentError("");
                  }
                }}
                placeholder={t("support.contact.attachmentPlaceholder")}
                aria-invalid={attachmentError ? "true" : "false"}
                aria-describedby="support-contact-attachment-help support-contact-attachment-error"
              />
              <small id="support-contact-attachment-help" className="support-contact-field-hint">
                {t("support.contact.attachmentHint")}
              </small>
              {attachmentError ? (
                <small id="support-contact-attachment-error" className="field-error support-contact-field-error">
                  {attachmentError}
                </small>
              ) : null}
            </label>

            <div className="support-contact-checklist card">
              <div>
                <strong>{t("support.contact.checklistTitle")}</strong>
              </div>
              <div className="support-contact-checklist-items">
                {checklistItems.map((item) => (
                  <span key={item} className="support-contact-checklist-item">
                    <i className="fa-solid fa-arrow-right" aria-hidden="true"></i>
                    {item}
                  </span>
                ))}
              </div>
            </div>

            <div className="support-contact-action-rail">
              <Link className="btn-ghost support-contact-secondary" href="/soporte/ayuda">
                {t("account.menu.help")}
              </Link>
            </div>

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
    </main>
  );
}
