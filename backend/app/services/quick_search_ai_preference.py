from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger(__name__)

OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TIMEOUT_SECONDS = float(os.environ.get("QUICK_SEARCH_AI_PREFERENCE_TIMEOUT_SECONDS", "8"))


@dataclass(frozen=True)
class QuickSearchAiPreferenceResult:
    enabled: bool
    source: str
    preferred_result_id: str | None
    fallback_used: bool
    reason: str | None = None
    failure_reason: str | None = None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if parsed != parsed:  # NaN
        return default
    return parsed


def _heuristic_preference(results: list[dict[str, Any]]) -> QuickSearchAiPreferenceResult:
    if not results:
        return QuickSearchAiPreferenceResult(
            enabled=False,
            source="heuristic",
            preferred_result_id=None,
            fallback_used=True,
            failure_reason="no_results",
        )

    min_price = min(_safe_float(item.get("price_total", item.get("price")), 0.0) for item in results)

    def score(item: dict[str, Any]) -> tuple[float, float, float, float, str]:
        price_value = _safe_float(item.get("price_total", item.get("price")), 0.0)
        ranking_score = _safe_float(item.get("ranking_score"), 999999.0)
        duration_total = _safe_float(item.get("duration_total_min"), 999999.0)
        distance_penalty = _safe_float(item.get("origin_distance_from_seed_km"), 0.0) + _safe_float(
            item.get("destination_distance_from_seed_km"), 0.0
        )
        stale_penalty = 35.0 if bool(item.get("stale_data")) else 0.0
        price_delta = max(0.0, price_value - min_price)
        total = ranking_score + (price_delta * 0.18) + (duration_total * 0.01) + (distance_penalty * 0.02) + stale_penalty
        result_id = str(item.get("result_id") or "")
        return (round(total, 4), price_value, duration_total, distance_penalty, result_id)

    preferred = min(results, key=score)
    route = f'{preferred.get("origin", "")}-{preferred.get("destination", "")}'.strip("-")
    return QuickSearchAiPreferenceResult(
        enabled=True,
        source="heuristic",
        preferred_result_id=str(preferred.get("result_id") or ""),
        fallback_used=True,
        reason=f"Mejor equilibrio entre precio, duracion y cercania para {route}.",
    )


def _build_candidate_payload(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in results:
        candidates.append(
            {
                "id": item.get("result_id"),
                "origin": item.get("origin"),
                "destination": item.get("destination"),
                "travel_date": item.get("travel_date"),
                "departure_time_local": item.get("departure_time_local"),
                "price_total": item.get("price_total", item.get("price")),
                "currency": item.get("currency"),
                "duration_total_min": item.get("duration_total_min"),
                "ranking_score": item.get("ranking_score"),
                "origin_distance_from_seed_km": item.get("origin_distance_from_seed_km"),
                "destination_distance_from_seed_km": item.get("destination_distance_from_seed_km"),
                "pair_category": item.get("pair_category"),
                "stale_data": bool(item.get("stale_data")),
            }
        )
    return candidates


def _call_openai_for_preference(
    results: list[dict[str, Any]],
    *,
    query_context: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None, "missing_openai_key"

    payload = {
        "model": OPENAI_MODEL,
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Eres un analista de quick-search de vuelos. Elige exactamente un resultado preferible por equilibrio "
                    "de precio, duracion, frescura y cercania a la ruta buscada. Devuelve SOLO JSON valido."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "query_context": query_context,
                        "candidates": _build_candidate_payload(results),
                        "response_format": {
                            "preferred_result_id": "string",
                            "reason": "string",
                        },
                        "rules": [
                            "preferred_result_id debe existir en candidates",
                            "elige solo uno",
                            "reason maximo 120 caracteres",
                        ],
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    }
    try:
        response = requests.post(
            OPENAI_ENDPOINT,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            data=json.dumps(payload, ensure_ascii=False),
            timeout=OPENAI_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        return None, f"openai_error:{exc.__class__.__name__}"

    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None, "openai_parse_error"

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None, "openai_invalid_json"

    if not isinstance(parsed, dict):
        return None, "openai_invalid_shape"
    return parsed, None


def select_quick_search_ai_preference(
    results: list[dict[str, Any]],
    *,
    query_context: dict[str, Any],
) -> QuickSearchAiPreferenceResult:
    heuristic = _heuristic_preference(results)
    if not heuristic.enabled:
        return heuristic

    parsed, error = _call_openai_for_preference(results, query_context=query_context)
    if error:
        logger.info("quick_search ai preference fallback reason=%s preferred_result_id=%s", error, heuristic.preferred_result_id)
        return QuickSearchAiPreferenceResult(
            enabled=heuristic.enabled,
            source="heuristic",
            preferred_result_id=heuristic.preferred_result_id,
            fallback_used=True,
            reason=heuristic.reason,
            failure_reason=error,
        )

    if parsed is None:
        return QuickSearchAiPreferenceResult(
            enabled=heuristic.enabled,
            source="heuristic",
            preferred_result_id=heuristic.preferred_result_id,
            fallback_used=True,
            reason=heuristic.reason,
            failure_reason="openai_missing_payload",
        )

    preferred_result_id = parsed.get("preferred_result_id")
    if not isinstance(preferred_result_id, str) or not preferred_result_id.strip():
        return QuickSearchAiPreferenceResult(
            enabled=heuristic.enabled,
            source="heuristic",
            preferred_result_id=heuristic.preferred_result_id,
            fallback_used=True,
            reason=heuristic.reason,
            failure_reason="openai_missing_preferred_result_id",
        )

    valid_ids = {str(item.get("result_id") or "") for item in results}
    preferred_result_id = preferred_result_id.strip()
    if preferred_result_id not in valid_ids:
        return QuickSearchAiPreferenceResult(
            enabled=heuristic.enabled,
            source="heuristic",
            preferred_result_id=heuristic.preferred_result_id,
            fallback_used=True,
            reason=heuristic.reason,
            failure_reason="openai_unknown_preferred_result_id",
        )

    reason = parsed.get("reason")
    normalized_reason = reason.strip() if isinstance(reason, str) and reason.strip() else heuristic.reason
    return QuickSearchAiPreferenceResult(
        enabled=True,
        source="ai",
        preferred_result_id=preferred_result_id,
        fallback_used=False,
        reason=normalized_reason,
        failure_reason=None,
    )
