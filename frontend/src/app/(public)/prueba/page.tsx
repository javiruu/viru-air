"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import ThemeToggle from "@/modules/shared/ThemeToggle";
import AirLoader from "@/modules/shared/AirLoader";
import { apiFetchWithStatus } from "@/modules/shared/api";
import { clearToken, hasToken } from "@/modules/shared/auth";
import { useI18n } from "@/i18n";

type LandingState = "checking" | "public";

export default function PruebaLandingPage() {
  const router = useRouter();
  const { t } = useI18n();
  const [state, setState] = useState<LandingState>("checking");

  useEffect(() => {
    let active = true;

    async function checkSession() {
      if (!hasToken()) {
        if (active) setState("public");
        return;
      }

      const meResult = await apiFetchWithStatus<{ id: string }>("/auth/me", undefined, { timeoutMs: 7000 });
      if (meResult.ok) {
        router.replace("/dashboard");
        return;
      }

      if (meResult.status === 401) {
        clearToken();
      }

      if (active) setState("public");
    }

    checkSession();
    return () => {
      active = false;
    };
  }, [router]);

  if (state === "checking") {
    return (
      <main className="shell landing-prueba-shell" id="main-content">
        <section className="panel panel-soft landing-check air-loader-section">
          <AirLoader />
          <p className="muted">{t("public.landing.checkingSession")}</p>
        </section>
      </main>
    );
  }

  return (
    <main className="landing-prueba-cinema" id="main-content">
      <video autoPlay loop muted playsInline className="absolute inset-0 w-full h-full object-cover z-0">
        <source src="https://res.cloudinary.com/dfonotyfb/video/upload/v1775585556/dds3_1_rqhg7x.mp4" type="video/mp4" />
      </video>
      <div className="landing-prueba-overlay" aria-hidden="true" />

      <header className="landing-prueba-cinema-header landing-stage">
        <div className="landing-brand">
          <span className="landing-dot" aria-hidden="true" />
          <div>
            <div className="landing-kicker">Viru Tracker</div>
            <p className="landing-tagline">{t("public.landing.brandTagline")}</p>
          </div>
        </div>
        <div className="landing-actions">
          <Link href="/policies" className="linkInline">{t("public.landing.policies")}</Link>
          <ThemeToggle />
        </div>
      </header>

      <section className="landing-prueba-cinema-body landing-stage landing-stage-delay">
        <p className="landing-prueba-kicker">flight intelligence</p>
        <h1>{t("public.landing.heroTitle")}</h1>
        <p className="landing-claim">{t("public.landing.heroClaim")}</p>
        <p className="landing-prueba-body">{t("public.landing.heroBody")}</p>
        <div className="landing-cta">
          <Link href="/login" className="btn-primary btn-layered">{t("public.landing.ctaEnter")}</Link>
        </div>
        <p className="landing-cta-note">
          {t("public.landing.ctaNoAccount")}{" "}
          <Link href="/register" className="linkInline">{t("public.landing.ctaCreate")}</Link>
        </p>
      </section>
    </main>
  );
}
