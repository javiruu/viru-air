from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_serializer


LiveCoverage = Literal[
    "live",
    "cached",
    "identity_missing",
    "not_configured",
    "no_coverage",
    "temporarily_unavailable",
    "completed",
]
LiveProviderStatus = Literal[
    "ok",
    "not_configured",
    "no_match",
    "ambiguous",
    "rate_limited",
    "unavailable",
]


class _UtcResponseModel(BaseModel):
    @field_serializer("*", when_used="json", check_fields=False)
    def serialize_utc_datetimes(self, value: object) -> object:
        if not isinstance(value, datetime):
            return value
        aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        return aware.isoformat().replace("+00:00", "Z")


class LiveFlightIdentityOut(_UtcResponseModel):
    flight_instance_fingerprint: str
    flight_number: str | None = None
    carrier_code: str | None = None
    origin_iata: str
    destination_iata: str
    scheduled_departure_at: datetime | None = None
    scheduled_arrival_at: datetime | None = None


class LiveFlightMilestoneOut(_UtcResponseModel):
    scheduled_at: datetime | None = None
    estimated_at: datetime | None = None
    actual_at: datetime | None = None
    terminal: str | None = None
    gate: str | None = None
    delay_minutes: int | None = None


class LiveFlightPositionOut(_UtcResponseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    altitude_m: float | None = Field(default=None, ge=-500, le=30000)
    speed_mps: float | None = Field(default=None, ge=0, le=500)
    heading_deg: float | None = Field(default=None, ge=0, le=360)
    on_ground: bool | None = None


class LiveFlightOperationalOut(_UtcResponseModel):
    status: Literal["scheduled", "active", "landed", "cancelled", "diverted", "unknown"]
    status_raw: str | None = None
    observed_at: datetime
    expires_at: datetime
    freshness: Literal["fresh", "stale"]
    provider: str
    callsign: str | None = None
    departure: LiveFlightMilestoneOut
    arrival: LiveFlightMilestoneOut
    position: LiveFlightPositionOut | None = None
    registration: str | None = None
    aircraft_iata: str | None = None
    aircraft_icao: str | None = None
    data_quality: str


class LiveIncomingAircraftOut(_UtcResponseModel):
    registration: str
    flight_number: str | None = None
    origin_iata: str
    destination_iata: str
    status: Literal["scheduled", "active", "landed", "cancelled", "diverted", "unknown"]
    scheduled_arrival_at: datetime
    estimated_arrival_at: datetime | None = None
    actual_arrival_at: datetime | None = None
    observed_at: datetime
    freshness: Literal["fresh", "stale"]


class LiveDelayPredictionAvailableOut(_UtcResponseModel):
    status: Literal["available"] = "available"
    model_version: Literal["viru_rotation_v1"] = "viru_rotation_v1"
    risk: Literal["low", "elevated", "high"]
    risk_score: int = Field(ge=0, le=100)
    confidence: Literal["low", "medium", "high"]
    predicted_delay_min_minutes: int = Field(ge=0)
    predicted_delay_max_minutes: int = Field(ge=0)
    turnaround_minutes: int
    factor_codes: list[
        Literal[
            "incoming_running_late",
            "tight_turnaround",
            "incoming_airborne",
            "official_delay_signal",
            "incoming_landed",
            "healthy_turnaround",
            "stale_observation",
        ]
    ]
    incoming_aircraft: LiveIncomingAircraftOut


class LiveDelayPredictionUnavailableOut(_UtcResponseModel):
    status: Literal["insufficient_data", "not_applicable"]
    model_version: Literal["viru_rotation_v1"] = "viru_rotation_v1"
    reason: Literal[
        "operational_data_missing",
        "registration_missing",
        "schedule_missing",
        "incoming_not_found",
        "already_departed",
        "flight_terminal",
    ]


LiveDelayPredictionOut = LiveDelayPredictionAvailableOut | LiveDelayPredictionUnavailableOut


class LiveFlightLegOut(_UtcResponseModel):
    sequence: int = Field(ge=0)
    identity: LiveFlightIdentityOut
    operational: LiveFlightOperationalOut | None = None
    delay_prediction: LiveDelayPredictionOut | None = None


class LiveFlightTrackingOut(_UtcResponseModel):
    watch_id: str
    coverage: LiveCoverage
    provider_status: LiveProviderStatus
    generated_at: datetime
    refresh_after_seconds: int = Field(ge=30)
    legs: list[LiveFlightLegOut] = Field(default_factory=list)
