"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useNotificationCenter } from "@/components/components/notifications/notification-center";
import { useI18n } from "@/i18n";
import { deleteDoorToDoorLocation, fetchSavedDoorToDoorLocation, saveDoorToDoorLocation } from "@/modules/door-to-door/api";
import type { DoorToDoorLocationType, DoorToDoorSavedLocation } from "@/modules/door-to-door/types";

export default function PreferenciasPuertaAPuertaPage() {
  const router = useRouter();
  const { t } = useI18n();
  const { notify } = useNotificationCenter();
  const [saved, setSaved] = useState<DoorToDoorSavedLocation | null>(null);
  const [label, setLabel] = useState("Almería");
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
      notify({ tone: "success", title: "Ubicación guardada" });
    } catch {
      notify({ tone: "error", title: "No se pudo guardar" });
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
    notify({ tone: "success", title: "Ubicación eliminada" });
  }

  return (
    <main className="shell prefs-shell" id="main-content">
      <div className="page-header prefs-header">
        <button className="btn-ghost" type="button" onClick={() => router.push("/preferencias")}>{t("shared.actions.back")}</button>
        <div className="page-title">
          <h1>Puerta a puerta</h1>
          <p>Define tu origen habitual.</p>
        </div>
      </div>

      <section className="panel prefs-hero d2d-prefs-hero">
        <div>
          <p className="prefs-kicker">Origen habitual</p>
          <h2>{saved ? saved.label : "Aún no hay ubicación guardada"}</h2>
          <p className="prefs-hero-summary">Solo se usa con tu permiso.</p>
        </div>
        {saved ? <span className="status-pill success">Guardada</span> : <span className="status-pill warning">Pendiente de guardar</span>}
      </section>

      <form className="panel panel-soft prefs-form d2d-location-form prefs-priority-block" onSubmit={onSubmit}>
        {loading ? <p className="panel-note">Cargando ubicación…</p> : null}
        <label className="field">
          Etiqueta
          <input className="prefs-control" value={label} onChange={(event) => setLabel(event.target.value)} />
        </label>
        <label className="field">
          Tipo
          <select className="prefs-control" value={type} onChange={(event) => setType(event.target.value as DoorToDoorLocationType)}>
            <option value="city">Ciudad</option>
            <option value="address">Dirección</option>
            <option value="station">Estación</option>
            <option value="saved_location">Ubicación guardada</option>
          </select>
        </label>
        <div className="d2d-location-coords">
          <label className="field">Latitud<input className="prefs-control" value={lat} onChange={(event) => setLat(event.target.value)} /></label>
          <label className="field">Longitud<input className="prefs-control" value={lng} onChange={(event) => setLng(event.target.value)} /></label>
        </div>
        <div className="row-actions">
          <button className="btn-primary" type="submit" disabled={saving || !label.trim()}>{saving ? "Guardando…" : "Guardar"}</button>
        </div>
      </form>

      <section className="panel panel-soft prefs-secondary-block d2d-danger-zone">
        <div className="panel-header">
          <div>
            <h2>Borrar ubicación guardada</h2>
            <p className="panel-note">Acción secundaria para limpiar tu origen habitual.</p>
          </div>
          <span className="status-pill warning">Acción destructiva</span>
        </div>
        <div className="row-actions">
          <button className="btn-ghost" type="button" onClick={onDelete} disabled={!saved}>Borrar</button>
        </div>
      </section>
    </main>
  );
}
