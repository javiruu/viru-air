"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { useI18n } from "@/i18n";
import { deleteDoorToDoorLocation, fetchSavedDoorToDoorLocation, saveDoorToDoorLocation } from "@/modules/door-to-door/api";
import type { DoorToDoorLocationType, DoorToDoorSavedLocation } from "@/modules/door-to-door/types";
import { Skeleton } from "@/modules/shared/Skeleton";

export default function PreferenciasPuertaAPuertaPage() {
  const router = useRouter();
  const { t } = useI18n();
  const { notify } = useNotificationCenter();
  const [saved, setSaved] = useState<DoorToDoorSavedLocation | null>(null);
  const [label, setLabel] = useState(t("doorToDoor.defaults.origin"));
  const [type, setType] = useState<DoorToDoorLocationType>("city");
  const [lat, setLat] = useState("36.834");
  const [lng, setLng] = useState("-2.463");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchSavedDoorToDoorLocation()
      .then((location) => {
        setSaved(location);
        if (location) {
          setLabel(location.label);
          setType(location.type);
          setLat(location.lat == null ? "" : String(location.lat));
          setLng(location.lng == null ? "" : String(location.lng));
        }
      })
      .finally(() => setLoading(false));
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      const next = await saveDoorToDoorLocation({
        label,
        type,
        lat: lat ? Number(lat) : null,
        lng: lng ? Number(lng) : null,
      });
      setSaved(next);
      notify({ tone: "success", title: t("doorToDoor.preferences.savedToast") });
    } catch {
      notify({ tone: "error", title: t("doorToDoor.preferences.saveError") });
    } finally {
      setSaving(false);
    }
  }

  async function onDelete() {
    await deleteDoorToDoorLocation();
    setSaved(null);
    setLabel("");
    setLat("");
    setLng("");
    notify({ tone: "success", title: t("doorToDoor.preferences.deletedToast") });
  }

  return (
    <main className="shell prefs-shell" id="main-content">
      <div className="page-header prefs-header">
        <button className="btn-ghost" type="button" onClick={() => router.push("/preferencias")}>{t("shared.actions.back")}</button>
        <div className="page-title">
          <h1>{t("doorToDoor.title")}</h1>
          <p>{t("doorToDoor.preferences.subtitle")}</p>
        </div>
      </div>

      <section className="panel prefs-hero d2d-prefs-hero">
        <div>
          <p className="prefs-kicker">{t("doorToDoor.preferences.kicker")}</p>
          <h2>{saved ? saved.label : t("doorToDoor.preferences.emptySaved")}</h2>
          <p className="prefs-hero-summary">{t("doorToDoor.preferences.permission")}</p>
        </div>
        {saved ? <span className="status-pill success">{t("doorToDoor.preferences.saved")}</span> : <span className="status-pill warning">{t("doorToDoor.preferences.pending")}</span>}
      </section>

      <form className="panel panel-soft prefs-form d2d-location-form prefs-priority-block" onSubmit={onSubmit}>
        {loading ? (
          <div className="air-loader-section" role="status" aria-live="polite" aria-label={t("doorToDoor.preferences.loading")} aria-busy="true">
            <Skeleton variant="line" width="62%" />
          </div>
        ) : null}
        <label className="field">
          {t("doorToDoor.preferences.label")}
          <input className="prefs-control" value={label} onChange={(event) => setLabel(event.target.value)} />
        </label>
        <label className="field">
          {t("doorToDoor.preferences.type")}
          <select className="prefs-control" value={type} onChange={(event) => setType(event.target.value as DoorToDoorLocationType)}>
            <option value="city">{t("doorToDoor.preferences.city")}</option>
            <option value="address">{t("doorToDoor.preferences.address")}</option>
            <option value="station">{t("doorToDoor.preferences.station")}</option>
            <option value="saved_location">{t("doorToDoor.preferences.savedLocation")}</option>
          </select>
        </label>
        <div className="d2d-location-coords">
          <label className="field">{t("doorToDoor.preferences.lat")}<input className="prefs-control" value={lat} onChange={(event) => setLat(event.target.value)} /></label>
          <label className="field">{t("doorToDoor.preferences.lng")}<input className="prefs-control" value={lng} onChange={(event) => setLng(event.target.value)} /></label>
        </div>
        <div className="row-actions">
          <button className="btn-primary" type="submit" disabled={saving || !label.trim()}>{saving ? t("doorToDoor.preferences.saving") : t("doorToDoor.preferences.save")}</button>
        </div>
      </form>

      <section className="panel panel-soft prefs-secondary-block d2d-danger-zone">
        <div className="panel-header">
          <div>
            <h2>{t("doorToDoor.preferences.deleteTitle")}</h2>
            <p className="panel-note">{t("doorToDoor.preferences.deleteBody")}</p>
          </div>
          <span className="status-pill warning">{t("doorToDoor.preferences.destructive")}</span>
        </div>
        <div className="row-actions">
          <button className="btn-ghost" type="button" onClick={onDelete} disabled={!saved}>{t("doorToDoor.preferences.delete")}</button>
        </div>
      </section>
    </main>
  );
}
