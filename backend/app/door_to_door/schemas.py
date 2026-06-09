from datetime import datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field, model_validator

DoorToDoorSourceType = Literal["api", "open_data", "aggregator", "deeplink", "scraper", "mock", "estimate", "maps", "external_deeplink"]
DoorToDoorOptionStatus = Literal["real_result", "real_deeplink", "estimate_only"]
DoorToDoorCompleteness = Literal["full", "partial_actionable", "exploratory"]
DoorToDoorDeepLinkKind = Literal["directions", "provider_search", "booking"]
DoorToDoorConfidence = Literal["live", "cached", "estimated", "deeplink", "unavailable"]
DoorToDoorLocationType = Literal["city", "address", "station", "saved_location", "airport", "airport_only"]
DoorToDoorSortBy = Literal["best_balance", "cheapest", "fastest", "fewest_changes"]
DoorToDoorLuggage = Literal["backpack", "cabin", "checked"]
DoorToDoorMode = Literal["bus", "train", "rideshare", "shuttle", "taxi", "car", "walking", "flight"]
DoorToDoorSuggestionSourceType = Literal["local_static", "mock", "api", "open_data"]
DoorToDoorCapabilityState = Literal["available", "partial", "planned", "unavailable"]
DoorToDoorCapabilityKey = Literal[
    "navigation",
    "traffic",
    "transit",
    "alternatives",
    "street_view_preview",
    "saved_places",
    "nearby_pois",
    "offline",
    "incidents",
    "eco_route",
]
DoorToDoorProviderStatusKind = Literal[
    "functional_api",
    "functional_mock",
    "functional_deeplink",
    "functional_open_data",
    "functional_scraper",
    "functional_estimate",
    "functional_maps",
    "scraper_base_only",
    "deeplink_stub",
    "pure_stub",
    "disabled",
]


class DoorToDoorLocation(BaseModel):
    type: DoorToDoorLocationType
    label: str = Field(min_length=1, max_length=180)
    lat: float | None = None
    lng: float | None = None
    place_id: str | None = Field(default=None, max_length=220)


class DoorToDoorPreferences(BaseModel):
    min_airport_buffer_minutes: int = Field(default=120, ge=45, le=360)
    max_price: float | None = Field(default=None, ge=0)
    passengers: int = Field(default=1, ge=1, le=9)
    luggage: DoorToDoorLuggage = "cabin"
    allow_bus: bool = True
    allow_train: bool = True
    allow_rideshare: bool = True
    allow_shuttle: bool = True
    allow_taxi: bool = False
    allow_car: bool = True
    public_transport_only: bool = False
    sort_by: DoorToDoorSortBy = "best_balance"


class DoorToDoorSearchRequest(BaseModel):
    flight_watch_id: str = Field(
        min_length=1,
        max_length=80,
        validation_alias=AliasChoices("flight_watch_id", "watchId"),
        serialization_alias="flight_watch_id",
    )
    origin: DoorToDoorLocation
    final_destination: DoorToDoorLocation
    preferences: DoorToDoorPreferences = Field(default_factory=DoorToDoorPreferences)
    save_origin_as_default: bool = False

    @model_validator(mode="after")
    def normalize_public_transport_only(self):
        if self.preferences.public_transport_only:
            self.preferences.allow_rideshare = False
            self.preferences.allow_shuttle = False
            self.preferences.allow_taxi = False
            self.preferences.allow_car = False
        return self


class DoorToDoorFlightOut(BaseModel):
    origin_airport: str
    destination_airport: str
    departure_at: datetime
    arrival_at: datetime
    flight_time_confidence: DoorToDoorConfidence


class DoorToDoorSourceOut(BaseModel):
    provider: str
    source_provider: str
    source_type: DoorToDoorSourceType
    confidence: DoorToDoorConfidence
    checked_at: datetime
    expires_at: datetime | None = None
    booking_url: str | None = None


class DoorToDoorActionOut(BaseModel):
    id: str
    provider: Literal["google_maps", "blablacar", "goopti", "gtfs"]
    label: str
    url: str
    kind: Literal["directions", "provider_search", "booking"]
    opens_external: bool = True
    source_status: Literal["external_search", "real_result"]
    price_status: Literal["external", "confirmed", "unavailable"]
    availability_status: Literal["external", "confirmed", "unavailable"]
    trust_copy: str


class DoorToDoorLegOut(BaseModel):
    type: Literal["ground", "flight"]
    mode: DoorToDoorMode
    from_location: str = Field(alias="from")
    to_location: str = Field(alias="to")
    departure_at: datetime | None = None
    arrival_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=0)
    distance_meters: int | None = Field(default=None, ge=0)
    price_min: float | None = Field(default=None, ge=0)
    price_max: float | None = Field(default=None, ge=0)
    provider: str | None = None
    booking_url: str | None = None
    source_type: DoorToDoorSourceType | None = None
    confidence: DoorToDoorConfidence | None = None
    actions: list[DoorToDoorActionOut] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class DoorToDoorDeepLinkOut(BaseModel):
    url: str
    label: str
    kind: DoorToDoorDeepLinkKind
    opens_external: bool = True


class DoorToDoorPriceOut(BaseModel):
    amount: float | None = None
    currency: str | None = None
    status: Literal["confirmed", "unavailable", "external", "estimated"] = "unavailable"


class DoorToDoorOptionOut(BaseModel):
    id: str
    label: str
    description: str
    status: DoorToDoorOptionStatus = "real_deeplink"
    total_price_min: float | None = Field(default=None, ge=0)
    total_price_max: float | None = Field(default=None, ge=0)
    price_per_person_min: float | None = Field(default=None, ge=0)
    price_per_person_max: float | None = Field(default=None, ge=0)
    currency: str = "EUR"
    total_duration_minutes: int | None = Field(default=None, ge=0)
    score: int | None = Field(default=None, ge=0, le=100)
    transfer_count: int = Field(ge=0)
    airport_buffer_minutes: int | None = Field(default=None, ge=0)
    confidence: DoorToDoorConfidence
    source_types: list[DoorToDoorSourceType]
    sources: list[DoorToDoorSourceOut]
    legs: list[DoorToDoorLegOut]
    is_recommended: bool = False
    is_extended: bool = False
    completeness: DoorToDoorCompleteness = "exploratory"
    deep_link: DoorToDoorDeepLinkOut | None = None
    price: DoorToDoorPriceOut | None = None
    trust_copy: str | None = None


class DoorToDoorSummaryOut(BaseModel):
    recommended_option_id: str | None = None
    cheapest_option_id: str | None = None
    fastest_option_id: str | None = None
    fewest_changes_option_id: str | None = None
    history_id: str | None = None
    chosen_option_id: str | None = None


class DoorToDoorWarningOut(BaseModel):
    code: str
    message: str
    provider: str | None = None


class DoorToDoorMapCapabilityOut(BaseModel):
    state: DoorToDoorCapabilityState
    source_type: DoorToDoorSourceType | Literal["none"]
    confidence: DoorToDoorConfidence
    last_checked_at: datetime | None = None
    why_missing: str | None = None


class DoorToDoorSearchResponse(BaseModel):
    flight: DoorToDoorFlightOut
    summary: DoorToDoorSummaryOut
    options: list[DoorToDoorOptionOut]
    warnings: list[DoorToDoorWarningOut] = Field(default_factory=list)
    map_capabilities: dict[DoorToDoorCapabilityKey, DoorToDoorMapCapabilityOut] | None = None


class DoorToDoorSuggestionOut(BaseModel):
    id: str
    type: DoorToDoorLocationType
    label: str
    subtitle: str
    source_type: DoorToDoorSuggestionSourceType = "local_static"
    lat: float | None = None
    lng: float | None = None
    place_id: str | None = None


class DoorToDoorSuggestionsMetaOut(BaseModel):
    provider_status: Literal["api_live", "fallback_active", "provider_error"] = "api_live"
    degraded_reason: str | None = None
    used_region_codes: list[str] = Field(default_factory=list)


class DoorToDoorSuggestionsResponseOut(BaseModel):
    items: list[DoorToDoorSuggestionOut] = Field(default_factory=list)
    meta: DoorToDoorSuggestionsMetaOut = Field(default_factory=DoorToDoorSuggestionsMetaOut)


class DoorToDoorSavedLocationIn(BaseModel):
    location: DoorToDoorLocation


class DoorToDoorSavedLocationOut(BaseModel):
    id: str
    type: DoorToDoorLocationType
    label: str
    lat: float | None = None
    lng: float | None = None
    updated_at: datetime


class DoorToDoorHistoryOut(BaseModel):
    id: str
    watch_id: str
    origin_label: str
    final_destination_label: str
    origin: dict | None = None
    final_destination: dict | None = None
    preferences: dict | None = None
    created_at: datetime
    recommended_option_id: str | None = None
    recommended_label: str | None = None
    total_price_min: float | None = None
    total_price_max: float | None = None
    chosen_option_id: str | None = None


class DoorToDoorChosenOptionIn(BaseModel):
    option_id: str = Field(min_length=1, max_length=80)
    option_label: str = Field(min_length=1, max_length=120)
    option_summary: dict = Field(default_factory=dict)


class DoorToDoorChosenOptionOut(BaseModel):
    id: str
    watch_id: str
    history_id: str | None = None
    option_id: str
    option_label: str
    chosen_at: datetime


class DoorToDoorSavedPlaceIn(BaseModel):
    label: str = Field(min_length=1, max_length=180)
    note: str = Field(default="", max_length=280)
    watch_id: str | None = Field(default=None, max_length=80)


class DoorToDoorSavedPlaceOut(BaseModel):
    id: str
    label: str
    note: str
    watch_id: str | None = None
    created_at: datetime


class DoorToDoorProviderStatusOut(BaseModel):
    name: str
    enabled: bool
    status: DoorToDoorProviderStatusKind
    source_type: DoorToDoorSourceType
    production_ready: bool
    supports_search: bool
    supports_booking_url: bool
    has_tests: bool
    notes: str | None = None
