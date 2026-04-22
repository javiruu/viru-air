"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { useMemo } from "react";
import { usePathname } from "next/navigation";

import { hasToken } from "@/modules/shared/auth";
import { useI18n } from "@/i18n";

type FooterLink = {
  label: string;
  href: string;
  icon?: string;
  external?: boolean;
};

type FooterGroup = {
  title: string;
  links: FooterLink[];
};

function buildHrefWithOrigin(href: string) {
  if (typeof window === "undefined") return href;
  return new URL(href, window.location.origin).toString();
}

export default function ViruFooterBlock() {
  const { t } = useI18n();
  const pathname = usePathname() ?? "/";
  const shouldReduceMotion = useReducedMotion();
  const loggedIn = hasToken();

  const isPrivateContext =
    loggedIn ||
    pathname.startsWith("/dashboard") ||
    pathname.startsWith("/watchlist") ||
    pathname.startsWith("/quick-search") ||
    pathname.startsWith("/alerts") ||
    pathname.startsWith("/recomendaciones") ||
    pathname.startsWith("/suggestions") ||
    pathname.startsWith("/preferencias") ||
    pathname.startsWith("/preferences") ||
    pathname.startsWith("/history") ||
    pathname.startsWith("/cuenta") ||
    pathname.startsWith("/soporte") ||
    pathname.startsWith("/admin");

  const isAdminContext = pathname.startsWith("/admin");

  const footerGroups = useMemo<FooterGroup[]>(() => {
    const publicGroups: FooterGroup[] = [
      {
        title: t("shared.footer.groups.explore"),
        links: [
          { label: t("shared.footer.links.home"), href: "/", icon: "fa-house" },
          { label: t("shared.footer.links.help"), href: "/ayuda", icon: "fa-circle-question" },
          { label: t("shared.footer.links.policies"), href: "/policies", icon: "fa-shield-heart" },
        ],
      },
      {
        title: t("shared.footer.groups.access"),
        links: [
          { label: t("shared.actions.enter"), href: "/login", icon: "fa-right-to-bracket" },
          { label: t("shared.footer.links.register"), href: "/register", icon: "fa-user-plus" },
        ],
      },
      {
        title: t("shared.footer.groups.contact"),
        links: [
          { label: t("shared.footer.links.supportEmail"), href: "mailto:soporte@viru.app", icon: "fa-envelope", external: true },
          { label: t("shared.footer.links.privacyEmail"), href: "mailto:privacidad@viru.app", icon: "fa-user-shield", external: true },
          { label: t("shared.footer.links.pressEmail"), href: "mailto:press@viru.app", icon: "fa-newspaper", external: true },
        ],
      },
    ];

    const privateGroups: FooterGroup[] = [
      {
        title: t("shared.footer.groups.workspace"),
        links: [
          { label: t("shared.footer.links.dashboard"), href: "/dashboard", icon: "fa-table-columns" },
          { label: t("shared.footer.links.watchlist"), href: "/watchlist", icon: "fa-binoculars" },
          { label: t("shared.footer.links.quickSearch"), href: "/quick-search", icon: "fa-magnifying-glass-chart" },
          { label: t("shared.footer.links.alerts"), href: "/alerts", icon: "fa-bell" },
          { label: t("shared.footer.links.recommendations"), href: "/recomendaciones", icon: "fa-sparkles" },
          { label: t("shared.footer.links.suggestions"), href: "/suggestions", icon: "fa-lightbulb" },
        ],
      },
      {
        title: t("shared.footer.groups.account"),
        links: [
          { label: t("shared.footer.links.profile"), href: "/cuenta/perfil", icon: "fa-id-card-clip" },
          { label: t("shared.footer.links.security"), href: "/cuenta/seguridad", icon: "fa-shield-halved" },
          { label: t("shared.footer.links.preferences"), href: "/preferencias", icon: "fa-sliders" },
          { label: t("shared.footer.links.appearance"), href: "/preferencias/apariencia", icon: "fa-palette" },
          { label: t("shared.footer.links.searchPrefs"), href: "/preferencias/busqueda", icon: "fa-compass-drafting" },
          { label: t("shared.footer.links.region"), href: "/preferencias/region", icon: "fa-globe" },
        ],
      },
      {
        title: t("shared.footer.groups.support"),
        links: [
          { label: t("shared.footer.links.supportHelp"), href: "/soporte/ayuda", icon: "fa-headset" },
          { label: t("shared.footer.links.contact"), href: "/soporte/contacto", icon: "fa-paper-plane" },
          { label: t("shared.footer.links.feedback"), href: "/soporte/feedback", icon: "fa-bug" },
          { label: t("shared.footer.links.aboutUs"), href: "/soporte/about-us", icon: "fa-people-group" },
          { label: t("shared.footer.links.policies"), href: "/policies", icon: "fa-scale-balanced" },
        ],
      },
    ];

    if (isAdminContext) {
      privateGroups.push({
        title: t("shared.footer.groups.admin"),
        links: [
          { label: t("shared.footer.links.admin"), href: "/admin", icon: "fa-crown" },
          { label: t("shared.footer.links.productHealth"), href: "/admin/product-health", icon: "fa-heart-pulse" },
        ],
      });
    }

    return isPrivateContext ? privateGroups : publicGroups;
  }, [isAdminContext, isPrivateContext, t]);

  const quickLinks = useMemo<FooterLink[]>(() => {
    if (isPrivateContext) {
      return [
        { label: t("shared.footer.links.help"), href: "/soporte/ayuda" },
        { label: t("shared.footer.links.contact"), href: "/soporte/contacto" },
        { label: t("shared.footer.links.feedback"), href: "/soporte/feedback?type=bug" },
      ];
    }

    return [
      { label: t("shared.actions.enter"), href: "/login" },
      { label: t("shared.footer.links.register"), href: "/register" },
      { label: t("shared.footer.links.policies"), href: "/policies" },
    ];
  }, [isPrivateContext, t]);

  function onScrollToTop() {
    window.scrollTo({ top: 0, behavior: shouldReduceMotion ? "auto" : "smooth" });
  }

  function onCopyLink() {
    const shareTarget = isPrivateContext ? "/dashboard" : "/";
    const absolute = buildHrefWithOrigin(shareTarget);
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      void navigator.clipboard.writeText(absolute);
    }
  }

  return (
    <motion.footer
      className="viru-footer-block"
      initial={shouldReduceMotion ? undefined : { opacity: 0, y: 18 }}
      whileInView={shouldReduceMotion ? undefined : { opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="shell viru-footer-shell">
        <div className="viru-footer-surface">
          <div className="viru-footer-glow viru-footer-glow-primary" aria-hidden="true" />
          <div className="viru-footer-glow viru-footer-glow-secondary" aria-hidden="true" />

          <motion.div
            className="viru-footer-top"
            initial={shouldReduceMotion ? undefined : { opacity: 0, y: 12 }}
            whileInView={shouldReduceMotion ? undefined : { opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 0.45, delay: 0.05 }}
          >
            <div className="viru-footer-brand">
              <span className="viru-footer-brand-mark" aria-hidden="true">
                <span className="landing-dot" />
              </span>
              <div className="viru-footer-brand-copy">
                <span className="viru-footer-kicker">{t("shared.footer.kicker")}</span>
                <h2>Viru Tracker</h2>
                <p>
                  {isPrivateContext ? t("shared.footer.privateBody") : t("shared.footer.publicBody")}
                </p>
              </div>
            </div>

            <div className="viru-footer-utility">
              <div className="viru-footer-status">
                <span className="viru-footer-status-label">{t("shared.footer.statusLabel")}</span>
                <strong>{isPrivateContext ? t("shared.footer.statusPrivate") : t("shared.footer.statusPublic")}</strong>
              </div>
              <div className="viru-footer-actions">
                {quickLinks.map((item) => (
                  <Link key={item.href} href={item.href} className="viru-footer-chip">
                    {item.label}
                  </Link>
                ))}
                <button type="button" className="viru-footer-chip viru-footer-chip-ghost" onClick={onCopyLink}>
                  {t("shared.footer.copyLink")}
                </button>
                <button type="button" className="viru-footer-scroll" onClick={onScrollToTop}>
                  <span>{t("shared.footer.scrollTop")}</span>
                  <i className="fa-solid fa-arrow-up" aria-hidden="true" />
                </button>
              </div>
            </div>
          </motion.div>

          <div className="viru-footer-grid">
            {footerGroups.map((group, index) => (
              <motion.section
                key={group.title}
                className="viru-footer-column"
                initial={shouldReduceMotion ? undefined : { opacity: 0, y: 14 }}
                whileInView={shouldReduceMotion ? undefined : { opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.25 }}
                transition={{ duration: 0.42, delay: 0.08 + index * 0.06 }}
              >
                <div className="viru-footer-column-head">
                  <h3>{group.title}</h3>
                </div>
                <ul>
                  {group.links.map((link) => (
                    <li key={`${group.title}-${link.href}`}>
                      {link.external ? (
                        <a href={link.href} className="viru-footer-link">
                          {link.icon ? <i className={`fa-solid ${link.icon}`} aria-hidden="true" /> : null}
                          <span>{link.label}</span>
                        </a>
                      ) : (
                        <Link href={link.href} className="viru-footer-link">
                          {link.icon ? <i className={`fa-solid ${link.icon}`} aria-hidden="true" /> : null}
                          <span>{link.label}</span>
                        </Link>
                      )}
                    </li>
                  ))}
                </ul>
              </motion.section>
            ))}
          </div>

          <div className="viru-footer-bottom">
            <p>
              {t("shared.footer.copyright", { year: new Date().getFullYear() })}
            </p>
            <p>{t("shared.footer.note")}</p>
          </div>
        </div>
      </div>
    </motion.footer>
  );
}
