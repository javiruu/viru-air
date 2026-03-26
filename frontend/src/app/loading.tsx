"use client";

import AirLoader from "@/modules/shared/AirLoader";

export default function Loading() {
  return (
    <main className="shell air-loader-screen" id="main-content">
      <section className="panel panel-soft air-loader-section">
        <AirLoader />
      </section>
    </main>
  );
}
