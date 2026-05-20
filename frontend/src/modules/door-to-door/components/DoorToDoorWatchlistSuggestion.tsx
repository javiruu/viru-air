import React from "react";
import Link from "next/link";

import type { Watch } from "@/modules/watchlist/types";

export function DoorToDoorWatchlistSuggestion({ watch }: { watch: Watch }) {
  return (
    <section className="panel panel-soft d2d-watch-suggestion" aria-label="Sugerencia Puerta a puerta">
      <div className="d2d-watch-suggestion-copy">
        <span className="d2d-mini-kicker">Puerta a puerta</span>
        <strong>{watch.origin_iata} → {watch.destination_iata}, pero desde tu puerta real</strong>
        <p>Calcula coste, tiempo y riesgo de llegar al aeropuerto y continuar al aterrizar.</p>
      </div>
      <Link className="btn-primary btn-compact" href={`/puerta-a-puerta?watchId=${encodeURIComponent(watch.id)}`}>
        Calcular puerta a puerta
      </Link>
    </section>
  );
}
