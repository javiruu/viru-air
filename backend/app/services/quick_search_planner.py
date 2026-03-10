from __future__ import annotations

from dataclasses import dataclass

from app.infrastructure.airports_catalog import ExpandedAirportCandidate


@dataclass(frozen=True)
class PairPlanItem:
    origin_iata: str
    destination_iata: str
    origin_seed_iata: str
    destination_seed_iata: str
    origin_distance_km: float
    destination_distance_km: float
    is_origin_seed: bool
    is_destination_seed: bool


def build_pair_plan(
    origin_expanded: list[ExpandedAirportCandidate],
    destination_expanded: list[ExpandedAirportCandidate],
    *,
    max_pairs: int,
    max_requests: int,
    date_count: int,
) -> tuple[list[PairPlanItem], dict[str, int | bool]]:
    rows: list[tuple[tuple[int, float, float, str, str], PairPlanItem]] = []

    for origin in origin_expanded:
      for destination in destination_expanded:
        if origin.expanded_iata == destination.expanded_iata:
          continue

        seed_rank = (0 if origin.is_seed else 1) + (0 if destination.is_seed else 1)
        distance_sum = float(origin.distance_km) + float(destination.distance_km)
        distance_max = max(float(origin.distance_km), float(destination.distance_km))

        item = PairPlanItem(
            origin_iata=origin.expanded_iata,
            destination_iata=destination.expanded_iata,
            origin_seed_iata=origin.seed_iata,
            destination_seed_iata=destination.seed_iata,
            origin_distance_km=float(origin.distance_km),
            destination_distance_km=float(destination.distance_km),
            is_origin_seed=origin.is_seed,
            is_destination_seed=destination.is_seed,
        )
        key = (seed_rank, distance_sum, distance_max, origin.expanded_iata, destination.expanded_iata)
        rows.append((key, item))

    rows.sort(key=lambda row: row[0])

    date_count = max(1, date_count)
    max_pairs_by_requests = max(1, max_requests // date_count)
    effective_max_pairs = max(1, min(max_pairs, max_pairs_by_requests))

    total_pairs = len(rows)
    selected = [row[1] for row in rows[:effective_max_pairs]]

    return selected, {
        "total_pairs": total_pairs,
        "selected_pairs": len(selected),
        "effective_max_pairs": effective_max_pairs,
        "max_pairs_by_requests": max_pairs_by_requests,
        "truncated": total_pairs > len(selected),
    }
