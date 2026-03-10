from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from app.domain.entities import ProviderFlight
from app.services.quick_search_planner import PairPlanItem


@dataclass(frozen=True)
class RankedResult:
    origin: str
    destination: str
    travel_date: dt.date
    flight: ProviderFlight
    final_score: float
    score_breakdown: dict[str, float | str]
    origin_seed_iata: str
    destination_seed_iata: str
    origin_is_seed: bool
    destination_is_seed: bool
    origin_distance_from_seed_km: float
    destination_distance_from_seed_km: float
    pair_category: str
    discovery_explanation: str


def rank_quick_search_results(
    rows: list[tuple[str, str, dt.date, ProviderFlight]],
    planned_pairs: list[PairPlanItem],
    *,
    soft_filters_weight: float = 0.6,
) -> list[RankedResult]:
    if not rows:
        return []

    pair_by_key = {(pair.origin_iata, pair.destination_iata): pair for pair in planned_pairs}
    min_price = min(max(0.0, float(row[3].price)) for row in rows)

    ranked: list[RankedResult] = []
    soft_weight_factor = max(0.0, min(2.0, soft_filters_weight)) / 0.6

    for origin, destination, travel_date, flight in rows:
        pair = pair_by_key.get((origin, destination))
        if pair is None:
            continue

        price_value = max(0.0, float(flight.price))
        price_component = price_value - min_price

        origin_seed_penalty = (0.0 if pair.origin_is_seed else 12.0) * soft_weight_factor
        destination_seed_penalty = (0.0 if pair.destination_is_seed else 12.0) * soft_weight_factor

        origin_distance_penalty = pair.origin_distance_from_seed_km * 0.06 * soft_weight_factor
        destination_distance_penalty = pair.destination_distance_from_seed_km * 0.06 * soft_weight_factor
        distance_penalty_total = origin_distance_penalty + destination_distance_penalty

        pair_category_bias = {
            "seed-seed": 0.0,
            "seed-nearby": 8.0,
            "nearby-seed": 8.0,
            "nearby-nearby": 22.0,
        }.get(pair.pair_reason, 30.0) * soft_weight_factor

        final_score = (
            price_component
            + origin_seed_penalty
            + destination_seed_penalty
            + distance_penalty_total
            + pair_category_bias
        )

        discovery_explanation = {
            "seed-seed": "direct_seed",
            "seed-nearby": "nearby_destination",
            "nearby-seed": "nearby_origin",
            "nearby-nearby": "nearby_both_sides",
        }.get(pair.pair_reason, "unknown")

        ranked.append(
            RankedResult(
                origin=origin,
                destination=destination,
                travel_date=travel_date,
                flight=flight,
                final_score=round(final_score, 4),
                score_breakdown={
                    "final_score": round(final_score, 4),
                    "price_component": round(price_component, 4),
                    "origin_seed_penalty": round(origin_seed_penalty, 4),
                    "destination_seed_penalty": round(destination_seed_penalty, 4),
                    "distance_penalty_total": round(distance_penalty_total, 4),
                    "pair_category": pair.pair_reason,
                    "soft_filters_weight_applied": round(soft_weight_factor, 4),
                },
                origin_seed_iata=pair.origin_seed_iata,
                destination_seed_iata=pair.destination_seed_iata,
                origin_is_seed=pair.origin_is_seed,
                destination_is_seed=pair.destination_is_seed,
                origin_distance_from_seed_km=pair.origin_distance_from_seed_km,
                destination_distance_from_seed_km=pair.destination_distance_from_seed_km,
                pair_category=pair.pair_reason,
                discovery_explanation=discovery_explanation,
            )
        )

    ranked.sort(
        key=lambda item: (
            item.final_score,
            item.flight.price,
            item.score_breakdown["distance_penalty_total"],
            str(item.travel_date),
            item.flight.departure_time_local or "99:99",
            item.origin,
            item.destination,
        )
    )
    return ranked
