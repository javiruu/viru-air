"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";


export default function HistoryPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/watchlist");
  }, [router]);

  return (
    <main className="shell" id="main-content">
      <section className="panel panel-soft stack section-gap" aria-live="polite">
        <h1>Redirecting to the unified panel</h1>
        <p>History is now part of Flight Watchlist.</p>
      </section>
    </main>
  );
}
