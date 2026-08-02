"use client";

import { useI18n } from "@/i18n";

type Props = {
  onRetry: () => void;
};

export function ErrorFallback({ onRetry }: Props) {
  const { t } = useI18n();
  return (
    <section className="notice notice-error section-gap" role="alert" aria-live="assertive">
      <div>
        <strong>{t("errors.sectionLoadFailed")}</strong>
        <p>{t("errors.tryReload")}</p>
      </div>
      <div className="notice-actions">
        <button type="button" className="btn-secondary btn-compact" onClick={onRetry}>
          {t("actions.retry")}
        </button>
      </div>
    </section>
  );
}
