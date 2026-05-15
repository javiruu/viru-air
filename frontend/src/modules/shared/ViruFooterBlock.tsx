"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
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

/* ── Inline SVG icons (no FontAwesome CDN dependency) ── */

const ICONS: Record<string, string> = {
  "house": "<path d=\"M2 7.5L8 2l6 5.5V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V7.5z\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M6 14v-4h4v4\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/>",
  "circle-question": "<circle cx=\"8\" cy=\"8\" r=\"6\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/><path d=\"M6 6.5a2 2 0 1 1 2.5 1.94V9.5\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><circle cx=\"8\" cy=\"11.5\" r=\".75\" fill=\"currentColor\"/>",
  "shield-heart": "<path d=\"M8 1.5l5 2v3.5a5.5 5.5 0 0 1-5 5.5 5.5 5.5 0 0 1-5-5.5V3.5l5-2z\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linejoin=\"round\"/><path d=\"M5.5 8.5L8 11l2.5-2.5a1.4 1.4 0 0 0-2-2L8 7l-.5-.5a1.4 1.4 0 0 0-2 2z\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/>",
  "right-to-bracket": "<path d=\"M7 2.5H4a1.5 1.5 0 0 0-1.5 1.5v8A1.5 1.5 0 0 0 4 13.5h3\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M10 11l3-3-3-3\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M13 8H6\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\"/>",
  "user-plus": "<path d=\"M10 12a4 4 0 0 0-8 0\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><circle cx=\"6\" cy=\"5\" r=\"2.5\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/><path d=\"M13 4v4M11 6h4\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\"/>",
  "envelope": "<rect x=\"1.5\" y=\"3\" width=\"13\" height=\"10\" rx=\"1.5\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/><path d=\"M2 4l6 4.5L14 4\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/>",
  "user-shield": "<path d=\"M10 12.5a4 4 0 0 0-8 0\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><circle cx=\"6\" cy=\"5\" r=\"2.5\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/><path d=\"M11 8l3 1.5v3A4 4 0 0 1 11 16a4 4 0 0 1-3-3.5v-3L11 8z\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linejoin=\"round\"/>",
  "newspaper": "<path d=\"M2 3h10a1 1 0 0 1 1 1v9a1.5 1.5 0 0 1-1.5 1.5H3A1.5 1.5 0 0 1 1.5 13V4a1 1 0 0 1 1-1z\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/><path d=\"M5 6h4M5 8.5h4M5 11h2\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><path d=\"M13 13a1.5 1.5 0 0 0 1.5-1.5V5l-1.5-1\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/>",
  "table-columns": "<rect x=\"1.5\" y=\"2.5\" width=\"13\" height=\"11\" rx=\"1.5\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/><path d=\"M7.5 2.5v11M1.5 7.5h13\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/>",
  "binoculars": "<path d=\"M3 10.5L5 4h2l1 6\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M13 10.5L11 4H9l-1 6\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><circle cx=\"4\" cy=\"11.5\" r=\"2\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/><circle cx=\"12\" cy=\"11.5\" r=\"2\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/>",
  "magnifying-glass-chart": "<circle cx=\"7\" cy=\"7\" r=\"5\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/><path d=\"M11 11l3 3\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><path d=\"M5 7.5l1-2 1 1.5 1-3 1 2\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/>",
  "bell": "<path d=\"M8 1.5A3.5 3.5 0 0 0 4.5 5v2.5l-1 3h9l-1-3V5A3.5 3.5 0 0 0 8 1.5z\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M5.5 11a2.5 2.5 0 0 0 5 0\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\"/>",
  "sparkles": "<path d=\"M8 2l1 2.5L11.5 6 9 7l-1 2.5L7 7 4.5 6 7 4.5 8 2z\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.3\" stroke-linejoin=\"round\"/><path d=\"M12 9l.5 1L13.5 11l-1 .5-.5 1-.5-1-1-.5 1-.5.5-1z\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.3\" stroke-linejoin=\"round\"/><path d=\"M3 10l.5 1 1 .5-1 .5-.5 1-.5-1-1-.5 1-.5.5-1z\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.3\" stroke-linejoin=\"round\"/>",
  "id-card-clip": "<rect x=\"2\" y=\"2.5\" width=\"12\" height=\"11\" rx=\"1.5\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/><path d=\"M9 6a1 1 0 1 0-2 0v1h2V6z\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/><path d=\"M5 10.5A2 2 0 0 1 7 9h2a2 2 0 0 1 2 2v.5H5v-.5z\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/>",
  "shield-halved": "<path d=\"M8 1.5l5 2v3.5a5.5 5.5 0 0 1-5 5.5 5.5 5.5 0 0 1-5-5.5V3.5l5-2z\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linejoin=\"round\"/><path d=\"M8 1.5V12a5.5 5.5 0 0 0 5-5.5V3.5l-5-2z\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linejoin=\"round\" opacity=\".4\"/>",
  "sliders": "<path d=\"M2 4h4M10 4h4\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><circle cx=\"6\" cy=\"4\" r=\"1.5\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/><path d=\"M2 8h3M9 8h5\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><circle cx=\"7\" cy=\"8\" r=\"1.5\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/><path d=\"M2 12h6M12 12h2\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><circle cx=\"10\" cy=\"12\" r=\"1.5\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/>",
  "palette": "<circle cx=\"8\" cy=\"8\" r=\"6\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/><circle cx=\"5.5\" cy=\"6.5\" r=\".8\" fill=\"currentColor\"/><circle cx=\"10.5\" cy=\"6.5\" r=\".8\" fill=\"currentColor\"/><circle cx=\"8\" cy=\"11\" r=\".8\" fill=\"currentColor\"/><path d=\"M8 2a6 6 0 0 1 6 6c0 1-.8 1.5-1.5 1.5H11a1.5 1.5 0 0 0 0 3v.5A6 6 0 1 1 8 2z\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/>",
  "compass-drafting": "<circle cx=\"8\" cy=\"8\" r=\"6\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/><path d=\"M8 2v12M4 5l8 6M12 5l-8 6\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.3\" stroke-linecap=\"round\"/>",
  "globe": "<circle cx=\"8\" cy=\"8\" r=\"6\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/><path d=\"M2 8h12M4 5a8 8 0 0 0 8 0M4 11a8 8 0 0 1 8 0\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><path d=\"M8 2c1.5 2 2 4 2 6s-.5 4-2 6c-1.5-2-2-4-2-6s.5-4 2-6z\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/>",
  "headset": "<path d=\"M4 10V8a4 4 0 1 1 8 0v2\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><path d=\"M4 10a2 2 0 0 0-2 2v1a2 2 0 0 0 2 2h1V10H4z\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/><path d=\"M12 10h-1v5h1a2 2 0 0 0 2-2v-1a2 2 0 0 0-2-2z\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/>",
  "paper-plane": "<path d=\"M1.5 3l13 5-13 5L4 8l-2.5-5z\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linejoin=\"round\"/><path d=\"M14 8H4\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\"/>",
  "bug": "<circle cx=\"8\" cy=\"6\" r=\"2.5\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/><path d=\"M4 8h8\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\"/><path d=\"M5.5 4.5L3 2M10.5 4.5L13 2\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.3\" stroke-linecap=\"round\"/><path d=\"M5.5 11.5L3 14M10.5 11.5L13 14\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.3\" stroke-linecap=\"round\"/><path d=\"M5 8a3 3 0 0 0 6 0\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/><path d=\"M4 14a6 6 0 0 0 8 0\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/>",
  "lightbulb": "<path d=\"M5.5 10.5A4 4 0 1 1 10.5 7c0 1.8-1 2.8-1.5 3.5V12h-2v-1.5c-.5-.7-1.5-1.7-1.5-3.5z\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M6.5 13.5h3M7 15h2\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\"/>",
  "people-group": "<circle cx=\"5\" cy=\"4.5\" r=\"2\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/><circle cx=\"11\" cy=\"4.5\" r=\"2\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/><circle cx=\"8\" cy=\"10\" r=\"2\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/><path d=\"M2 13a4 4 0 0 1 6 0M14 13a4 4 0 0 0-6 0M5 10a3 3 0 0 0-3 3M13 13a3 3 0 0 0-3-3\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/>",
  "scale-balanced": "<path d=\"M3 3h10l-1 6H4L3 3z\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linejoin=\"round\"/><path d=\"M8 1.5V9\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\"/><path d=\"M5 14l3-2 3 2\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/>",
  "crown": "<path d=\"M2 12l2-7 4 3 4-3 2 7H2z\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linejoin=\"round\"/><circle cx=\"4\" cy=\"10\" r=\"1\" fill=\"currentColor\"/><circle cx=\"12\" cy=\"10\" r=\"1\" fill=\"currentColor\"/><circle cx=\"8\" cy=\"4.5\" r=\"1\" fill=\"currentColor\"/>",
  "heart-pulse": "<path d=\"M8 13.5l-5.5-5A3.5 3.5 0 0 1 8 4.5a3.5 3.5 0 0 1 5.5 4\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/><path d=\"M5.5 9.5l1-2 1 2 1-2 1 2\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/>",
  "arrow-up": "<path d=\"M8 14V3M3 7.5L8 2l5 5.5\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/>",
};

function FooterIcon({ name, className }: { name: string; className?: string }) {
  const pathData = ICONS[name];
  if (!pathData) return null;
  return (
    <svg
      className={className}
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      dangerouslySetInnerHTML={{ __html: pathData }}
    />
  );
}

function buildHrefWithOrigin(href: string) {
  if (typeof window === "undefined") return href;
  return new URL(href, window.location.origin).toString();
}

export default function ViruFooterBlock() {
  const { t } = useI18n();
  const pathname = usePathname() ?? "/";
  const shouldReduceMotion = useReducedMotion();
  const [hasSession, setHasSession] = useState(false);

  useEffect(() => {
    setHasSession(hasToken());
  }, []);

  const isPrivateRoute =
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
  const isPrivateContext = isPrivateRoute || hasSession;

  const isAdminContext = pathname.startsWith("/admin");

  const footerGroups = useMemo<FooterGroup[]>(() => {
    const publicGroups: FooterGroup[] = [
      {
        title: t("shared.footer.groups.explore"),
        links: [
          { label: t("shared.footer.links.home"), href: "/", icon: "house" },
          { label: t("shared.footer.links.help"), href: "/ayuda", icon: "circle-question" },
          { label: t("shared.footer.links.policies"), href: "/policies", icon: "shield-heart" },
        ],
      },
      {
        title: t("shared.footer.groups.access"),
        links: [
          { label: t("shared.actions.enter"), href: "/login", icon: "right-to-bracket" },
          { label: t("shared.footer.links.register"), href: "/register", icon: "user-plus" },
        ],
      },
      {
        title: t("shared.footer.groups.contact"),
        links: [
          {
            label: t("shared.footer.links.supportEmail"),
            href: "mailto:soporte@viru.app",
            icon: "envelope",
            external: true,
          },
          {
            label: t("shared.footer.links.privacyEmail"),
            href: "mailto:privacidad@viru.app",
            icon: "user-shield",
            external: true,
          },
          {
            label: t("shared.footer.links.pressEmail"),
            href: "mailto:press@viru.app",
            icon: "newspaper",
            external: true,
          },
        ],
      },
    ];

    const privateGroups: FooterGroup[] = [
      {
        title: t("shared.footer.groups.workspace"),
        links: [
          { label: t("shared.footer.links.dashboard"), href: "/dashboard", icon: "table-columns" },
          { label: t("shared.footer.links.watchlist"), href: "/watchlist", icon: "binoculars" },
          { label: t("shared.footer.links.quickSearch"), href: "/quick-search", icon: "magnifying-glass-chart" },
          { label: t("shared.footer.links.alerts"), href: "/alerts", icon: "bell" },
          { label: t("shared.footer.links.opportunities"), href: "/recomendaciones", icon: "sparkles" },
        ],
      },
      {
        title: t("shared.footer.groups.account"),
        links: [
          { label: t("shared.footer.links.profile"), href: "/cuenta/perfil", icon: "id-card-clip" },
          { label: t("shared.footer.links.security"), href: "/cuenta/seguridad", icon: "shield-halved" },
          { label: t("shared.footer.links.preferences"), href: "/preferencias", icon: "sliders" },
          { label: t("shared.footer.links.appearance"), href: "/preferencias/apariencia", icon: "palette" },
          { label: t("shared.footer.links.searchPrefs"), href: "/preferencias/busqueda", icon: "compass-drafting" },
          { label: t("shared.footer.links.region"), href: "/preferencias/region", icon: "globe" },
        ],
      },
      {
        title: t("shared.footer.groups.support"),
        links: [
          { label: t("shared.footer.links.supportHelp"), href: "/soporte/ayuda", icon: "headset" },
          { label: t("shared.footer.links.contact"), href: "/soporte/contacto", icon: "paper-plane" },
          { label: t("shared.footer.links.feedback"), href: "/soporte/feedback", icon: "bug" },
          { label: t("shared.footer.links.productFeedback"), href: "/soporte/feedback?type=idea", icon: "lightbulb" },
          { label: t("shared.footer.links.aboutUs"), href: "/soporte/about-us", icon: "people-group" },
          { label: t("shared.footer.links.policies"), href: "/policies", icon: "scale-balanced" },
        ],
      },
    ];

    if (isAdminContext) {
      privateGroups.push({
        title: t("shared.footer.groups.admin"),
        links: [
          { label: t("shared.footer.links.admin"), href: "/admin", icon: "crown" },
          { label: t("shared.footer.links.productHealth"), href: "/admin/product-health", icon: "heart-pulse" },
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
      <div className="viru-footer-glow viru-footer-glow-primary" aria-hidden="true" />
      <div className="viru-footer-glow viru-footer-glow-secondary" aria-hidden="true" />
      <div className="shell viru-footer-shell">
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
                <FooterIcon name="arrow-up" />
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
                        {link.icon ? <FooterIcon name={link.icon} /> : null}
                        <span>{link.label}</span>
                      </a>
                    ) : (
                      <Link href={link.href} className="viru-footer-link">
                        {link.icon ? <FooterIcon name={link.icon} /> : null}
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
          <p>{t("shared.footer.copyright", { year: new Date().getFullYear() })}</p>
          <p>{t("shared.footer.note")}</p>
        </div>
      </div>
    </motion.footer>
  );
}
