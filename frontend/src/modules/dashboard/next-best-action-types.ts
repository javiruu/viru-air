export type DashboardWatch = {
  id: string;
  origin_iata: string;
  destination_iata: string;
  travel_date_local: string;
};

export type DashboardHistoryRow = {
  watch_id: string;
  captured_at_utc: string;
  raw_price: number;
  raw_currency: string;
};

export type DashboardNotificationSummary = {
  total: number;
  unread: number;
  price: number;
  security: number;
  digest: number;
  worker: number;
};

export type DashboardNextAction =
  | {
      kind: "strong_drop";
      key: string;
      routeLabel: string;
      watchId: string;
      origin: string;
      destination: string;
      travelDate: string;
      dropAmount: number;
      latestPrice: number;
      previousPrice: number;
      currency: string;
    }
  | {
      kind: "new_low";
      key: string;
      routeLabel: string;
      watchId: string;
      origin: string;
      destination: string;
      travelDate: string;
      latestPrice: number;
      previousLowPrice: number;
      currency: string;
    }
  | {
      kind: "best_month";
      key: string;
      routeLabel: string;
      watchId: string;
      origin: string;
      destination: string;
      travelDate: string;
      latestPrice: number;
      currency: string;
      monthlyObservationCount: number;
    }
  | {
      kind: "unread_alerts";
      key: string;
      unreadCount: number;
    }
  | {
      kind: "stale_watch";
      key: string;
      routeLabel: string;
      watchId: string;
      origin: string;
      destination: string;
      travelDate: string;
      staleHours: number | null;
      lastUpdatedAt: string | null;
    }
  | {
      kind: "onboarding";
      key: string;
    }
  | {
      kind: "calm";
      key: string;
      trackedCount: number;
    };
