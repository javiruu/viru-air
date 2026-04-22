"use client";

import Link from "next/link";

import { useI18n } from "@/i18n";

import { buildSupportAboutMembers } from "./content";

export default function SoporteAboutUsClient() {
  const { t } = useI18n();
  const members = buildSupportAboutMembers(t);
  const principles = [
    t("support.aboutUs.principles.one"),
    t("support.aboutUs.principles.two"),
    t("support.aboutUs.principles.three"),
  ];

  return (
    <main className="shell support-about-page" id="main-content">
      <div className="page-header">
        <div className="page-title">
          <h1>{t("support.aboutUs.title")}</h1>
          <p>{t("support.aboutUs.subtitle")}</p>
        </div>
        <div className="row-actions">
          <Link className="btn-ghost" href="/soporte/ayuda">
            {t("account.menu.help")}
          </Link>
          <Link className="btn-primary" href="/dashboard">
            {t("shared.actions.back")}
          </Link>
        </div>
      </div>

      <section className="panel support-about-hero">
        <div className="support-about-hero-copy">
          <span className="support-about-eyebrow">{t("support.aboutUs.eyebrow")}</span>
          <div className="support-about-hero-header">
            <div>
              <h2>{t("support.aboutUs.heroTitle")}</h2>
              <p>{t("support.aboutUs.heroBody")}</p>
            </div>
            <span className="status-badge status-ok">{t("support.aboutUs.badge")}</span>
          </div>
        </div>

        <div className="support-about-principles">
          {principles.map((principle) => (
            <article key={principle} className="support-about-principle">
              <span className="support-about-principle-icon" aria-hidden="true">
                <i className="fa-solid fa-sparkles"></i>
              </span>
              <p>{principle}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="support-about-section">
        <div className="support-about-section-copy">
          <span className="support-about-kicker">{t("support.aboutUs.team.kicker")}</span>
          <h2>{t("support.aboutUs.team.title")}</h2>
          <p>{t("support.aboutUs.team.body")}</p>
          <div className="support-about-actions">
            <Link className="btn-primary" href="/soporte/contacto">
              {t("support.aboutUs.ctaPrimary")}
            </Link>
            <Link className="btn-ghost" href="/soporte/feedback">
              {t("support.aboutUs.ctaSecondary")}
            </Link>
          </div>
        </div>

        <div className="support-about-team-grid">
          {members.map((member) => (
            <article
              key={member.name}
              className={`support-about-card support-about-card-${member.accent} card`}
            >
              <div className="support-about-card-top">
                <span className="support-about-card-badge">{member.role}</span>
                <span className="support-about-card-avatar" aria-hidden="true">
                  {member.name
                    .split(" ")
                    .map((part) => part[0])
                    .join("")
                    .slice(0, 2)
                    .toUpperCase()}
                </span>
              </div>
              <div className="support-about-card-copy">
                <h3>{member.name}</h3>
                <p>{member.summary}</p>
              </div>
              <div className="support-about-focus-list">
                {member.focus.map((item) => (
                  <span key={item} className="support-about-focus-pill">
                    {item}
                  </span>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
