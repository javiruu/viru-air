export type LiveFlightCoverage =
  | "live"
  | "cached"
  | "identity_missing"
  | "not_configured"
  | "no_coverage"
  | "temporarily_unavailable"
  | "completed";

export type LiveFlightStatus =
  | "scheduled"
  | "active"
  | "landed"
  | "cancelled"
  | "diverted"
  | "unknown";

export type LiveFlightMilestone = {
  scheduled_at: string | null;
  estimated_at: string | null;
  actual_at: string | null;
  terminal: string | null;
  gate: string | null;
  delay_minutes: number | null;
};

export type LiveFlightPosition = {
  latitude: number;
  longitude: number;
  altitude_m: number | null;
  speed_mps: number | null;
  heading_deg: number | null;
  on_ground: boolean | null;
};

export type LiveFlightOperational = {
  status: LiveFlightStatus;
  status_raw: string | null;
  observed_at: string;
  expires_at: string;
  freshness: "fresh" | "stale";
  provider: string;
  callsign: string | null;
  departure: LiveFlightMilestone;
  arrival: LiveFlightMilestone;
  position: LiveFlightPosition | null;
  registration: string | null;
  aircraft_iata: string | null;
  aircraft_icao: string | null;
  data_quality: string;
};

export type LiveFlightLeg = {
  sequence: number;
  identity: {
    flight_instance_fingerprint: string;
    flight_number: string | null;
    carrier_code: string | null;
    origin_iata: string;
    destination_iata: string;
    scheduled_departure_at: string | null;
    scheduled_arrival_at: string | null;
  };
  operational: LiveFlightOperational | null;
};

export type LiveFlightTracking = {
  watch_id: string;
  coverage: LiveFlightCoverage;
  provider_status:
    | "ok"
    | "not_configured"
    | "no_match"
    | "ambiguous"
    | "rate_limited"
    | "unavailable";
  generated_at: string;
  refresh_after_seconds: number;
  legs: LiveFlightLeg[];
};
