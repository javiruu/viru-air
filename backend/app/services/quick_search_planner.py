from __future__ import annotations

from dataclasses import dataclass

from app.infrastructure.airports_catalog import ExpandedAirportCandidate


@dataclass(frozen=True)
class PairPlanItem:
    origin_iata: str
    destination_iata: str
    origin_seed_iata: str
    destination_seed_iata: str
    origin_is_seed: bool
    destination_is_seed: bool
    origin_distance_from_seed_km: float
    destination_distance_from_seed_km: float
    pair_priority_score: float
    pair_reason: str


def _pair_reason(origin_is_seed: bool, destination_is_seed: bool) -> str:
    if origin_is_seed and destination_is_seed:
        return "seed-seed"
    if origin_is_seed and not destination_is_seed:
        return "seed-nearby"
    if not origin_is_seed and destination_is_seed:
        return "nearby-seed"
    return "nearby-nearby"


def _pair_priority(origin: ExpandedAirportCandidate, destination: ExpandedAirportCandidate) -> float:
    seed_penalty = (0 if origin.is_seed else 1) + (0 if destination.is_seed else 1)
    distance_sum = float(origin.distance_km) + float(destination.distance_km)
    distance_max = max(float(origin.distance_km), float(destination.distance_km))
    # Lower score is better; deterministic and explainable.
    return (seed_penalty * 1_000_000.0) + (distance_sum * 1000.0) + distance_max


def build_pair_plan(
    origin_expanded: list[ExpandedAirportCandidate],
    destination_expanded: list[ExpandedAirportCandidate],
    *,
    max_pairs: int,
    max_requests: int,
    date_count: int,
) -> tuple[list[PairPlanItem], dict[str, int | bool]]:
    rows: list[tuple[tuple[float, str, str], PairPlanItem]] = []
    seen_pairs: set[tuple[str, str]] = set()

    for origin in origin_expanded:
        for destination in destination_expanded:
            if origin.expanded_iata == destination.expanded_iata:
                continue

            pair_key = (origin.expanded_iata, destination.expanded_iata)
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            priority = _pair_priority(origin, destination)
            item = PairPlanItem(
                origin_iata=origin.expanded_iata,
                destination_iata=destination.expanded_iata,
                origin_seed_iata=origin.seed_iata,
                destination_seed_iata=destination.seed_iata,
                origin_is_seed=origin.is_seed,
                destination_is_seed=destination.is_seed,
                origin_distance_from_seed_km=float(origin.distance_km),
                destination_distance_from_seed_km=float(destination.distance_km),
                pair_priority_score=priority,
                pair_reason=_pair_reason(origin.is_seed, destination.is_seed),
            )
            rows.append(((priority, origin.expanded_iata, destination.expanded_iata), item))

    rows.sort(key=lambda row: row[0])

    # max_pairs applies to base O×D pairs only (not multiplied by flex dates)
    effective_max_pairs = max(1, max_pairs)
    total_pairs = len(rows)
    selected = [row[1] for row in rows[:effective_max_pairs]]

    # Kept for next execution cycle visibility; not used for truncation in this phase.
    date_count = max(1, date_count)
    max_pairs_by_requests = max(1, max_requests // date_count)

    return selected, {
        "total_pairs": total_pairs,
        "selected_pairs": len(selected),
        "effective_max_pairs": effective_max_pairs,
        "max_pairs_by_requests": max_pairs_by_requests,
        "truncated": total_pairs > len(selected),
    }
