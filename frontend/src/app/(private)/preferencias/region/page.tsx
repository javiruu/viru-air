"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import AirLoader from "@/modules/shared/AirLoader";
import { apiFetch } from "@/modules/shared/api";
import { persistLocale, useI18n } from "@/i18n";

type RegionPref = {
  language: string;
  region: string;
  time_format: string;
  decimal_separator: string;
  currency: string;
};

const REGION_OPTIONS = ["ES", "EU", "US", "UK"] as const;
const CURRENCY_OPTIONS = ["EUR", "USD", "GBP"] as const;

export default function PreferenciasRegionPage() {
  const router = useRouter();
  const { t } = useI18n();
  const { notify } = useNotificationCenter();
  const [pref, setPref] = useState<RegionPref | null>(null);
  const [initialPref, setInitialPref] = useState<RegionPref | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    apiFetch<RegionPref>("/preferences/region")
      .then((data) => {
        setPref(data);
        setInitialPref(data);
        if (data?.language) {
          persistLocale(data.language === "en" ? "en" : "es");
        }
      })
      .catch(() => notify({ tone: "error", title: t("preferences.region.loadError"), durationMs: 3200 }));
  }, [notify, t]);

  const dirty = useMemo(() => {
    if (!pref || !initialPref) return false;
    return JSON.stringify(pref) !== JSON.stringify(initialPref);
  }, [pref, initialPref]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!pref) return;
    setSaving(true);
    try {
      await apiFetch<{ status: string }>("/preferences/region", {
        method: "PUT",
        body: JSON.stringify(pref),
      });
      setInitialPref(pref);
      if (pref.language) {
        persistLocale(pref.language === "en" ? "en" : "es");
      }
      notify({ tone: "success", title: t("preferences.region.saveSuccess"), durationMs: 3200 });
    } catch {
      notify({ tone: "error", title: t("preferences.region.saveError"), durationMs: 3200 });
    } finally {
      setSaving(false);
    }
  }

  if (!pref) {
    return (
      <main className="shell" id="main-content">
        <div className="page-header">
          <button className="btn-ghost" type="button" onClick={() => router.push("/dashboard")}>
            {t("shared.actions.back")}
          </button>
          <div className="page-title">
            <h1>{t("preferences.region.title")}</h1>
            <p>{t("preferences.region.subtitleLoading")}</p>
          </div>
        </div>
        <section className="panel panel-soft air-loader-section">
          <AirLoader size={0.85} />
          <p className="muted">{t("preferences.region.loading")}</p>
        </section>
      </main>
    );
  }

  return (
    <main className="shell" id="main-content">
      <div className="page-header">
        <button className="btn-ghost" type="button" onClick={() => router.push("/dashboard")}>
          {t("shared.actions.back")}
        </button>
        <div className="page-title">
          <h1>{t("preferences.region.title")}</h1>
          <p>{t("preferences.region.subtitleMain")}</p>
        </div>
      </div>

      <section className="panel">
        <div className="panel-header">
          <h2>{t("preferences.region.sectionTitle")}</h2>
          <span className="muted">{t("preferences.region.sectionHint")}</span>
        </div>
        <form className="form" onSubmit={onSubmit}>
          <div className="split">
            <label>
              {t("preferences.region.languageLabel")}
              <select
                name="language"
                value={pref.language}
                onChange={(event) => setPref({ ...pref, language: event.target.value })}
              >
                <option value="es">{t("preferences.region.languageOptionSpanish")}</option>
                <option value="en">{t("preferences.region.languageOptionEnglish")}</option>
              </select>
            </label>

            <label>
              {t("preferences.region.regionLabel")}
              <select
                name="region"
                value={pref.region}
                onChange={(event) => setPref({ ...pref, region: event.target.value })}
              >
                {REGION_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="split">
            <label>
              {t("preferences.region.timeFormatLabel")}
              <select
                name="time_format"
                value={pref.time_format}
                onChange={(event) => setPref({ ...pref, time_format: event.target.value })}
              >
                <option value="24h">24h</option>
                <option value="12h">12h</option>
              </select>
            </label>

            <label>
              {t("preferences.region.decimalLabel")}
              <select
                name="decimal_separator"
                value={pref.decimal_separator}
                onChange={(event) => setPref({ ...pref, decimal_separator: event.target.value })}
              >
                <option value=",">{t("preferences.region.decimalComma")}</option>
                <option value=".">{t("preferences.region.decimalDot")}</option>
              </select>
            </label>
          </div>

          <label>
            {t("preferences.region.currencyLabel")}
            <input
              type="text"
              name="currency"
              list="region-currency-options"
              value={pref.currency}
              onChange={(event) => setPref({ ...pref, currency: event.target.value.toUpperCase() })}
            />
            <datalist id="region-currency-options">
              {CURRENCY_OPTIONS.map((option) => (
                <option key={option} value={option} />
              ))}
            </datalist>
          </label>

          <div className="row-actions">
            <button type="submit" className="btn-primary" disabled={saving || !dirty}>
              {saving ? t("preferences.region.saving") : t("preferences.region.saveButton")}
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}
