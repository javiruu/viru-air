export type DashboardNewsItem = {
  title: string;
  excerpt: string;
  author: string;
  publishedAt: string;
  readTime: string;
  image: string;
  href: string;
  eyebrow: string;
  ctaLabel: string;
};

const dashboardNewsEs: DashboardNewsItem = {
  eyebrow: "Novedad del producto",
  title: "Ventanas de precio, señales y contexto: así leeremos las próximas oportunidades en Viru.",
  excerpt:
    "Estamos afinando cómo resumimos cambios de precio y criterio operativo para que una actualización importante se entienda en segundos, sin perder la lectura editorial que ayuda a decidir cuándo comprar.",
  author: "Equipo Viru",
  publishedAt: "2026-04-20",
  readTime: "4 min de lectura",
  image: "/images/dashboard-news-flight-window.svg",
  href: "/soporte/about-us?from=dashboard-news",
  ctaLabel: "Leer actualización",
};

const dashboardNewsEn: DashboardNewsItem = {
  eyebrow: "Product update",
  title: "Price windows, signals, and context: how Viru will frame the next opportunities.",
  excerpt:
    "We are refining the way major price changes and travel signals are summarized so each update reads in seconds, while keeping the editorial context users need before deciding when to buy.",
  author: "Viru team",
  publishedAt: "2026-04-20",
  readTime: "4 min read",
  image: "/images/dashboard-news-flight-window.svg",
  href: "/soporte/about-us?from=dashboard-news",
  ctaLabel: "Read update",
};

export function getDashboardFeaturedNews(localeTag?: string): DashboardNewsItem {
  if (localeTag?.toLowerCase().startsWith("es")) {
    return dashboardNewsEs;
  }

  return dashboardNewsEn;
}
