"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import AirLoader from "@/modules/shared/AirLoader";
import { apiFetch } from "@/modules/shared/api";
import { useI18n } from "@/i18n";

type AppearancePref = {
  theme: "light" | "dark" | "system";
  density: "compact" | "comfortable";
  reduce_motion: boolean;
  high_contrast: boolean;
};

type ToastState = { tone: "success" | "error"; message: string } | null;

export default function PreferenciasAparienciaPage() {
  const router = useRouter();
  const { t } = useI18n();
  const [pref, setPref] = useState<AppearancePref | null>(null);
  const [initialPref, setInitialPref] = useState<AppearancePref | null>(null);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<ToastState>(null);

  const themeOptions = useMemo(
    () => [
      { value: "light" as const, label: t("preferences.appearance.themeLight"), desc: t("preferences.appearance.themeLightDesc") },
      { value: "dark" as const, label: t("preferences.appearance.themeDark"), desc: t("preferences.appearance.themeDarkDesc") },
      { value: "system" as const, label: t("preferences.appearance.themeSystem"), desc: t("preferences.appearance.themeSystemDesc") },
    ],
    [t],
  );

  const densityOptions = useMemo(
    () => [
      { value: "comfortable" as const, label: t("preferences.appearance.densityComfortable"), desc: t("preferences.appearance.densityComfortableDesc") },
      { value: "compact" as const, label: t("preferences.appearance.densityCompact"), desc: t("preferences.appearance.densityCompactDesc") },
    ],
    [t],
  );

  useEffect(() => {
    apiFetch<AppearancePref>("/preferences/appearance")
      .then((data) => {
        setPref(data);
        setInitialPref(data);
      })
      .catch(() => setToast({ tone: "error", message: t("preferences.appearance.loadError") }));
  }, [t]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 3200);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const dirty = useMemo(() => {
    if (!pref || !initialPref) return false;
    return JSON.stringify(pref) !== JSON.stringify(initialPref);
  }, [pref, initialPref]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!pref) return;
    setSaving(true);
    try {
      await apiFetch<{ status: string }>("/preferences/appearance", {
        method: "PUT",
        body: JSON.stringify(pref),
      });
      setInitialPref(pref);
      setToast({ tone: "success", message: t("preferences.appearance.saveSuccess") });
    } catch {
      setToast({ tone: "error", message: t("preferences.appearance.saveError") });
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
            <h1>{t("preferences.appearance.title")}</h1>
            <p>{t("preferences.appearance.subtitle")}</p>
          </div>
        </div>
        <section className="panel panel-soft air-loader-section">
          <AirLoader size={0.85} />
          <p className="muted">{t("preferences.appearance.loading")}</p>
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
          <h1>{t("preferences.appearance.title")}</h1>
          <p>{t("preferences.appearance.subtitle")}</p>
        </div>
      </div>

      <section className="panel">
        <div className="panel-header">
          <h2>{t("preferences.appearance.themeLabel")}</h2>
          <span className="muted">{t("preferences.appearance.themeHint")}</span>
        </div>
        <div className="prefs-chip-row" role="group" aria-label={t("preferences.appearance.themeLabel")}>
          {themeOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              className={`btn-ghost btn-compact ${pref.theme === option.value ? "is-active" : ""}`}
              onClick={() => setPref({ ...pref, theme: option.value })}
              aria-pressed={pref.theme === option.value}
            >
              <strong>{option.label}</strong>
              <span className="panel-note">{option.desc}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>{t("preferences.appearance.densityLabel")}</h2>
          <span className="muted">{t("preferences.appearance.densityHint")}</span>
        </div>
        <div className="prefs-chip-row" role="group" aria-label={t("preferences.appearance.densityLabel")}>
          {densityOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              className={`btn-ghost btn-compact ${pref.density === option.value ? "is-active" : ""}`}
              onClick={() => setPref({ ...pref, density: option.value })}
              aria-pressed={pref.density === option.value}
            >
              <strong>{option.label}</strong>
              <span className="panel-note">{option.desc}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="panel panel-soft">
        <div className="panel-header">
          <h2>{t("preferences.appearance.accessibilityTitle")}</h2>
          <span className="muted">{t("preferences.appearance.accessibilityHint")}</span>
        </div>
        <div className="form">
          <div className="field">
            <span>{t("preferences.appearance.reduceMotion")}</span>
            <span className="hint">{t("preferences.appearance.reduceMotionHint")}</span>
            <button
              type="button"
              role="switch"
              aria-checked={pref.reduce_motion}
              className={`prefs-toggle ${pref.reduce_motion ? "is-on" : ""}`}
              onClick={() => setPref({ ...pref, reduce_motion: !pref.reduce_motion })}
            >
              <span className="prefs-toggle-track" aria-hidden="true">
                <span className="prefs-toggle-knob" />
              </span>
              <span className="prefs-toggle-text">
                {pref.reduce_motion ? t("preferences.search.enabled") : t("preferences.search.disabled")}
              </span>
            </button>
          </div>
          <div className="field">
            <span>{t("preferences.appearance.highContrast")}</span>
            <span className="hint">{t("preferences.appearance.highContrastHint")}</span>
            <button
              type="button"
              role="switch"
              aria-checked={pref.high_contrast}
              className={`prefs-toggle ${pref.high_contrast ? "is-on" : ""}`}
              onClick={() => setPref({ ...pref, high_contrast: !pref.high_contrast })}
            >
              <span className="prefs-toggle-track" aria-hidden="true">
                <span className="prefs-toggle-knob" />
              </span>
              <span className="prefs-toggle-text">
                {pref.high_contrast ? t("preferences.search.enabled") : t("preferences.search.disabled")}
              </span>
            </button>
          </div>
        </div>
      </section>

      <section className="panel">
        <form onSubmit={onSubmit}>
          <div className="row-actions">
            <button type="submit" className="btn-primary" disabled={saving || !dirty}>
              {saving ? t("preferences.appearance.saving") : t("preferences.appearance.saveButton")}
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
