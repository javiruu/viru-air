import React from "react";
export function DoorToDoorLoadingState() {
  return (
    <section className="panel d2d-loading-state" role="status" aria-live="polite">
      <div className="d2d-loading-radar" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <div>
        <h2>Buscando combinaciones terrestres, márgenes y fuentes disponibles…</h2>
        <p className="panel-note">Revisamos coste, tiempo, cambios y riesgo alrededor del vuelo guardado.</p>
      </div>
    </section>
  );
}
