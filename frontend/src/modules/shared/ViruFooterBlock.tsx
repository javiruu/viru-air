"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { useMemo } from "react";
import { usePathname } from "next/navigation";

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

export default function ViruFooterBlock() {
  const { t } = useI18n();
  const pathname = usePathname() ?? "/";
  const shouldReduceMotion = useReducedMotion();

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
  const isPrivateContext = isPrivateRoute;

  const isAdminContext = pathname.startsWith("/admin");

  const footerGroups = useMemo<FooterGroup[]>(() => {
    const publicGroups: FooterGroup[] = [
      {
        title: t("shared.footer.groups.explore"),
        links: [
          { label: t("shared.footer.links.home"), href: "/" },
          { label: t("shared.footer.links.help"), href: "/ayuda" },
          { label: t("shared.footer.links.policies"), href: "/policies" },
        ],
      },
      {
        title: t("shared.footer.groups.account"),
        links: [
          { label: t("shared.actions.enter"), href: "/login" },
          { label: t("shared.footer.links.register"), href: "/register" },
        ],
      },
      {
        title: t("shared.footer.groups.contact"),
        links: [
          { label: t("shared.footer.links.supportEmail"), href: "mailto:soporte@viru.app", external: true },
          { label: t("shared.footer.links.privacyEmail"), href: "mailto:privacidad@viru.app", external: true },
          { label: t("shared.footer.links.pressEmail"), href: "mailto:press@viru.app", external: true },
        ],
      },
    ];

    const privateGroups: FooterGroup[] = [
      {
        title: t("shared.footer.groups.workspace"),
        links: [
          { label: t("shared.footer.links.dashboard"), href: "/dashboard" },
          { label: t("shared.footer.links.watchlist"), href: "/watchlist" },
          { label: t("shared.footer.links.quickSearch"), href: "/quick-search" },
          { label: t("shared.footer.links.alerts"), href: "/alerts" },
          { label: t("shared.footer.links.opportunities"), href: "/recomendaciones" },
        ],
      },
      {
        title: t("shared.footer.groups.account"),
        links: [
          { label: t("shared.footer.links.profile"), href: "/cuenta/perfil" },
          { label: t("shared.footer.links.security"), href: "/cuenta/seguridad" },
          { label: t("shared.footer.links.preferences"), href: "/preferencias" },
          { label: t("shared.footer.links.appearance"), href: "/preferencias/apariencia" },
          { label: t("shared.footer.links.searchPrefs"), href: "/preferencias/busqueda" },
          { label: t("shared.footer.links.region"), href: "/preferencias/region" },
        ],
      },
      {
        title: t("shared.footer.groups.support"),
        links: [
          { label: t("shared.footer.links.supportHelp"), href: "/soporte/ayuda" },
          { label: t("shared.footer.links.contact"), href: "/soporte/contacto" },
          { label: t("shared.footer.links.feedback"), href: "/soporte/feedback" },
          { label: t("shared.footer.links.productFeedback"), href: "/soporte/feedback?type=idea" },
          { label: t("shared.footer.links.aboutUs"), href: "/soporte/about-us" },
          { label: t("shared.footer.links.policies"), href: "/policies" },
        ],
      },
    ];

    if (isAdminContext) {
      privateGroups.push({
        title: t("shared.footer.groups.admin"),
        links: [
          { label: t("shared.footer.links.admin"), href: "/admin" },
          { label: t("shared.footer.links.productHealth"), href: "/admin/product-health" },
        ],
      });
    }

    return isPrivateContext ? privateGroups : publicGroups;
  }, [isAdminContext, isPrivateContext, t]);

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
            <div className="viru-footer-brand-copy">
              <h2>Viru Tracker</h2>
              <p>
                {isPrivateContext ? t("shared.footer.privateBody") : t("shared.footer.publicBody")}
              </p>
              <span className="viru-footer-context-pill">
                {isPrivateContext ? t("shared.footer.statusPrivate") : t("shared.footer.statusPublic")}
              </span>
            </div>
          </div>
        </motion.div>

        <nav className="viru-footer-grid" aria-label={t("shared.footer.navLabel")}>
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
                        <span>{link.label}</span>
                      </a>
                    ) : (
                      <Link href={link.href} className="viru-footer-link">
                        <span>{link.label}</span>
                      </Link>
                    )}
                  </li>
                  ))}
                </ul>
            </motion.section>
          ))}
        </nav>

        <div className="viru-footer-bottom">
          <p>
            {t("shared.footer.copyright", { year: new Date().getFullYear() })}
          </p>
          <div className="viru-footer-bottom-links">
            <Link href="/policies" className="viru-footer-link-inline">
              {t("shared.footer.links.policies")}
            </Link>
            <button
              type="button"
              className="viru-footer-link-inline viru-footer-link-inline-button"
              onClick={() => window.scrollTo({ top: 0, behavior: shouldReduceMotion ? "auto" : "smooth" })}
            >
              {t("shared.footer.scrollTop")}
            </button>
          </div>
        </div>
      </div>
    </motion.footer>
  );
}
