export const PRODUCT_VOCAB = {
  watchlist: {
    label: "Watchlist",
    route: "/watchlist",
    api: "/api/v1/watchlist",
    entity: "FlightWatch",
  },
  history: {
    label: "Historico",
    route: "/watchlist",
    api: "/api/v1/prices",
    entity: "PriceSnapshot",
    legacy: "/history",
  },
  alerts: {
    label: "Alertas",
    route: "/alerts",
    api: "/api/v1/alerts",
    entity: "AlertRule",
  },
  opportunities: {
    label: "Oportunidades",
    route: "/recomendaciones",
    api: "/api/v1/recommendations",
    entity: "RecommendationResult",
  },
  preferences: {
    label: "Preferencias",
    route: "/preferencias",
    api: "/api/v1/preferences",
    entity: "UserPreference",
    legacy: "/preferences",
  },
  feedback: {
    label: "Feedback de producto",
    route: "/soporte/feedback?type=idea",
    api: "/api/v1/support/feedback",
    entity: "SupportFeedback",
    legacy: "/suggestions",
  },
} as const;

export const UNSPECIFIED_MODEL_NAMES = [
  "watchlist_item",
  "activity_event",
  "system_status",
] as const;
