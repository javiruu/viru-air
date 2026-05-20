import React from "react";
import type { DoorToDoorPreferences, DoorToDoorSortBy } from "@/modules/door-to-door/types";

export function DoorToDoorFilters({ preferences, onChange }: { preferences: DoorToDoorPreferences; onChange: (next: DoorToDoorPreferences) => void }) {
  function patch(next: Partial<DoorToDoorPreferences>) {
    onChange({ ...preferences, ...next });
  }
  return (
    <section className="panel panel-soft d2d-filters">
      <div className="panel-header">
        <h2 className="panel-title">Filtros de decisión</h2>
      </div>
      <div className="d2d-filter-grid">
        <label className="field">
          Ordenar por
          <select className="prefs-control" value={preferences.sort_by} onChange={(event) => patch({ sort_by: event.target.value as DoorToDoorSortBy })}>
            <option value="best_balance">Mejor equilibrio</option>
            <option value="cheapest">Más barato</option>
            <option value="lowest_risk">Menos riesgo</option>
            <option value="fastest">Más rápido</option>
            <option value="fewest_changes">Menos cambios</option>
          </select>
        </label>
        <label className="field">
          Margen mínimo antes del vuelo
          <input className="prefs-control" type="number" min={45} max={360} value={preferences.min_airport_buffer_minutes} onChange={(event) => patch({ min_airport_buffer_minutes: Number(event.target.value) })} />
        </label>
        <label className="field">
          Pasajeros
          <input className="prefs-control" type="number" min={1} max={9} value={preferences.passengers} onChange={(event) => patch({ passengers: Number(event.target.value) })} />
        </label>
        <label className="field">
          Equipaje
          <select className="prefs-control" value={preferences.luggage} onChange={(event) => patch({ luggage: event.target.value as DoorToDoorPreferences["luggage"] })}>
            <option value="backpack">Mochila</option>
            <option value="cabin">Cabina</option>
            <option value="checked">Maleta facturada</option>
          </select>
        </label>
      </div>
      <div className="d2d-toggle-row">
        <button type="button" className={`btn-ghost btn-compact ${preferences.public_transport_only ? "is-active" : ""}`} onClick={() => patch({ public_transport_only: !preferences.public_transport_only })}>Solo transporte público</button>
        <button type="button" className={`btn-ghost btn-compact ${preferences.allow_rideshare ? "is-active" : ""}`} onClick={() => patch({ allow_rideshare: !preferences.allow_rideshare })}>Permitir coche compartido</button>
        <button type="button" className={`btn-ghost btn-compact ${preferences.allow_shuttle ? "is-active" : ""}`} onClick={() => patch({ allow_shuttle: !preferences.allow_shuttle })}>Permitir shuttle</button>
      </div>
    </section>
  );
}
