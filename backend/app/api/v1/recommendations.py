import datetime as dt
import json
import math
import os
from typing import Any, Iterable

import requests
from fastapi import APIRouter, Body, HTTPException

from app.core.errors import ApiError, message_for_code

from app.domain.schemas import RecommendationRequest, RecommendationResponse
from app.infrastructure.airports_catalog import expand_airports, get_airport
from app.infrastructure.providers.ryanair_public_provider import RyanairPublicProvider

router = APIRouter()
provider = RyanairPublicProvider()

OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


def _normalize_iata_list(value: str | list[str] | None) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        items = [str(item).strip().upper() for item in value]
    else:
        items = [item.strip().upper() for item in value.split(",")]
    return [item for item in items if item]


def _parse_iata_input(value: str | list[str]) -> list[str]:
    codes = _normalize_iata_list(value)
    if not codes:
        raise HTTPException(status_code=400, detail="iata_invalido")
    cleaned: list[str] = []
    for code in codes:
        if len(code) != 3 or not code.isalpha():
            raise HTTPException(status_code=400, detail="iata_invalido")
        cleaned.append(code.upper())
    return cleaned


def _date_range(base: dt.date, before: int, after: int, limit: int = 7) -> list[dt.date]:
    start = base - dt.timedelta(days=max(0, before))
    end = base + dt.timedelta(days=max(0, after))
    days = (end - start).days + 1
    if days <= 0:
        return [base]
    dates = [start + dt.timedelta(days=idx) for idx in range(days)]
    if len(dates) <= limit:
        return dates
    step = max(1, len(dates) // limit)
    sampled = dates[::step][:limit]
    if base not in sampled:
        sampled[-1] = base
    return sorted(set(sampled))


def _time_to_minutes(value: str | None) -> int | None:
    if not value:
        return None
    parts = value.split(":")
    if len(parts) < 2:
        return None
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return None
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return hour * 60 + minute


def _matches_time_window(
    departure: str | None,
    after_value: str | None,
    before_value: str | None,
) -> bool:
    if not after_value and not before_value:
        return True
    dep_minutes = _time_to_minutes(departure)
    if dep_minutes is None:
        return False
    after_minutes = _time_to_minutes(after_value)
    before_minutes = _time_to_minutes(before_value)
    if after_minutes is None and before_minutes is None:
        return True
    if after_minutes is None:
        return dep_minutes <= before_minutes
    if before_minutes is None:
        return dep_minutes >= after_minutes
    if after_minutes <= before_minutes:
        return after_minutes <= dep_minutes <= before_minutes
    return dep_minutes >= after_minutes or dep_minutes <= before_minutes


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _estimate_duration_minutes(origin: str, destination: str) -> int | None:
    origin_airport = get_airport(origin)
    destination_airport = get_airport(destination)
    if not origin_airport or not destination_airport:
        return None
    distance = _haversine_km(
        origin_airport.latitude,
        origin_airport.longitude,
        destination_airport.latitude,
        destination_airport.longitude,
    )
    hours = distance / 780.0 + 0.5
    return max(45, int(hours * 60))


def _fetch_weather(iata: str, date_value: dt.date) -> dict[str, Any] | None:
    airport = get_airport(iata)
    if not airport:
        return None
    params = {
        "latitude": airport.latitude,
        "longitude": airport.longitude,
        "timezone": "auto",
        "start_date": str(date_value),
        "end_date": str(date_value),
        "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
    }
    try:
        resp = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=8)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException:
        return None
    daily = data.get("daily") or {}
    if not daily:
        return None
    temps_max = daily.get("temperature_2m_max") or []
    temps_min = daily.get("temperature_2m_min") or []
    prec = daily.get("precipitation_probability_max") or []
    code = (daily.get("weathercode") or [None])[0]
    return {
        "code": code,
        "temp_max": temps_max[0] if temps_max else None,
        "temp_min": temps_min[0] if temps_min else None,
        "precip_probability": prec[0] if prec else None,
    }


def _score_weather(weather: dict[str, Any] | None) -> float:
    if not weather:
        return 0.5
    temp_max = weather.get("temp_max")
    temp_min = weather.get("temp_min")
    if temp_max is None or temp_min is None:
        return 0.5
    comfort = 1 - min(1, abs((temp_max + temp_min) / 2 - 22) / 18)
    rain = weather.get("precip_probability")
    rain_penalty = 0.0 if rain is None else min(0.4, rain / 250)
    return max(0.0, min(1.0, comfort - rain_penalty))


def _trend_label(best: float, avg: float | None) -> str:
    if avg is None or avg <= 0:
        return "flat"
    ratio = best / avg
    if ratio <= 0.92:
        return "down"
    if ratio >= 1.08:
        return "up"
    return "flat"


def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    total = sum(max(0, value) for value in weights.values())
    if total <= 0:
        return {key: 0 for key in weights}
    return {key: max(0, value) / total for key, value in weights.items()}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _soft_penalty_from_weight(weight: float | None) -> float:
    strength = _clamp(weight if weight is not None else 0.6, 0.2, 1.0)
    return 0.08 + (strength * 0.22)


def _score_candidate(candidate: dict[str, Any], weights: dict[str, float]) -> float:
    price_score = candidate["signals"]["price"]
    speed_score = candidate["signals"]["speed"]
    climate_score = candidate["signals"]["climate"]
    trend_score = candidate["signals"]["trend"]
    novelty_score = candidate["signals"]["novelty"]
    score = (
        weights["price"] * price_score
        + weights["speed"] * speed_score
        + weights["climate"] * climate_score
        + weights["trend"] * trend_score
        + weights["novelty"] * novelty_score
    )
    return round(score * 100, 2)


def _call_ai(candidates: list[dict[str, Any]], locale: str, weights: dict[str, float]) -> tuple[dict[str, Any] | None, str | None]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None, "missing_openai_key"
    system = (
        "Eres un analista de viajes. Debes rankear recomendaciones usando señales "
        "de precio, clima, tendencia y duración. Devuelve SOLO JSON válido."
    )
    user = {
        "locale": locale,
        "weights": weights,
        "candidates": candidates,
        "response_format": {
            "items": [
                {
                    "id": "string",
                    "score": 0,
                    "reason": "string",
                    "tags": ["string"],
                }
            ]
        },
        "rules": [
            "No inventes rutas fuera de candidates",
            "Score 0-100",
            "reason: 1 frase corta",
            "tags: max 3",
        ],
    }
    payload = {
        "model": OPENAI_MODEL,
        "temperature": 0.3,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
    }
    try:
        resp = requests.post(
            OPENAI_ENDPOINT,
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        return None, f"openai_error:{exc}"
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None, "openai_parse_error"
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None, "openai_invalid_json"
    if not isinstance(parsed, dict) or "items" not in parsed:
        return None, "openai_missing_items"
    return parsed, None


def _build_candidates(
    origin_list: list[str],
    destination_list: list[str],
    dates: Iterable[dt.date],
    include_nearby_origins: bool,
    include_nearby_destinations: bool,
    radius_km: int,
    exclude_origins: list[str],
    exclude_destinations: list[str],
) -> list[tuple[str, str, list[tuple[dt.date, Any]]]]:
    origin_candidates = origin_list[:]
    destination_candidates = destination_list[:]
    if include_nearby_origins:
        origin_candidates = expand_airports(origin_list, radius_km, limit_per_seed=6)
    if include_nearby_destinations:
        destination_candidates = expand_airports(destination_list, radius_km, limit_per_seed=6)

    origin_candidates = [code for code in origin_candidates if code not in exclude_origins]
    destination_candidates = [code for code in destination_candidates if code not in exclude_destinations]

    pairs: list[tuple[str, str, list[tuple[dt.date, Any]]]] = []
    pair_limit = 12
    pair_count = 0
    for origin_code in origin_candidates:
        for destination_code in destination_candidates:
            if origin_code == destination_code:
                continue
            if pair_count >= pair_limit:
                return pairs
            flights_by_date: list[tuple[dt.date, Any]] = []
            for date_value in dates:
                try:
                    flights = provider.get_flights(origin_code, destination_code, str(date_value))
                except Exception:
                    flights = []
                for flight in flights:
                    flights_by_date.append((date_value, flight))
            pairs.append((origin_code, destination_code, flights_by_date))
            pair_count += 1
    return pairs


@router.post("")
def recommendations(
    payload: RecommendationRequest | None = Body(default=None),
) -> RecommendationResponse:
    payload = payload or RecommendationRequest()
    origin_value = payload.origin_iata
    destination_value = payload.destination_iata
    travel_date_value = payload.travel_date or payload.date
    if not origin_value:
        raise ApiError(
            status=422,
            code="validation_error",
            message=message_for_code("validation_error"),
            details=[{"loc": ["body", "origin_iata"], "msg": "Field required", "type": "missing"}],
        )
    if not destination_value:
        raise ApiError(
            status=422,
            code="validation_error",
            message=message_for_code("validation_error"),
            details=[{"loc": ["body", "destination_iata"], "msg": "Field required", "type": "missing"}],
        )
    if not travel_date_value:
        raise ApiError(
            status=422,
            code="validation_error",
            message=message_for_code("validation_error"),
            details=[{"loc": ["body", "travel_date"], "msg": "Field required", "type": "missing"}],
        )

    origin_list = _parse_iata_input(origin_value)
    destination_list = _parse_iata_input(destination_value)
    exclude_origin_list = _normalize_iata_list(payload.exclude_origins)
    exclude_destination_list = _normalize_iata_list(payload.exclude_destinations)

    days_before = max(0, payload.days_before or 0)
    days_after = max(0, payload.days_after or 0)
    date_candidates = _date_range(travel_date_value, days_before, days_after, limit=7)

    pairs = _build_candidates(
        origin_list,
        destination_list,
        date_candidates,
        bool(payload.include_nearby_origins),
        bool(payload.include_nearby_destinations),
        payload.radius_km or 150,
        exclude_origin_list,
        exclude_destination_list,
    )

    strict_filters = payload.strict_filters if payload.strict_filters is not None else True
    soft_filters_weight = payload.soft_filters_weight if payload.soft_filters_weight is not None else 0.6
    apply_time_window = bool(payload.depart_after or payload.depart_before)

    candidates: list[dict[str, Any]] = []
    for origin_code, destination_code, flights in pairs:
        if not flights:
            continue

        in_window_flights = [
            (date_value, flight)
            for date_value, flight in flights
            if _matches_time_window(flight.departure_time_local, payload.depart_after, payload.depart_before)
        ]

        soft_penalty = 0.0
        selected_flights = flights
        if apply_time_window:
            if strict_filters:
                selected_flights = in_window_flights
                if not selected_flights:
                    continue
            elif in_window_flights:
                selected_flights = in_window_flights
            else:
                selected_flights = flights
                soft_penalty = _soft_penalty_from_weight(soft_filters_weight)

        best = min(selected_flights, key=lambda item: item[1].price)
        best_date = best[0]
        best_flight = best[1]
        per_date_price: dict[dt.date, float] = {}
        for date_value, flight in selected_flights:
            price = flight.price
            if date_value not in per_date_price or price < per_date_price[date_value]:
                per_date_price[date_value] = price
        avg_price = sum(per_date_price.values()) / len(per_date_price) if per_date_price else None
        weather = _fetch_weather(destination_code, best_date)
        duration_minutes = _estimate_duration_minutes(origin_code, destination_code)
        distance_km = None
        origin_airport = get_airport(origin_code)
        destination_airport = get_airport(destination_code)
        if origin_airport and destination_airport:
            distance_km = round(
                _haversine_km(
                    origin_airport.latitude,
                    origin_airport.longitude,
                    destination_airport.latitude,
                    destination_airport.longitude,
                ),
                1,
            )
        trend = _trend_label(best_flight.price, avg_price)
        signals = {
            "price": 1 / (1 + best_flight.price / 60),
            "speed": 1.0 if duration_minutes is None else max(0.2, 1 - duration_minutes / 600),
            "climate": _score_weather(weather),
            "trend": 0.7 if trend == "down" else 0.5 if trend == "flat" else 0.35,
            "novelty": 0.6,
        }
        candidates.append(
            {
                "id": f"{origin_code}-{destination_code}-{best_date}",
                "origin_iata": origin_code,
                "destination_iata": destination_code,
                "travel_date": str(best_date),
                "departure_time_local": best_flight.departure_time_local,
                "price": best_flight.price,
                "currency": best_flight.currency,
                "avg_price": avg_price,
                "distance_km": distance_km,
                "duration_minutes_est": duration_minutes,
                "weather": weather,
                "trend": trend,
                "source": best_flight.source,
                "signals": signals,
                "soft_penalty": soft_penalty,
            }
        )

    weight_input = payload.weights.model_dump() if payload.weights else {}
    weight_defaults = {"price": 0.4, "speed": 0.2, "climate": 0.2, "trend": 0.1, "novelty": 0.1}
    combined_weights = {**weight_defaults, **{k: float(v) for k, v in weight_input.items()}}
    weights = _normalize_weights(combined_weights)

    ai_payload = [
        {
            "id": item["id"],
            "route": f"{item['origin_iata']} -> {item['destination_iata']}",
            "date": item["travel_date"],
            "price": item["price"],
            "currency": item["currency"],
            "duration_minutes_est": item["duration_minutes_est"],
            "distance_km": item["distance_km"],
            "weather": item["weather"],
            "trend": item["trend"],
            "signals": item["signals"],
        }
        for item in candidates
    ]
    ai_result, ai_error = _call_ai(ai_payload, payload.locale or "es", weights)
    ai_map: dict[str, dict[str, Any]] = {}
    if ai_result:
        for item in ai_result.get("items", []):
            if isinstance(item, dict) and "id" in item:
                ai_map[str(item["id"])] = item

    enriched: list[dict[str, Any]] = []
    for item in candidates:
        ai_item = ai_map.get(item["id"], {})
        score = ai_item.get("score")
        if score is None:
            score = _score_candidate(item, weights)
        penalty = float(item.get("soft_penalty") or 0.0)
        penalized_score = float(score) * (1 - _clamp(penalty, 0.0, 0.7))
        enriched.append(
            {
                **item,
                "score": round(penalized_score, 2),
                "ai_reason": ai_item.get("reason", ""),
                "tags": ai_item.get("tags", []),
            }
        )

    enriched_sorted = sorted(enriched, key=lambda entry: entry["score"], reverse=True)

    return RecommendationResponse(
        query={
            "origin_iata": ",".join(origin_list),
            "destination_iata": ",".join(destination_list),
            "travel_date": str(travel_date_value),
            "days_before": days_before,
            "days_after": days_after,
            "radius_km": payload.radius_km or 150,
            "include_nearby_origins": bool(payload.include_nearby_origins),
            "include_nearby_destinations": bool(payload.include_nearby_destinations),
            "exclude_origins": exclude_origin_list,
            "exclude_destinations": exclude_destination_list,
            "strict_filters": strict_filters,
            "soft_filters_weight": soft_filters_weight,
            "depart_after": payload.depart_after,
            "depart_before": payload.depart_before,
            "weights": weights,
        },
        items=enriched_sorted,
        ai={
            "used": bool(ai_result),
            "model": OPENAI_MODEL if ai_result else None,
            "error": ai_error,
            "reasoning_mode": "ai" if ai_result else "heuristic",
            "summary": (
                "Ranking based on AI model signals."
                if ai_result
                else "Using heuristic ranking based on price, trend, speed, and climate."
            ),
            "active_signals": ["price", "trend", "speed", "climate", "novelty"],
        },
    )
