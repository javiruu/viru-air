"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Skeleton, SkeletonPanel } from "@/modules/shared/Skeleton";
import { apiFetchWithStatus } from "@/modules/shared/api";
import { clearToken, hasToken } from "@/modules/shared/auth";
import { isDashboardDemoAccessEnabled } from "@/modules/shared/dashboard-demo-session";
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
        <SkeletonPanel className="landing-check air-loader-section" ariaLabel={t("public.landing.checkingSession")}>
          <Skeleton variant="pill" width={180} height={18} />
          <Skeleton variant="line" width="68%" />
          <Skeleton variant="line" width="52%" />
          <div className="loading-skeleton-row" aria-hidden="true">
            <Skeleton variant="card" className="loading-skeleton-card" />
            <Skeleton variant="card" className="loading-skeleton-card" />
          </div>
        </SkeletonPanel>
      </main>
    );
  }

  const authEntryHref = isDashboardDemoAccessEnabled() ? "/dashboard" : "/login";
  const registerHref = isDashboardDemoAccessEnabled() ? "/dashboard" : "/register";

  return (
    <>
      <main className="landing-shell-full" id="main-content">
        <section className="landing-fullband landing-fullband-hero landing-stage">
          <div className="landing-inner landing-inner-wide">
            <div className="landing-hero-v2 landing-conv-hero-grid">
              <div className="landing-hero-airway" aria-hidden="true">
                <span className="airway-point airway-point-origin">MAD</span>
                <span className="airway-arc" />
                <span className="airway-point airway-point-destination">FCO</span>
              </div>
              <div className="landing-hero-v2-copy landing-conv-copy">
                <p className="landing-eyebrow">{t("public.landing.heroEyebrow")}</p>
                <h1>{t("public.landing.heroTitle")}</h1>
                <p className="landing-claim">{t("public.landing.heroClaim")}</p>
                <p className="landing-body">{t("public.landing.heroBody")}</p>
                <ul className="landing-hero-points" aria-label={t("public.landing.heroPointsLabel")}>
                  <li>{t("public.landing.heroPointQuickSearch")}</li>
                  <li>{t("public.landing.heroPointWatchlists")}</li>
                  <li>{t("public.landing.heroPointPulse")}</li>
                  <li>{t("public.landing.heroPointAlerts")}</li>
                </ul>
                <div className="landing-cta-row">
                  <Link href={authEntryHref} className="btn-primary btn-layered">{t("public.landing.ctaEnter")}</Link>
                  <Link href={registerHref} className="btn-secondary">{t("public.landing.ctaCreate")}</Link>
                  <Link href="/policies" className="linkInline landing-hero-link">{t("public.landing.policies")}</Link>
                </div>
                <p className="landing-cta-note">{t("public.landing.ctaSupport")}</p>
                <div className="landing-conv-trust" aria-label={t("public.landing.heroTrustLabel")}>
                  <span>{t("public.landing.heroTrustFreshness")}</span>
                  <span>{t("public.landing.heroTrustNoNoise")}</span>
                  <span>{t("public.landing.heroTrustDirect")}</span>
                </div>
                <div className="landing-conv-metrics-row">
                  <article className="landing-metric-v2 landing-metric-v2--hero">
                    <strong>{t("public.landing.metricPricesStrong")}</strong>
                    <span>{t("public.landing.metricPricesLabel")}</span>
                  </article>
                  <article className="landing-metric-v2 landing-metric-v2--hero">
                    <strong>{t("public.landing.metricRefreshStrong")}</strong>
                    <span>{t("public.landing.metricRefreshLabel")}</span>
                  </article>
                  <article className="landing-metric-v2 landing-metric-v2--hero">
                    <strong>{t("public.landing.metricNoSmokeStrong")}</strong>
                    <span>{t("public.landing.metricNoSmokeLabel")}</span>
                  </article>
                </div>
              </div>

              <aside className="landing-signal-panel landing-conv-demo">
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
                <div className="landing-demo-stack">
                  <article className="landing-demo-card landing-demo-card--history">
                    <div className="landing-demo-card-header">
                      <strong>{t("public.landing.demoHistory")}</strong>
                      <span className="signal-chip signal-chip-muted">{t("public.landing.demoTrend")}</span>
                    </div>
                    <div className="landing-flight-strip" aria-hidden="true">
                      <span>MAD</span>
                      <span>{t("public.landing.demoWatchState")}</span>
                      <span>FCO</span>
                      <span>{t("public.landing.demoWindowValue")}</span>
                    </div>
                  </article>
                  <article className="landing-demo-card landing-demo-card--calendar">
                    <div className="landing-demo-card-header">
                      <strong>{t("public.landing.demoCalendar")}</strong>
                      <span className="signal-chip">{t("public.landing.demoPulse")}</span>
                    </div>
                    <div className="demo-calendar-grid demo-calendar-grid-v3">
                      {calendarDays.map((day, index) => (
                        <span key={`hero-demo-day-${index}`} className="demo-day">{day}</span>
                      ))}
                      {Array.from({ length: 14 }).map((_, index) => (
                        <span key={`hero-demo-date-${index}`} className={`demo-date demo-date-${(index % 3) + 1}`}>
                          {index + 10}
                        </span>
                      ))}
                    </div>
                  </article>
                </div>
                <div className="landing-signal-foot landing-signal-foot--elevated">
                  <span className="signal-chip">{t("public.landing.signalSource")}</span>
                  <span className="signal-chip signal-chip-muted">{t("public.landing.signalUpdated")}</span>
                  <span className="signal-chip signal-chip-success">{t("public.landing.demoDecisionReady")}</span>
                </div>
              </aside>
            </div>
          </div>
        </section>

        <section className="landing-fullband landing-fullband-proof landing-stage landing-stage-delay">
          <div className="landing-inner landing-inner-wide">
            <div className="landing-proof-band landing-proof-cred">
              <div className="landing-proof-copy landing-proof-copy-v2">
                <p className="landing-eyebrow">{t("public.landing.proofEyebrow")}</p>
                <h2>{t("public.landing.proofTitle")}</h2>
                <p>{t("public.landing.proofBody")}</p>
              </div>
              <div className="landing-metrics-v2 landing-proof-metrics">
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
              <div className="landing-proof-grid-v2">
                <article className="landing-cap-card landing-proof-card">
                  <h3>{t("public.landing.whyVisibility")}</h3>
                  <p>{t("public.landing.whyVisibilityBody")}</p>
                </article>
                <article className="landing-cap-card landing-proof-card">
                  <h3>{t("public.landing.whyCompare")}</h3>
                  <p>{t("public.landing.whyCompareBody")}</p>
                </article>
                <article className="landing-cap-card landing-proof-card">
                  <h3>{t("public.landing.whyAlerts")}</h3>
                  <p>{t("public.landing.whyAlertsBody")}</p>
                </article>
              </div>
            </div>
          </div>
        </section>

        <section className="landing-conv-decision landing-inner landing-inner-wide landing-stage landing-stage-delay-2">
          <div className="landing-panel-header landing-panel-header-v2 landing-decision-heading">
            <div>
              <p className="landing-eyebrow">{t("public.landing.capMainPill")}</p>
              <h2>{t("public.landing.capMainTitle")}</h2>
              <p>{t("public.landing.capMainSubtitle")}</p>
            </div>
          </div>
          <div className="landing-decision-grid">
            <article className="landing-capability-main landing-decision-story">
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
              <div className="landing-steps-grid-v2 landing-steps-grid-v3" role="list">
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
            </article>
            <div className="landing-capability-side landing-decision-support">
              <article className="landing-cap-card">
                <h3>{t("public.landing.gridWatch")}</h3>
                <p>{t("public.landing.gridWatchBody")}</p>
              </article>
              <article className="landing-cap-card">
                <h3>{t("public.landing.gridCompare")}</h3>
                <p>{t("public.landing.gridCompareBody")}</p>
              </article>
              <article className="landing-cap-card">
                <h3>{t("public.landing.gridSearch")}</h3>
                <p>{t("public.landing.gridSearchBody")}</p>
              </article>
              <article className="landing-cap-card landing-cap-card--cta">
                <h3>{t("public.landing.whyQuickSearch")}</h3>
                <p>{t("public.landing.whyQuickSearchBody")}</p>
                <Link href={registerHref} className="btn-secondary">{t("public.landing.ctaCreate")}</Link>
              </article>
            </div>
          </div>
        </section>

        <section className="landing-fullband landing-fullband-close landing-stage landing-stage-delay-3">
          <div className="landing-inner landing-inner-wide">
            <div className="landing-close-cta landing-close-cta-v2">
              <div className="landing-close-copy">
                <p className="landing-eyebrow">{t("public.landing.closeEyebrow")}</p>
                <h2>{t("public.landing.closeTitle")}</h2>
                <p>{t("public.landing.closeBody")}</p>
                <ul className="landing-close-proof" aria-label={t("public.landing.closeProofLabel")}>
                  <li>{t("public.landing.closeProofFreshness")}</li>
                  <li>{t("public.landing.closeProofContext")}</li>
                  <li>{t("public.landing.closeProofTiming")}</li>
                </ul>
              </div>
              <div className="landing-close-actions">
                <Link href={authEntryHref} className="btn-primary btn-layered">{t("public.landing.ctaEnter")}</Link>
                <Link href={registerHref} className="btn-ghost">{t("public.landing.ctaCreate")}</Link>
                <Link href="/policies" className="linkInline">{t("public.landing.policies")}</Link>
              </div>
            </div>
          </div>
        </section>
      </main>
    </>
  );
}
