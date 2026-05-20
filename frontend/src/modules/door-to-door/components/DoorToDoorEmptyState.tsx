import React from "react";
export function DoorToDoorEmptyState({ hasWatch }: { hasWatch: boolean }) {
  return (
    <section className="panel panel-soft d2d-state-card d2d-empty-state">
      <span className="d2d-radar-dot" aria-hidden="true" />
      <h2>{hasWatch ? "Elige origen y destino final" : "Selecciona un vuelo guardado"}</h2>
      <p>
        {hasWatch
          ? "Elige desde dónde sales y dónde quieres terminar el viaje. Viru montará la ruta completa alrededor de tu vuelo."
          : "Puerta a puerta se activa cuando hay un vuelo de tu Watchlist para usarlo como tramo aéreo."}
      </p>
    </section>
  );
}
