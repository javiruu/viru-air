"use client";

import { type FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { BoneyardForm } from "@/modules/shared/BoneyardLoad";
import { useI18n } from "@/i18n";
import {
  getAppearancePreferencesApiV1PreferencesAppearanceGet,
  setAppearancePreferencesApiV1PreferencesAppearancePut,
} from "@/api/generated/preferences/preferences";

type AppearancePref = {
  theme: "light" | "dark" | "system";
  density: "compact" | "comfortable";
  reduce_motion: boolean;
  high_contrast: boolean;
};

export default function PreferenciasAparienciaPage() {
  const router = useRouter();
  const { t } = useI18n();
  const { notify } = useNotificationCenter();
  const queryClient = useQueryClient();

  const [pref, setPref] = useState<AppearancePref | null>(null);
  const [initialPref, setInitialPref] = useState<AppearancePref | null>(null);

  const themeOptions = useMemo(
    () => [
      {
        value: "light" as const,
        label: t("preferences.appearance.themeLight"),
        desc: t("preferences.appearance.themeLightDesc"),
      },
      {
        value: "dark" as const,
        label: t("preferences.appearance.themeDark"),
        desc: t("preferences.appearance.themeDarkDesc"),
      },
      {
        value: "system" as const,
        label: t("preferences.appearance.themeSystem"),
        desc: t("preferences.appearance.themeSystemDesc"),
      },
    ],
    [t],
  );

  const densityOptions = useMemo(
    () => [
      {
        value: "comfortable" as const,
        label: t("preferences.appearance.densityComfortable"),
        desc: t("preferences.appearance.densityComfortableDesc"),
      },
      {
        value: "compact" as const,
        label: t("preferences.appearance.densityCompact"),
        desc: t("preferences.appearance.densityCompactDesc"),
      },
    ],
    [t],
  );

  const prefQuery = useQuery({
    queryKey: ["appearancePref"],
    queryFn: () => getAppearancePreferencesApiV1PreferencesAppearanceGet(),
  });

  useEffect(() => {
    if (prefQuery.data) {
      const data = prefQuery.data as unknown as AppearancePref;
      setPref(data);
      setInitialPref(data);
    }
  }, [prefQuery.data]);

  useEffect(() => {
    if (prefQuery.isError) {
      notify({ tone: "error", title: t("preferences.appearance.loadError"), durationMs: 3200 });
    }
  }, [prefQuery.isError, notify, t]);

  const prefMutation = useMutation({
    mutationFn: (data: AppearancePref) =>
      setAppearancePreferencesApiV1PreferencesAppearancePut(data as any),
    onSuccess: (data) => {
      queryClient.setQueryData(["appearancePref"], data);
      setInitialPref(pref);
      notify({ tone: "success", title: t("preferences.appearance.saveSuccess"), durationMs: 3200 });
    },
    onError: () => {
      notify({ tone: "error", title: t("preferences.appearance.saveError"), durationMs: 3200 });
    },
  });

  const dirty = useMemo(() => {
    if (!pref || !initialPref) return false;
    return JSON.stringify(pref) !== JSON.stringify(initialPref);
  }, [pref, initialPref]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!pref) return;
    prefMutation.mutate(pref);
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
        <BoneyardForm
          name="preferences-appearance-load"
          className="air-loader-section"
          ariaLabel={t("preferences.appearance.loading")}
        />
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

      <section className="panel prefs-priority-block">
        <div className="panel-header">
          <h2>{t("preferences.appearance.themeLabel")}</h2>
          <span className="muted">{t("preferences.appearance.themeHint")}</span>
        </div>
        <div
          className="prefs-chip-row"
          role="group"
          aria-label={t("preferences.appearance.themeLabel")}
        >
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

      <section className="panel panel-soft prefs-secondary-block">
        <div className="panel-header">
          <h2>{t("preferences.appearance.densityLabel")}</h2>
          <span className="muted">{t("preferences.appearance.densityHint")}</span>
        </div>
        <div
          className="prefs-chip-row"
          role="group"
          aria-label={t("preferences.appearance.densityLabel")}
        >
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

      <details className="panel panel-soft prefs-advanced" open={false}>
        <summary>
          <span>{t("preferences.appearance.accessibilityTitle")}</span>
          <span className="panel-note">{t("preferences.appearance.accessibilityHint")}</span>
        </summary>
        <div className="prefs-advanced-content form">
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
                {pref.reduce_motion
                  ? t("preferences.search.enabled")
                  : t("preferences.search.disabled")}
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
                {pref.high_contrast
                  ? t("preferences.search.enabled")
                  : t("preferences.search.disabled")}
              </span>
            </button>
          </div>
        </div>
      </details>

      <section className="panel">
        <form onSubmit={onSubmit}>
          <div className="row-actions">
            <button type="submit" className="btn-primary" disabled={prefMutation.isPending || !dirty}>
              {prefMutation.isPending ? t("preferences.appearance.saving") : t("preferences.appearance.saveButton")}
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}
