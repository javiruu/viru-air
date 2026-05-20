"use client";

import { useState } from "react";

import { persistLocale, useI18n, type Locale } from "@/i18n";
import { apiFetch } from "@/modules/shared/api";

type RegionPref = {
  language: string;
  region: string;
  time_format: string;
  decimal_separator: string;
  currency: string;
};

export default function LanguageToggle() {
  const { locale, t } = useI18n();
  const [saving, setSaving] = useState(false);

  async function onToggleLanguage() {
    if (saving) return;
    setSaving(true);
    const nextLocale: Locale = locale === "en" ? "es" : "en";
    try {
      const pref = await apiFetch<RegionPref>("/preferences/region");
      await apiFetch<{ status: string }>("/preferences/region", {
        method: "PUT",
        body: JSON.stringify({
          ...pref,
          language: nextLocale,
        }),
      });
      persistLocale(nextLocale);
      window.location.reload();
    } finally {
      setSaving(false);
    }
  }

  const currentLabel = locale === "en" ? "EN" : "ES";

  return (
    <button
      type="button"
      className="language-toggle"
      onClick={onToggleLanguage}
      disabled={saving}
      aria-label={t("shared.a11y.changeLanguage")}
      title={t("shared.labels.language")}
    >
      <span className="language-toggle__label">{currentLabel}</span>
    </button>
  );
}
