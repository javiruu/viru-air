"use client";

import { BoneyardPanel } from "@/modules/shared/BoneyardLoad";

export default function Loading() {
  return (
    <main className="shell air-loader-screen" id="main-content">
      <BoneyardPanel name="app-root-load" className="air-loader-section" ariaLabel="Cargando contenido" />
    </main>
  );
}
