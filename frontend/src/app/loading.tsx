"use client";

import { SkeletonPanel } from "@/modules/shared/Skeleton";

export default function Loading() {
  return (
    <main className="shell air-loader-screen" id="main-content">
      <SkeletonPanel className="air-loader-section" ariaLabel="Cargando contenido" />
    </main>
  );
}
