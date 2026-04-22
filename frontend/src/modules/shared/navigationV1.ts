export const NAV_V1_PRIVATE = [
  { href: "/dashboard", label: "Panel" },
  { href: "/watchlist", label: "Seguimiento" },
  { href: "/quick-search", label: "Búsqueda rápida" },
  { href: "/alerts", label: "Alertas" },
  { href: "/recomendaciones", label: "Recomendaciones" },
  { href: "/preferencias", label: "Preferencias" },
  { href: "/soporte/ayuda", label: "Ayuda" },
] as const;

export const NAV_V1_PUBLIC = [
  { href: "/", label: "Inicio" },
  { href: "/ayuda", label: "Ayuda" },
  { href: "/policies", label: "Políticas" },
  { href: "/login", label: "Entrar" },
  { href: "/register", label: "Crear cuenta" },
] as const;

export const CANONICAL_ROUTES = {
  history: "/watchlist",
  preferences: "/preferencias",
  supportFeedback: "/soporte/feedback",
  privateContact: "/soporte/contacto",
  suggestions: "/suggestions",
  publicHelp: "/ayuda",
  privateHelp: "/soporte/ayuda",
} as const;
