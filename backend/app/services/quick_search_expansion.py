from __future__ import annotations

from dataclasses import dataclass

from app.infrastructure.airports_catalog import ExpandedAirportCandidate, expand_side, resolve_seed_airport


@dataclass(frozen=True)
class SideExpansionSummary:
    side: str
    seed_iata: str
    include_nearby_applied: bool
    radius_km_effective: int
    max_candidates_effective: int
    exclusions_applied: list[str]
    total_candidates_before_limit: int
    total_candidates_after_limit: int


@dataclass(frozen=True)
class SideExpansionResult:
    side: str
    candidates: list[ExpandedAirportCandidate]
    summary: SideExpansionSummary


def expand_search_sides(
    *,
    origin_seed_iata: str,
    destination_seed_iata: str,
    include_nearby_origins: bool,
    include_nearby_destinations: bool,
    origin_radius_km: int,
    destination_radius_km: int,
    origin_max_candidates: int,
    destination_max_candidates: int,
    exclude_origins: list[str],
    exclude_destinations: list[str],
) -> tuple[SideExpansionResult, SideExpansionResult]:
    # Explicit seed resolution phase (fail fast, no silent fallback)
    resolve_seed_airport(origin_seed_iata)
    resolve_seed_airport(destination_seed_iata)

    origin_result = _expand_side_with_summary(
        side="origin",
        seed_iata=origin_seed_iata,
        include_nearby=include_nearby_origins,
        radius_km=origin_radius_km,
        max_candidates=origin_max_candidates,
        exclusions=exclude_origins,
    )
    destination_result = _expand_side_with_summary(
        side="destination",
        seed_iata=destination_seed_iata,
        include_nearby=include_nearby_destinations,
        radius_km=destination_radius_km,
        max_candidates=destination_max_candidates,
        exclusions=exclude_destinations,
    )

    if not origin_result.candidates:
        raise ValueError("origin_candidates_empty_after_exclusions")
    if not destination_result.candidates:
        raise ValueError("destination_candidates_empty_after_exclusions")

    return origin_result, destination_result


def _expand_side_with_summary(
    *,
    side: str,
    seed_iata: str,
    include_nearby: bool,
    radius_km: int,
    max_candidates: int,
    exclusions: list[str],
) -> SideExpansionResult:
    exclusions_normalized = sorted({code.strip().upper() for code in exclusions if code and len(code.strip()) == 3})
    seed_upper = seed_iata.strip().upper()

    if seed_upper in exclusions_normalized:
        raise ValueError(f"{side}_seed_excluded")

    expanded_unbounded = expand_side(
        seed_iata=seed_upper,
        include_nearby=include_nearby,
        radius_km=radius_km,
        max_candidates=min(16, max(1, max_candidates * 2)),
        exclusions=exclusions_normalized,
    )

    # Rule: max_candidates counts the FINAL set including seed
    expanded_limited = expanded_unbounded[: max(1, max_candidates)]

    with_side = [
        ExpandedAirportCandidate(
            seed_iata=candidate.seed_iata,
            expanded_iata=candidate.expanded_iata,
            is_seed=candidate.is_seed,
            distance_km=candidate.distance_km,
            candidate_reason=candidate.candidate_reason,
            source_of_expansion=f"{candidate.source_of_expansion}:{side}",
        )
        for candidate in expanded_limited
    ]

    summary = SideExpansionSummary(
        side=side,
        seed_iata=seed_upper,
        include_nearby_applied=include_nearby,
        radius_km_effective=radius_km,
        max_candidates_effective=max(1, max_candidates),
        exclusions_applied=exclusions_normalized,
        total_candidates_before_limit=len(expanded_unbounded),
        total_candidates_after_limit=len(with_side),
    )

    return SideExpansionResult(side=side, candidates=with_side, summary=summary)
