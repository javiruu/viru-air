from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from app.services.quick_search_ranking import RankedResult


@dataclass(frozen=True)
class DedupeOutcome:
    results: list[RankedResult]
    meta: dict[str, int]


def dedupe_ranked_results(ranked: list[RankedResult]) -> DedupeOutcome:
    if not ranked:
        return DedupeOutcome(results=[], meta={"input_results": 0, "output_results": 0, "deduped_count": 0})

    groups: dict[tuple[str, str, str, str, str, str], list[RankedResult]] = defaultdict(list)
    for item in ranked:
        # Semantic identity heuristic (stronger than time/price/currency only):
        # route + date + departure time + source + currency.
        key = (
            item.origin,
            item.destination,
            str(item.travel_date),
            item.flight.departure_time_local or "",
            item.flight.source,
            item.flight.currency,
        )
        groups[key].append(item)

    deduped: list[RankedResult] = []
    for _, group in groups.items():
        # Keep the best candidate by final ranking criteria.
        winner = min(
            group,
            key=lambda item: (
                item.final_score,
                item.flight.price,
                float(item.score_breakdown.get("distance_penalty_total", 0.0)),
                item.origin,
                item.destination,
            ),
        )
        deduped.append(winner)

    deduped.sort(
        key=lambda item: (
            item.final_score,
            item.flight.price,
            float(item.score_breakdown.get("distance_penalty_total", 0.0)),
            str(item.travel_date),
            item.flight.departure_time_local or "99:99",
            item.origin,
            item.destination,
        )
    )

    return DedupeOutcome(
        results=deduped,
        meta={
            "input_results": len(ranked),
            "output_results": len(deduped),
            "deduped_count": max(0, len(ranked) - len(deduped)),
        },
    )
