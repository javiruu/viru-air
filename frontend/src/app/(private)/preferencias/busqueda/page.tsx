"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import AirLoader from "@/modules/shared/AirLoader";
import { apiFetch } from "@/modules/shared/api";
import { useI18n } from "@/i18n";

type Pref = {
  default_radius_km: number;
  include_stops_default: boolean;
  avoid_departure_before: string | null;
  preferred_currency: string;
  language: string;
};

type PrefErrors = Partial<Record<keyof Pref, string>>;
type ToastState = { tone: "success" | "error"; message: string } | null;

const QUICK_TIME_CHIPS = ["06:00", "07:00", "08:30", "10:00"] as const;
const MIN_RADIUS_KM = 0;
const MAX_RADIUS_KM = 500;
const DEFAULT_TIME_PLACEHOLDER = "08:30";

function isValidHour(value: string) {
  return /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(value);
}

export default function PreferenciasBusquedaPage() {
  const router = useRouter();
  const { t } = useI18n();
  const [pref, setPref] = useState<Pref | null>(null);
  const [initialPref, setInitialPref] = useState<Pref | null>(null);
  const [errors, setErrors] = useState<PrefErrors>({});
  const [toast, setToast] = useState<ToastState>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    apiFetch<Pref>("/preferences/search")
      .then((data) => {
        setPref(data);
        setInitialPref(data);
      })
      .catch(() => setToast({ tone: "error", message: t("preferences.search.loadError") }));
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

  function validate(nextPref: Pref): PrefErrors {
    const nextErrors: PrefErrors = {};

    if (
      Number.isNaN(nextPref.default_radius_km) ||
      nextPref.default_radius_km < MIN_RADIUS_KM ||
      nextPref.default_radius_km > MAX_RADIUS_KM
    ) {
      nextErrors.default_radius_km = t("preferences.search.rangeError", { min: MIN_RADIUS_KM, max: MAX_RADIUS_KM });
    }

    if (
      nextPref.avoid_departure_before &&
      nextPref.avoid_departure_before.trim() &&
      !isValidHour(nextPref.avoid_departure_before)
    ) {
      nextErrors.avoid_departure_before = t("preferences.search.timeError");
    }

    return nextErrors;
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!pref) return;

    const nextErrors = validate(pref);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      setToast({ tone: "error", message: t("preferences.search.validationError") });
      return;
    }
    if (!dirty) return;

    setSaving(true);
    try {
      await apiFetch<{ status: string }>("/preferences/search", {
        method: "PUT",
        body: JSON.stringify(pref),
      });
      setInitialPref(pref);
      setToast({ tone: "success", message: t("preferences.search.saveSuccess") });
    } catch {
      setToast({ tone: "error", message: t("preferences.search.saveError") });
    } finally {
      setSaving(false);
    }
  }

  function onRadiusChange(value: string) {
    if (!pref) return;
    const parsed = Number(value);
    setPref({
      ...pref,
      default_radius_km: Number.isNaN(parsed) ? MIN_RADIUS_KM : parsed,
    });
  }

  if (!pref) {
    return (
      <main className="shell" id="main-content">
        <div className="page-header">
          <button className="btn-ghost" type="button" onClick={() => router.push("/dashboard")}>
            {t("shared.actions.back")}
          </button>
          <div className="page-title">
            <h1>{t("preferences.search.title")}</h1>
            <p>{t("preferences.search.subtitle")}</p>
          </div>
        </div>
        <section className="panel panel-soft air-loader-section">
          <AirLoader size={0.85} />
          <p className="muted">{t("preferences.search.loading")}</p>
        </section>
      </main>
    );
  }

  const radiusDriveHours = (pref.default_radius_km / 100).toFixed(1);

  return (
    <main className="shell" id="main-content">
      <div className="page-header">
        <button className="btn-ghost" type="button" onClick={() => router.push("/dashboard")}>
          {t("shared.actions.back")}
        </button>
        <div className="page-title">
          <h1>{t("preferences.search.title")}</h1>
          <p>{t("preferences.search.subtitleStrong")}</p>
        </div>
      </div>

      <section className="panel">
        <div className="panel-header">
          <h2>{t("preferences.search.sectionTitle")}</h2>
          <span className="muted">{t("preferences.search.sectionHint")}</span>
        </div>
        <form className="form" onSubmit={onSubmit}>
          <label className="field" htmlFor="pref-radius">
            {t("preferences.search.radiusLabel")}
            <span className="hint">{t("preferences.search.radiusHint")}</span>
            <div className="prefs-radius-row">
              <input
                id="pref-radius"
                type="range"
                min={MIN_RADIUS_KM}
                max={MAX_RADIUS_KM}
                step={5}
                value={Math.min(MAX_RADIUS_KM, Math.max(MIN_RADIUS_KM, pref.default_radius_km))}
                onChange={(event) => onRadiusChange(event.target.value)}
              />
              <input
                className="prefs-control"
                type="number"
                min={MIN_RADIUS_KM}
                max={MAX_RADIUS_KM}
                name="default_radius_km"
                autoComplete="off"
                value={pref.default_radius_km}
                onChange={(event) => onRadiusChange(event.target.value)}
              />
            </div>
            <span className="hint">
              {t("preferences.search.radiusSummary", { value: pref.default_radius_km, hours: radiusDriveHours })}
            </span>
            {errors.default_radius_km ? <span className="prefs-error">{errors.default_radius_km}</span> : null}
          </label>

          <div className="field">
            <span>{t("preferences.search.includeStops")}</span>
            <span className="hint">{t("preferences.search.includeStopsHint")}</span>
            <button
              type="button"
              role="switch"
              aria-checked={pref.include_stops_default}
              className={`prefs-toggle ${pref.include_stops_default ? "is-on" : ""}`}
              onClick={() => setPref({ ...pref, include_stops_default: !pref.include_stops_default })}
            >
              <span className="prefs-toggle-track" aria-hidden="true">
                <span className="prefs-toggle-knob" />
              </span>
              <span className="prefs-toggle-text">
                {pref.include_stops_default ? t("preferences.search.enabled") : t("preferences.search.disabled")}
              </span>
            </button>
          </div>

          <label className="field" htmlFor="pref-time">
            {t("preferences.search.avoidBefore")}
            <span className="hint">{t("preferences.search.avoidBeforeHint")}</span>
            <input
              id="pref-time"
              className="prefs-control"
              type="time"
              name="avoid_departure_before"
              autoComplete="off"
              value={pref.avoid_departure_before ?? ""}
              placeholder={DEFAULT_TIME_PLACEHOLDER}
              onChange={(event) => setPref({ ...pref, avoid_departure_before: event.target.value || null })}
            />
            <div className="prefs-chip-row" role="group" aria-label={t("preferences.search.quickTimes")}>
              {QUICK_TIME_CHIPS.map((timeValue) => (
                <button
                  key={timeValue}
                  type="button"
                  className={`btn-ghost btn-compact ${pref.avoid_departure_before === timeValue ? "is-active" : ""}`}
                  onClick={() => setPref({ ...pref, avoid_departure_before: timeValue })}
                >
                  {timeValue}
                </button>
              ))}
            </div>
            {errors.avoid_departure_before ? <span className="prefs-error">{errors.avoid_departure_before}</span> : null}
          </label>

          <div className="row-actions">
            <button type="submit" className="btn-primary" disabled={saving || !dirty}>
              {saving ? t("preferences.search.saving") : t("preferences.search.saveButton")}
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
