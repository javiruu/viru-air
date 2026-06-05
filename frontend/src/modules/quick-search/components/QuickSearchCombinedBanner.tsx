"use client";

import type { QuickSearchLocale } from "@/modules/shared/quickSearchCopy";
import { getQuickSearchCopy } from "@/modules/shared/quickSearchCopy";

// ── Types ────────────────────────────────────────────────────────────

type Props = {
  /** Combined estimated price (outbound + return). */
  combinedPrice: number | null;
  /** Currency code (e.g. EUR). */
  currency: string;
  /** Whether we're in dual mode (only renders when true). */
  visible: boolean;
  /** Called when the user clicks "Save combination". */
  onSave: () => void;
  /** Save button state. */
  saving?: boolean;
  /** Locale for i18n. */
  locale?: QuickSearchLocale;
  /** Optional className. */
  className?: string;
};

// ── Component ────────────────────────────────────────────────────────

/**
 * Sticky combined‑price banner at the bottom of the dual‑panel workspace.
 *
 * Shows the estimated round‑trip price (outbound + return) with a
 * gradient‑text accent and a primary "Save combination" CTA.
 */
export function QuickSearchCombinedBanner({
  combinedPrice,
  currency,
  visible,
  onSave,
  saving = false,
  locale = "es",
  className,
}: Props) {
  const { t } = getQuickSearchCopy(locale);

  if (!visible) return null;

  const formatter = new Intl.NumberFormat(locale === "en" ? "en-US" : "es-ES", {
    style: "currency",
    currency: currency || "EUR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });

  const priceLabel =
    combinedPrice != null && combinedPrice > 0
      ? formatter.format(combinedPrice)
      : "--";

  return (
    <div
      className={`qs-dual-combined${className ? ` ${className}` : ""}`}
      role="complementary"
      aria-label={t("combinedPrice")}
    >
      <span className="qs-dual-combined__label">{t("combinedPrice")}</span>
      <span className="qs-dual-combined__price">{priceLabel}</span>

      <button
        type="button"
        className="qs-dual-combined__save"
        disabled={saving}
        onClick={onSave}
      >
        {saving ? (
          <span className="qs-dual-combined__saving" aria-label={t("savingCombination")}>
            <svg
              className="qs-spinner"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              aria-hidden="true"
            >
              <circle
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeDasharray="31.4 31.4"
                strokeLinecap="round"
              />
            </svg>
            {t("savingCombination")}
          </span>
        ) : (
          <span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2v16z"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            {t("saveCombination")}
          </span>
        )}
      </button>
    </div>
  );
}
