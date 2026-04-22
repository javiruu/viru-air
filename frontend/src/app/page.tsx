"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import ThemeToggle from "@/modules/shared/ThemeToggle";
import AirLoader from "@/modules/shared/AirLoader";
import { apiFetchWithStatus } from "@/modules/shared/api";
import { clearToken, hasToken } from "@/modules/shared/auth";
import { useI18n } from "@/i18n";

type LandingState = "checking" | "public";

export default function HomePage() {
  const router = useRouter();
  const { t, locale } = useI18n();
  const [state, setState] = useState<LandingState>("checking");

  useEffect(() => {
    let active = true;
    async function checkSession() {
      if (!hasToken()) {
        if (active) setState("public");
        return;
      }
      const meResult = await apiFetchWithStatus<{ id: string }>("/auth/me");
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

  const calendarDays = useMemo(
    () => (locale === "en" ? ["M", "T", "W", "T", "F", "S", "S"] : ["L", "M", "X", "J", "V", "S", "D"]),
    [locale],
  );

  if (state === "checking") {
    return (
      <main className="shell landing-shell" id="main-content">
        <section className="panel panel-soft landing-check air-loader-section">
          <AirLoader />
          <p className="muted">{t("public.landing.checkingSession")}</p>
        </section>
      </main>
    );
  }

  return (
    <main className="shell landing-shell" id="main-content">
      <header className="landing-header">
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

      <section className="landing-hero landing-stage">
        <div className="landing-hero-copy">
          <h1>{t("public.landing.heroTitle")}</h1>
          <p className="landing-claim">{t("public.landing.heroClaim")}</p>
          <p>{t("public.landing.heroBody")}</p>
          <div className="cta-row landing-cta">
            <Link href="/login" className="btn-primary btn-layered">{t("public.landing.ctaEnter")}</Link>
          </div>
          <p className="landing-cta-note">
            {t("public.landing.ctaNoAccount")}{" "}
            <Link href="/register" className="linkInline">{t("public.landing.ctaCreate")}</Link>
          </p>
        </div>

        <div className="landing-hero-panel">
          <div className="landing-panel-header">
            <div>
              <h2>{t("public.landing.demoTitle")}</h2>
              <p>{t("public.landing.demoSubtitle")}</p>
            </div>
            <span className="landing-pill">{t("public.landing.demoPulse")}</span>
          </div>
          <div className="landing-demo">
            <div className="demo-chart">
              <div className="demo-chart-header">
                <span>{t("public.landing.demoHistory")}</span>
                <strong>EUR 68 → 54</strong>
              </div>
              <div className="demo-chart-bars">
                <span style={{ height: "34%" }} />
                <span style={{ height: "52%" }} />
                <span style={{ height: "46%" }} />
                <span style={{ height: "64%" }} />
                <span style={{ height: "58%" }} />
                <span style={{ height: "72%" }} />
                <span style={{ height: "48%" }} />
                <span style={{ height: "62%" }} />
                <span style={{ height: "40%" }} />
                <span style={{ height: "68%" }} />
              </div>
              <div className="demo-trend">
                <i className="fa-solid fa-arrow-trend-down" aria-hidden="true" />
                <span>{t("public.landing.demoTrend")}</span>
              </div>
            </div>
            <div className="demo-calendar">
              <div className="demo-calendar-header">
                <span>{t("public.landing.demoCalendar")}</span>
                <i className="fa-solid fa-calendar-check" aria-hidden="true" />
              </div>
              <div className="demo-calendar-grid">
                {calendarDays.map((day) => (
                  <span key={day} className="demo-day">{day}</span>
                ))}
                {Array.from({ length: 14 }).map((_, index) => (
                  <span key={index} className={`demo-date demo-date-${(index % 3) + 1}`}>
                    {index + 10}
                  </span>
                ))}
              </div>
            </div>
          </div>
          <div className="demo-footnote">
            <span className="demo-chip">Ryanair</span>
            <span className="demo-chip demo-chip-muted">{t("public.landing.demoUpdated")}</span>
          </div>
        </div>
      </section>

      <section className="landing-metrics landing-stage landing-stage-delay">
        <div className="landing-metric">
          <strong>{t("public.landing.metricPricesStrong")}</strong>
          <span>{t("public.landing.metricPricesLabel")}</span>
        </div>
        <div className="landing-metric">
          <strong>{t("public.landing.metricRefreshStrong")}</strong>
          <span>{t("public.landing.metricRefreshLabel")}</span>
        </div>
        <div className="landing-metric">
          <strong>{t("public.landing.metricLocalAiStrong")}</strong>
          <span>{t("public.landing.metricLocalAiLabel")}</span>
        </div>
        <div className="landing-metric">
          <strong>{t("public.landing.metricNoSmokeStrong")}</strong>
          <span>{t("public.landing.metricNoSmokeLabel")}</span>
        </div>
      </section>

      <section className="landing-why landing-stage landing-stage-delay-2">
        <div className="landing-section-title">
          <h2>{t("public.landing.whyTitle")}</h2>
          <p>{t("public.landing.whySubtitle")}</p>
        </div>
        <div className="landing-why-grid">
          <article className="landing-why-card">
            <i className="fa-solid fa-eye" aria-hidden="true" />
            <div>
              <h3>{t("public.landing.whyVisibility")}</h3>
              <p>{t("public.landing.whyVisibilityBody")}</p>
            </div>
          </article>
          <article className="landing-why-card">
            <i className="fa-solid fa-bell" aria-hidden="true" />
            <div>
              <h3>{t("public.landing.whyAlerts")}</h3>
              <p>{t("public.landing.whyAlertsBody")}</p>
            </div>
          </article>
          <article className="landing-why-card">
            <i className="fa-solid fa-chart-line" aria-hidden="true" />
            <div>
              <h3>{t("public.landing.whyCompare")}</h3>
              <p>{t("public.landing.whyCompareBody")}</p>
            </div>
          </article>
          <article className="landing-why-card">
            <i className="fa-solid fa-magnifying-glass" aria-hidden="true" />
            <div>
              <h3>{t("public.landing.whyQuickSearch")}</h3>
              <p>{t("public.landing.whyQuickSearchBody")}</p>
            </div>
          </article>
        </div>
      </section>

      <section className="landing-pulse-section landing-stage landing-stage-delay-3">
        <div className="landing-panel-header">
          <div>
            <h2>{t("public.landing.pulseTitle")}</h2>
            <p>{t("public.landing.pulseSubtitle")}</p>
          </div>
          <span className="landing-pill">{t("public.landing.pulseEdition")}</span>
        </div>
        <div className="landing-pulse">
          <div className="pulse-row">
            <div>
              <div className="pulse-label">{t("public.landing.pulseTrendLabel")}</div>
              <div className="pulse-value">MAD → FCO</div>
            </div>
            <div className="pulse-chip">-18%</div>
          </div>
          <div className="pulse-row">
            <div>
              <div className="pulse-label">{t("public.landing.pulseAlertLabel")}</div>
              <div className="pulse-value">BRU → LIS</div>
            </div>
            <div className="pulse-chip pulse-chip-muted">{t("public.landing.pulseAlertState")}</div>
          </div>
          <div className="pulse-row">
            <div>
              <div className="pulse-label">{t("public.landing.pulseLastLabel")}</div>
              <div className="pulse-value">{t("public.landing.pulseLastValue")}</div>
            </div>
            <div className="pulse-chip">{t("public.landing.pulseOk")}</div>
          </div>
        </div>
        <div className="landing-pulse-grid">
          <div className="pulse-card">
            <h3>{t("public.landing.pulseCardWatchlist")}</h3>
            <p>{t("public.landing.pulseCardWatchlistBody")}</p>
          </div>
          <div className="pulse-card">
            <h3>{t("public.landing.pulseCardAlerts")}</h3>
            <p>{t("public.landing.pulseCardAlertsBody")}</p>
          </div>
        </div>
      </section>

      <section className="landing-steps landing-stage landing-stage-delay-3">
        <div className="landing-steps-header">
          <h2>{t("public.landing.stepsTitle")}</h2>
          <p>{t("public.landing.stepsSubtitle")}</p>
        </div>
        <div className="landing-steps-grid">
          <div className="landing-step">
            <i className="fa-solid fa-route" aria-hidden="true" />
            <h3>{t("public.landing.stepRoute")}</h3>
            <p>{t("public.landing.stepRouteBody")}</p>
          </div>
          <div className="landing-step">
            <i className="fa-solid fa-wave-square" aria-hidden="true" />
            <h3>{t("public.landing.stepTrends")}</h3>
            <p>{t("public.landing.stepTrendsBody")}</p>
          </div>
          <div className="landing-step">
            <i className="fa-solid fa-bell" aria-hidden="true" />
            <h3>{t("public.landing.stepAlerts")}</h3>
            <p>{t("public.landing.stepAlertsBody")}</p>
          </div>
          <div className="landing-step">
            <i className="fa-solid fa-plane-departure" aria-hidden="true" />
            <h3>{t("public.landing.stepBuy")}</h3>
            <p>{t("public.landing.stepBuyBody")}</p>
          </div>
        </div>
      </section>

      <section className="landing-grid landing-stage landing-stage-delay-3">
        <article className="landing-card">
          <i className="fa-solid fa-shield" aria-hidden="true" />
          <h3>{t("public.landing.gridWatch")}</h3>
          <p>{t("public.landing.gridWatchBody")}</p>
        </article>
        <article className="landing-card">
          <i className="fa-solid fa-chart-line" aria-hidden="true" />
          <h3>{t("public.landing.gridCompare")}</h3>
          <p>{t("public.landing.gridCompareBody")}</p>
        </article>
        <article className="landing-card">
          <i className="fa-solid fa-magnifying-glass" aria-hidden="true" />
          <h3>{t("public.landing.gridSearch")}</h3>
          <p>{t("public.landing.gridSearchBody")}</p>
        </article>
      </section>
    </main>
  );
}
