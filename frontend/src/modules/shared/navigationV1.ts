export const NAV_V1_PRIVATE = [
  { href: "/dashboard", labelKey: "shared.footer.links.dashboard" },
  { href: "/watchlist", labelKey: "shared.footer.links.watchlist" },
  { href: "/puerta-a-puerta", labelKey: "shared.footer.links.doorToDoor" },
  { href: "/quick-search", labelKey: "shared.footer.links.quickSearch" },
  { href: "/alerts", labelKey: "shared.footer.links.alerts" },
  { href: "/recomendaciones", labelKey: "shared.footer.links.opportunities" },
  { href: "/preferencias", labelKey: "shared.footer.links.preferences" },
  { href: "/soporte/ayuda", labelKey: "shared.footer.links.help" },
] as const;

export const NAV_V1_PUBLIC = [
  { href: "/", labelKey: "shared.footer.links.home" },
  { href: "/ayuda", labelKey: "shared.footer.links.help" },
  { href: "/policies", labelKey: "shared.footer.links.policies" },
  { href: "/login", labelKey: "shared.actions.enter" },
  { href: "/register", labelKey: "shared.footer.links.register" },
] as const;

export const CANONICAL_ROUTES = {
  history: "/watchlist",
  preferences: "/preferencias",
  supportFeedback: "/soporte/feedback",
  privateContact: "/soporte/contacto",
  suggestions: "/soporte/feedback?type=idea",
  publicHelp: "/ayuda",
  privateHelp: "/soporte/ayuda",
} as const;
