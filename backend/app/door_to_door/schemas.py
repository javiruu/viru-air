from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

DoorToDoorSourceType = Literal["api", "open_data", "aggregator", "deeplink", "scraper", "mock"]
DoorToDoorConfidence = Literal["live", "cached", "estimated", "deeplink", "unavailable"]
DoorToDoorRiskLevel = Literal["low", "medium", "high", "unknown"]
DoorToDoorLocationType = Literal["city", "address", "station", "saved_location", "airport", "airport_only"]
DoorToDoorSortBy = Literal["best_balance", "cheapest", "lowest_risk", "fastest", "fewest_changes"]
DoorToDoorLuggage = Literal["backpack", "cabin", "checked"]
DoorToDoorMode = Literal["bus", "train", "rideshare", "shuttle", "taxi", "car", "walking", "flight"]


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
    flight_watch_id: str = Field(min_length=1, max_length=80)
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


class DoorToDoorLegOut(BaseModel):
    type: Literal["ground", "flight"]
    mode: DoorToDoorMode
    from_label: str = Field(alias="from")
    to_label: str = Field(alias="to")
    departure_at: datetime | None = None
    arrival_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=0)
    price_min: float | None = Field(default=None, ge=0)
    price_max: float | None = Field(default=None, ge=0)
    provider: str | None = None
    booking_url: str | None = None
    source_type: DoorToDoorSourceType | None = None
    confidence: DoorToDoorConfidence | None = None

    model_config = {"populate_by_name": True}


class DoorToDoorOptionOut(BaseModel):
    id: str
    label: str
    description: str
    total_price_min: float | None = Field(default=None, ge=0)
    total_price_max: float | None = Field(default=None, ge=0)
    price_per_person_min: float | None = Field(default=None, ge=0)
    price_per_person_max: float | None = Field(default=None, ge=0)
    currency: str = "EUR"
    total_duration_minutes: int = Field(ge=0)
    risk_level: DoorToDoorRiskLevel
    score: int = Field(ge=0, le=100)
    transfer_count: int = Field(ge=0)
    airport_buffer_minutes: int | None = Field(default=None, ge=0)
    confidence: DoorToDoorConfidence
    source_types: list[DoorToDoorSourceType]
    sources: list[DoorToDoorSourceOut]
    legs: list[DoorToDoorLegOut]
    is_recommended: bool = False
    is_extended: bool = False


class DoorToDoorSummaryOut(BaseModel):
    recommended_option_id: str | None = None
    cheapest_option_id: str | None = None
    lowest_risk_option_id: str | None = None
    fastest_option_id: str | None = None
    fewest_changes_option_id: str | None = None
    history_id: str | None = None
    chosen_option_id: str | None = None


class DoorToDoorWarningOut(BaseModel):
    code: str
    message: str
    provider: str | None = None


class DoorToDoorSearchResponse(BaseModel):
    flight: DoorToDoorFlightOut
    summary: DoorToDoorSummaryOut
    options: list[DoorToDoorOptionOut]
    warnings: list[DoorToDoorWarningOut] = Field(default_factory=list)


class DoorToDoorSuggestionOut(BaseModel):
    id: str
    type: DoorToDoorLocationType
    label: str
    subtitle: str
    lat: float | None = None
    lng: float | None = None


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
    created_at: datetime
    recommended_option_id: str | None = None
    recommended_label: str | None = None
    total_price_min: float | None = None
    total_price_max: float | None = None
    risk_level: DoorToDoorRiskLevel | None = None
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
