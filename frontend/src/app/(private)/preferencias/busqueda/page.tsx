"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { useI18n } from "@/i18n";
import AirLoader from "@/modules/shared/AirLoader";
import { apiFetch } from "@/modules/shared/api";
import { Pref } from "@/modules/quick-search/types";
import {
  buildSearchPreferenceSummary,
  SEARCH_PREF_DEFAULT_TIME_PLACEHOLDER,
  SEARCH_PREF_LATE_TIME_CHIPS,
  SEARCH_PREF_LATE_TIME_PLACEHOLDER,
  SEARCH_PREF_MAX_RADIUS_KM,
  SEARCH_PREF_MIN_RADIUS_KM,
  SEARCH_PREF_QUICK_TIME_CHIPS,
  validateSearchPreferences,
  SearchPreferenceErrors,
} from "@/modules/preferences/searchPreferences";

function PreferenceIcon({ path }: { path: string }) {
  return (
    <span className="prefs-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d={path} />
      </svg>
    </span>
  );
}

export default function PreferenciasBusquedaPage() {
  const router = useRouter();
  const { t } = useI18n();
  const { notify } = useNotificationCenter();
  const [pref, setPref] = useState<Pref | null>(null);
  const [initialPref, setInitialPref] = useState<Pref | null>(null);
  const [errors, setErrors] = useState<SearchPreferenceErrors>({});
  const [saving, setSaving] = useState(false);
  const [loadFailed, setLoadFailed] = useState(false);

  const loadPreferences = useCallback(() => {
    setLoadFailed(false);
    apiFetch<Pref>("/preferences/search")
      .then((data) => {
        const normalized: Pref = {
          ...data,
          country_price_hint_mode_default: data.country_price_hint_mode_default || "min",
          calendar_hint_bucket_mode_default: data.calendar_hint_bucket_mode_default || "monthly_terciles",
          calendar_hint_guideline_low_max_default: Number(data.calendar_hint_guideline_low_max_default ?? 90),
          calendar_hint_guideline_mid_max_default: Number(data.calendar_hint_guideline_mid_max_default ?? 150),
          preferred_currency: data.preferred_currency || "EUR",
        };
        setPref(normalized);
        setInitialPref(normalized);
      })
      .catch(() => {
        setLoadFailed(true);
        notify({ tone: "error", title: t("preferences.search.loadError"), durationMs: 3200 });
      });
  }, [notify, t]);

  useEffect(() => {
    loadPreferences();
    // we intentionally reload when translation context changes
  }, [loadPreferences]);

  const dirty = useMemo(() => {
    if (!pref || !initialPref) return false;
    return JSON.stringify(pref) !== JSON.stringify(initialPref);
  }, [pref, initialPref]);

  const summary = useMemo(() => {
    if (!pref) return null;
    return buildSearchPreferenceSummary(pref, (key) => t(key));
  }, [pref, t]);

  function updatePref<K extends keyof Pref>(key: K, value: Pref[K]) {
    if (!pref) return;
    setPref({ ...pref, [key]: value });
  }

  function onRadiusChange(value: string) {
    if (!pref) return;
    const parsed = Number(value);
    setPref({
      ...pref,
      default_radius_km: Number.isNaN(parsed) ? SEARCH_PREF_MIN_RADIUS_KM : parsed,
    });
  }

  function onGuidelineThresholdChange(field: "calendar_hint_guideline_low_max_default" | "calendar_hint_guideline_mid_max_default", value: string) {
    if (!pref) return;
    const parsed = Number(value);
    updatePref(field, Number.isFinite(parsed) ? parsed : 0);
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!pref) return;

    const nextErrors = validateSearchPreferences(pref, t);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      notify({ tone: "error", title: t("preferences.search.validationError"), durationMs: 3200 });
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
      notify({ tone: "success", title: t("preferences.search.saveSuccess"), durationMs: 3200 });
    } catch {
      notify({ tone: "error", title: t("preferences.search.saveError"), durationMs: 3200 });
    } finally {
      setSaving(false);
    }
  }

  if (!pref || !summary) {
    return (
      <main className="shell prefs-shell" id="main-content">
        <div className="page-header prefs-header">
          <button className="btn-ghost" type="button" onClick={() => router.push("/preferencias")}>
            {t("shared.actions.back")}
          </button>
          <div className="page-title">
            <h1>{t("preferences.search.title")}</h1>
            <p>{t("preferences.search.subtitle")}</p>
          </div>
        </div>
        <section className="panel panel-soft air-loader-section">
          {loadFailed ? (
            <>
              <p className="muted">{t("preferences.search.loadError")}</p>
              <button className="btn-primary" type="button" onClick={loadPreferences}>
                {t("shared.actions.retry")}
              </button>
            </>
          ) : (
            <>
              <AirLoader size={0.85} />
              <p className="muted">{t("preferences.search.loading")}</p>
            </>
          )}
        </section>
      </main>
    );
  }

  const radiusDriveHours = (pref.default_radius_km / 100).toFixed(1);

  return (
    <main className="shell prefs-shell" id="main-content">
      <div className="page-header prefs-header">
        <button className="btn-ghost" type="button" onClick={() => router.push("/preferencias")}>
          {t("shared.actions.back")}
        </button>
        <div className="page-title">
          <h1>{t("preferences.search.title")}</h1>
          <p>{t("preferences.search.subtitleStrong")}</p>
        </div>
        {dirty ? <span className="status-pill warning">{t("preferences.search.pendingBadge")}</span> : null}
      </div>

      <section className="panel prefs-hero prefs-search-hero">
        <div className="prefs-hero-copy">
          <p className="prefs-kicker">{t("preferences.search.heroKicker")}</p>
          <h2>{summary.title}</h2>
          <p>{summary.body}</p>
        </div>
        <div className="prefs-hero-chips">
          {summary.chips.map((chip) => (
            <span key={chip} className="status-pill info">
              {chip}
            </span>
          ))}
        </div>
      </section>

      <form className="prefs-form prefs-search-form" onSubmit={onSubmit}>
        <div className="prefs-search-grid">
          <section className="panel prefs-card prefs-search-card prefs-search-card-coverage">
            <div className="prefs-card-head">
              <PreferenceIcon path="M3 12h4l2-3 4 6 3-4h5" />
              <div>
                <h2>{t("preferences.search.coverageTitle")}</h2>
                <p className="panel-note">{t("preferences.search.coverageHint")}</p>
              </div>
            </div>

            <div className="prefs-search-toggle-grid">
              <div className="field">
                <span>{t("preferences.search.nearbyOrigins")}</span>
                <span className="hint">{t("preferences.search.nearbyOriginsHint")}</span>
                <button
                  type="button"
                  role="switch"
                  aria-checked={pref.include_nearby_origins_default}
                  className={`prefs-toggle ${pref.include_nearby_origins_default ? "is-on" : ""}`}
                  onClick={() => updatePref("include_nearby_origins_default", !pref.include_nearby_origins_default)}
                >
                  <span className="prefs-toggle-track" aria-hidden="true">
                    <span className="prefs-toggle-knob" />
                  </span>
                  <span className="prefs-toggle-text">
                    {pref.include_nearby_origins_default ? t("preferences.search.enabled") : t("preferences.search.disabled")}
                  </span>
                </button>
              </div>

              <div className="field">
                <span>{t("preferences.search.nearbyDestinations")}</span>
                <span className="hint">{t("preferences.search.nearbyDestinationsHint")}</span>
                <button
                  type="button"
                  role="switch"
                  aria-checked={pref.include_nearby_destinations_default}
                  className={`prefs-toggle ${pref.include_nearby_destinations_default ? "is-on" : ""}`}
                  onClick={() => updatePref("include_nearby_destinations_default", !pref.include_nearby_destinations_default)}
                >
                  <span className="prefs-toggle-track" aria-hidden="true">
                    <span className="prefs-toggle-knob" />
                  </span>
                  <span className="prefs-toggle-text">
                    {pref.include_nearby_destinations_default ? t("preferences.search.enabled") : t("preferences.search.disabled")}
                  </span>
                </button>
              </div>
            </div>

            <label className="field" htmlFor="pref-country-hint-mode">
              {t("preferences.search.countryHintMode")}
              <span className="hint">{t("preferences.search.countryHintModeHint")}</span>
              <select
                id="pref-country-hint-mode"
                className="prefs-control"
                value={pref.country_price_hint_mode_default || "min"}
                onChange={(event) => updatePref("country_price_hint_mode_default", event.target.value as Pref["country_price_hint_mode_default"])}
              >
                <option value="min">{t("preferences.search.countryHintModeMin")}</option>
                <option value="median">{t("preferences.search.countryHintModeMedian")}</option>
                <option value="fixed_route">{t("preferences.search.countryHintModeFixedRoute")}</option>
              </select>
            </label>

            <label className="field" htmlFor="pref-calendar-bucket-mode">
              {t("preferences.search.calendarHintBucketMode")}
              <span className="hint">{t("preferences.search.calendarHintBucketModeHint")}</span>
              <select
                id="pref-calendar-bucket-mode"
                className="prefs-control"
                value={pref.calendar_hint_bucket_mode_default || "monthly_terciles"}
                onChange={(event) => updatePref("calendar_hint_bucket_mode_default", event.target.value as Pref["calendar_hint_bucket_mode_default"])}
              >
                <option value="monthly_terciles">{t("preferences.search.calendarHintBucketModeMonthly")}</option>
                <option value="guidelines">{t("preferences.search.calendarHintBucketModeGuidelines")}</option>
              </select>
            </label>

            {pref.calendar_hint_bucket_mode_default === "guidelines" ? (
              <div className="field">
                <span>{t("preferences.search.calendarHintGuidelinesTitle")}</span>
                <div className="prefs-radius-row">
                  <label className="field" htmlFor="pref-guideline-low">
                    {t("preferences.search.calendarHintGuidelineLowLabel")}
                    <input
                      id="pref-guideline-low"
                      className="prefs-control"
                      type="number"
                      min={0}
                      step={1}
                      value={pref.calendar_hint_guideline_low_max_default}
                      onChange={(event) => onGuidelineThresholdChange("calendar_hint_guideline_low_max_default", event.target.value)}
                    />
                    {errors.calendar_hint_guideline_low_max_default ? (
                      <span className="prefs-error">{errors.calendar_hint_guideline_low_max_default}</span>
                    ) : null}
                  </label>
                  <label className="field" htmlFor="pref-guideline-mid">
                    {t("preferences.search.calendarHintGuidelineMidLabel")}
                    <input
                      id="pref-guideline-mid"
                      className="prefs-control"
                      type="number"
                      min={0}
                      step={1}
                      value={pref.calendar_hint_guideline_mid_max_default}
                      onChange={(event) => onGuidelineThresholdChange("calendar_hint_guideline_mid_max_default", event.target.value)}
                    />
                    {errors.calendar_hint_guideline_mid_max_default ? (
                      <span className="prefs-error">{errors.calendar_hint_guideline_mid_max_default}</span>
                    ) : null}
                  </label>
                </div>
                <span className="hint">
                  {t("preferences.search.calendarHintGuidelinesHint", {
                    low: pref.calendar_hint_guideline_low_max_default,
                    mid: pref.calendar_hint_guideline_mid_max_default,
                    currency: pref.preferred_currency || "EUR",
                  })}
                </span>
              </div>
            ) : null}

            <label className="field" htmlFor="pref-radius">
              {t("preferences.search.radiusLabel")}
              <span className="hint">{t("preferences.search.radiusHint")}</span>
              <div className="prefs-radius-row">
                <input
                  id="pref-radius"
                  type="range"
                  min={SEARCH_PREF_MIN_RADIUS_KM}
                  max={SEARCH_PREF_MAX_RADIUS_KM}
                  step={5}
                  value={Math.min(SEARCH_PREF_MAX_RADIUS_KM, Math.max(SEARCH_PREF_MIN_RADIUS_KM, pref.default_radius_km))}
                  onChange={(event) => onRadiusChange(event.target.value)}
                />
                <input
                  className="prefs-control"
                  type="number"
                  min={SEARCH_PREF_MIN_RADIUS_KM}
                  max={SEARCH_PREF_MAX_RADIUS_KM}
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
          </section>

          <section className="panel prefs-card prefs-search-card prefs-search-card-timing">
            <div className="prefs-card-head">
              <PreferenceIcon path="M12 6v6l4 2M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z" />
              <div>
                <h2>{t("preferences.search.timingTitle")}</h2>
                <p className="panel-note">{t("preferences.search.timingHint")}</p>
              </div>
            </div>

            <div className="prefs-search-time-grid">
              <label className="field" htmlFor="pref-time-after">
                {t("preferences.search.avoidBefore")}
                <span className="hint">{t("preferences.search.avoidBeforeHint")}</span>
                <input
                  id="pref-time-after"
                  className="prefs-control"
                  type="time"
                  name="avoid_departure_before"
                  autoComplete="off"
                  value={pref.avoid_departure_before ?? ""}
                  placeholder={SEARCH_PREF_DEFAULT_TIME_PLACEHOLDER}
                  onChange={(event) => updatePref("avoid_departure_before", event.target.value || null)}
                />
                <div className="prefs-chip-row" role="group" aria-label={t("preferences.search.quickTimes")}>
                  {SEARCH_PREF_QUICK_TIME_CHIPS.map((timeValue) => (
                    <button
                      key={timeValue}
                      type="button"
                      className={`btn-ghost btn-compact ${pref.avoid_departure_before === timeValue ? "is-active" : ""}`}
                      onClick={() => updatePref("avoid_departure_before", timeValue)}
                    >
                      {timeValue}
                    </button>
                  ))}
                </div>
                {errors.avoid_departure_before ? <span className="prefs-error">{errors.avoid_departure_before}</span> : null}
              </label>

              <label className="field" htmlFor="pref-time-before">
                {t("preferences.search.departBefore")}
                <span className="hint">{t("preferences.search.departBeforeHint")}</span>
                <input
                  id="pref-time-before"
                  className="prefs-control"
                  type="time"
                  name="depart_before_default"
                  autoComplete="off"
                  value={pref.depart_before_default ?? ""}
                  placeholder={SEARCH_PREF_LATE_TIME_PLACEHOLDER}
                  onChange={(event) => updatePref("depart_before_default", event.target.value || null)}
                />
                <div className="prefs-chip-row" role="group" aria-label={t("preferences.search.lateTimes")}>
                  {SEARCH_PREF_LATE_TIME_CHIPS.map((timeValue) => (
                    <button
                      key={timeValue}
                      type="button"
                      className={`btn-ghost btn-compact ${pref.depart_before_default === timeValue ? "is-active" : ""}`}
                      onClick={() => updatePref("depart_before_default", timeValue)}
                    >
                      {timeValue}
                    </button>
                  ))}
                </div>
                {errors.depart_before_default ? <span className="prefs-error">{errors.depart_before_default}</span> : null}
              </label>
            </div>

            <div className="field">
              <span>{t("preferences.search.strictMode")}</span>
              <span className="hint">{t("preferences.search.strictModeHint")}</span>
              <button
                type="button"
                role="switch"
                aria-checked={pref.strict_filters_default}
                className={`prefs-toggle ${pref.strict_filters_default ? "is-on" : ""}`}
                onClick={() => updatePref("strict_filters_default", !pref.strict_filters_default)}
              >
                <span className="prefs-toggle-track" aria-hidden="true">
                  <span className="prefs-toggle-knob" />
                </span>
                <span className="prefs-toggle-text">
                  {pref.strict_filters_default ? t("preferences.search.enabled") : t("preferences.search.disabled")}
                </span>
              </button>
            </div>
          </section>
        </div>

        <section className="panel prefs-card prefs-search-card prefs-search-card-connectivity">
          <div className="prefs-card-head">
            <PreferenceIcon path="M2.5 12h7m5 0h7M9.5 9l3 3-3 3m5-6l3 3-3 3" />
            <div>
              <h2>{t("preferences.search.connectivityTitle")}</h2>
              <p className="panel-note">{t("preferences.search.connectivityHint")}</p>
            </div>
          </div>

          <div className="field">
            <span>{t("preferences.search.includeStops")}</span>
            <span className="hint">{t("preferences.search.includeStopsHint")}</span>
            <button
              type="button"
              role="switch"
              aria-checked={pref.include_stops_default}
              className={`prefs-toggle ${pref.include_stops_default ? "is-on" : ""}`}
              onClick={() => updatePref("include_stops_default", !pref.include_stops_default)}
            >
              <span className="prefs-toggle-track" aria-hidden="true">
                <span className="prefs-toggle-knob" />
              </span>
              <span className="prefs-toggle-text">
                {pref.include_stops_default ? t("preferences.search.enabled") : t("preferences.search.disabled")}
              </span>
            </button>
            <div className="panel panel-soft prefs-inline-callout prefs-search-inline-callout">
              <strong>{t("preferences.search.connectivityCalloutTitle")}</strong>
              <p className="panel-note">{t("preferences.search.connectivityCalloutBody")}</p>
            </div>
          </div>
        </section>

        <section className="panel panel-soft prefs-savebar">
          <div className="prefs-savebar-copy">
            <strong>{dirty ? t("preferences.search.unsavedTitle") : t("preferences.search.savedTitle")}</strong>
            <span>{dirty ? t("preferences.search.unsavedBody") : t("preferences.search.savedBody")}</span>
          </div>
          <div className="row-actions">
            <button type="button" className="btn-ghost" onClick={() => setPref(initialPref)}>
              {t("preferences.search.resetButton")}
            </button>
            <button type="submit" className="btn-primary" disabled={saving || !dirty}>
              {saving ? t("preferences.search.saving") : t("preferences.search.saveButton")}
            </button>
          </div>
        </section>
      </form>
    </main>
  );
}
