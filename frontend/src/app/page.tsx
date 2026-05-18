"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import ThemeToggle from "@/modules/shared/ThemeToggle";
import AirLoader from "@/modules/shared/AirLoader";
import ViruFooterBlock from "@/modules/shared/ViruFooterBlock";
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
    <>
      <main className="landing-shell-full" id="main-content">
        <header className="landing-header landing-inner">
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

        <section className="landing-fullband landing-fullband-hero landing-stage">
          <div className="landing-inner landing-inner-wide">
            <div className="landing-hero-v2">
              <div className="landing-hero-airway" aria-hidden="true">
                <span className="airway-point airway-point-origin">MAD</span>
                <span className="airway-arc" />
                <span className="airway-point airway-point-destination">FCO</span>
              </div>
              <div className="landing-hero-v2-copy">
                <p className="landing-eyebrow">{t("public.landing.heroEyebrow")}</p>
                <h1>{t("public.landing.heroTitle")}</h1>
                <p className="landing-claim">{t("public.landing.heroClaim")}</p>
                <p className="landing-body">{t("public.landing.heroBody")}</p>
                <div className="landing-cta-row">
                  <Link href="/login" className="btn-primary btn-layered">{t("public.landing.ctaEnter")}</Link>
                  <Link href="/register" className="btn-secondary">{t("public.landing.ctaCreate")}</Link>
                </div>
                <p className="landing-cta-note">{t("public.landing.ctaSupport")}</p>
              </div>

              <aside className="landing-signal-panel">
                <div className="landing-panel-header landing-panel-header-v2">
                  <div>
                    <h2>{t("public.landing.signalTitle")}</h2>
                    <p>{t("public.landing.signalSubtitle")}</p>
                  </div>
                  <span className="landing-pill">{t("public.landing.signalPill")}</span>
                </div>
                <div className="landing-signal-top">
                  <div className="signal-route">
                    <span className="signal-label">{t("public.landing.signalRouteLabel")}</span>
                    <strong>{"MAD -> FCO"}</strong>
                    <span className="signal-meta">{t("public.landing.signalRouteMeta")}</span>
                  </div>
                  <div className="signal-chip signal-chip-success signal-chip-pulse">-18%</div>
                </div>
                <div className="signal-bars" aria-hidden="true">
                  <span style={{ height: "30%" }} />
                  <span style={{ height: "52%" }} />
                  <span style={{ height: "42%" }} />
                  <span style={{ height: "68%" }} />
                  <span style={{ height: "57%" }} />
                  <span style={{ height: "75%" }} />
                  <span style={{ height: "49%" }} />
                </div>
                <div className="landing-signal-grid">
                  <div className="signal-cell">
                    <span>{t("public.landing.signalTrendLabel")}</span>
                    <strong>{t("public.landing.signalTrendValue")}</strong>
                  </div>
                  <div className="signal-cell">
                    <span>{t("public.landing.signalWindowLabel")}</span>
                    <strong>{t("public.landing.signalWindowValue")}</strong>
                  </div>
                </div>
                <div className="landing-flight-strip" aria-hidden="true">
                  <span>MAD</span>
                  <span>TRACK ACTIVO</span>
                  <span>FCO</span>
                  <span>+24H</span>
                </div>
                <div className="landing-signal-foot">
                  <span className="signal-chip">{t("public.landing.signalSource")}</span>
                  <span className="signal-chip signal-chip-muted">{t("public.landing.signalUpdated")}</span>
                </div>
              </aside>
            </div>
          </div>
        </section>

        <section className="landing-fullband landing-fullband-proof landing-stage landing-stage-delay">
          <div className="landing-inner landing-inner-wide">
            <div className="landing-proof-band">
              <div className="landing-proof-copy">
                <p className="landing-eyebrow">{t("public.landing.proofEyebrow")}</p>
                <h2>{t("public.landing.proofTitle")}</h2>
                <p>{t("public.landing.proofBody")}</p>
              </div>
              <div className="landing-metrics-v2">
                <article className="landing-metric-v2">
                  <strong>{t("public.landing.metricPricesStrong")}</strong>
                  <span>{t("public.landing.metricPricesLabel")}</span>
                </article>
                <article className="landing-metric-v2">
                  <strong>{t("public.landing.metricRefreshStrong")}</strong>
                  <span>{t("public.landing.metricRefreshLabel")}</span>
                </article>
                <article className="landing-metric-v2">
                  <strong>{t("public.landing.metricLocalAiStrong")}</strong>
                  <span>{t("public.landing.metricLocalAiLabel")}</span>
                </article>
                <article className="landing-metric-v2">
                  <strong>{t("public.landing.metricNoSmokeStrong")}</strong>
                  <span>{t("public.landing.metricNoSmokeLabel")}</span>
                </article>
              </div>
            </div>
          </div>
        </section>

        <section className="landing-capabilities landing-inner landing-inner-wide landing-stage landing-stage-delay-2">
          <article className="landing-capability-main">
            <div className="landing-panel-header landing-panel-header-v2">
              <div>
                <h2>{t("public.landing.capMainTitle")}</h2>
                <p>{t("public.landing.capMainSubtitle")}</p>
              </div>
              <span className="landing-pill">{t("public.landing.capMainPill")}</span>
            </div>
            <div className="landing-cap-main-grid">
              <div className="pulse-row">
                <div>
                  <div className="pulse-label">{t("public.landing.pulseTrendLabel")}</div>
                  <div className="pulse-value">{"MAD -> FCO"}</div>
                </div>
                <div className="pulse-chip">-18%</div>
              </div>
              <div className="pulse-row">
                <div>
                  <div className="pulse-label">{t("public.landing.pulseAlertLabel")}</div>
                  <div className="pulse-value">{"BRU -> LIS"}</div>
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
          </article>
          <div className="landing-capability-side">
            <article className="landing-cap-card">
              <h3>{t("public.landing.whyVisibility")}</h3>
              <p>{t("public.landing.whyVisibilityBody")}</p>
            </article>
            <article className="landing-cap-card">
              <h3>{t("public.landing.whyAlerts")}</h3>
              <p>{t("public.landing.whyAlertsBody")}</p>
            </article>
            <article className="landing-cap-card">
              <h3>{t("public.landing.whyCompare")}</h3>
              <p>{t("public.landing.whyCompareBody")}</p>
            </article>
            <article className="landing-cap-card">
              <h3>{t("public.landing.whyQuickSearch")}</h3>
              <p>{t("public.landing.whyQuickSearchBody")}</p>
            </article>
          </div>
        </section>

        <section className="landing-flow-v2 landing-inner landing-inner-wide landing-stage landing-stage-delay-3">
          <div className="landing-section-title">
            <h2>{t("public.landing.stepsTitle")}</h2>
            <p>{t("public.landing.stepsSubtitle")}</p>
          </div>
          <div className="landing-steps-grid-v2" role="list">
            <article className="landing-step-v2">
              <span className="step-index">01</span>
              <h3>{t("public.landing.stepRoute")}</h3>
              <p>{t("public.landing.stepRouteBody")}</p>
            </article>
            <article className="landing-step-v2">
              <span className="step-index">02</span>
              <h3>{t("public.landing.stepTrends")}</h3>
              <p>{t("public.landing.stepTrendsBody")}</p>
            </article>
            <article className="landing-step-v2">
              <span className="step-index">03</span>
              <h3>{t("public.landing.stepAlerts")}</h3>
              <p>{t("public.landing.stepAlertsBody")}</p>
            </article>
            <article className="landing-step-v2">
              <span className="step-index">04</span>
              <h3>{t("public.landing.stepBuy")}</h3>
              <p>{t("public.landing.stepBuyBody")}</p>
            </article>
          </div>
        </section>

        <section className="landing-fullband landing-fullband-close landing-stage landing-stage-delay-3">
          <div className="landing-inner landing-inner-wide">
            <div className="landing-close-cta">
              <div>
                <p className="landing-eyebrow">{t("public.landing.closeEyebrow")}</p>
                <h2>{t("public.landing.closeTitle")}</h2>
                <p>{t("public.landing.closeBody")}</p>
              </div>
              <div className="landing-close-actions">
                <Link href="/login" className="btn-primary btn-layered">{t("public.landing.ctaEnter")}</Link>
                <Link href="/register" className="btn-secondary">{t("public.landing.ctaCreate")}</Link>
                <Link href="/policies" className="linkInline">{t("public.landing.policies")}</Link>
              </div>
            </div>
          </div>
        </section>

        <section className="landing-calendar-preview landing-inner landing-inner-wide landing-stage landing-stage-delay-3">
          <div className="landing-panel-header landing-panel-header-v2">
            <div>
              <h2>{t("public.landing.demoTitle")}</h2>
              <p>{t("public.landing.demoSubtitle")}</p>
            </div>
            <span className="landing-pill">{t("public.landing.demoPulse")}</span>
          </div>
          <div className="demo-calendar-grid demo-calendar-grid-v2">
            {calendarDays.map((day, index) => (
              <span key={`demo-day-${index}`} className="demo-day">{day}</span>
            ))}
            {Array.from({ length: 14 }).map((_, index) => (
              <span key={index} className={`demo-date demo-date-${(index % 3) + 1}`}>
                {index + 10}
              </span>
            ))}
          </div>
          <div className="demo-meta-strip">
            <span className="signal-chip">{t("public.landing.demoTrend")}</span>
            <span className="signal-chip signal-chip-muted">{t("public.landing.demoUpdated")}</span>
          </div>
        </section>
      </main>
      <ViruFooterBlock variant="landing" />
    </>
  );
}
