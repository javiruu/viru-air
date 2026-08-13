from __future__ import annotations

import datetime
from dataclasses import dataclass

from app.infrastructure.db.models import HotelRateSnapshot


@dataclass
class ParitySignal:
    """Aggregated parity data for a single stay group (matching check-in/out, guests, currency)."""

    check_in: datetime.date
    check_out: datetime.date
    guests: int
    currency: str
    provider_count: int
    lowest_price: float | None = None
    highest_price: float | None = None
    average_price: float | None = None
    spread_amount: float | None = None
    spread_percent: float | None = None
    is_parity_broken: bool = False
    status: str = "info"
    label: str = "limited"

    @classmethod
    def from_rates(cls, rates: list[HotelRateSnapshot]) -> ParitySignal | None:
        eligible_rates = [rate for rate in rates if rate.availability_status not in {"unavailable", "stale"}]
        if not eligible_rates:
            return None

        first = eligible_rates[0]
        providers: set[str] = set()
        amounts: list[float] = []

        for rate in eligible_rates:
            providers.add(rate.provider)
            amounts.append(float(rate.amount))

        provider_count = len(providers)

        if provider_count < 2 or len(amounts) < 2:
            return cls(
                check_in=first.check_in,
                check_out=first.check_out,
                guests=first.guests,
                currency=first.currency,
                provider_count=provider_count,
                is_parity_broken=False,
                status="info",
                label="limited",
            )

        sorted_amounts = sorted(amounts)
        lowest = sorted_amounts[0]
        highest = sorted_amounts[-1]
        average = round(sum(amounts) / len(amounts), 2)
        spread_amount = round(highest - lowest, 2)
        spread_percent = round((spread_amount / lowest) * 100, 1)

        if spread_percent >= 20:
            status = "error"
            label = "breach"
            is_parity_broken = True
        elif spread_percent >= 10:
            status = "warning"
            label = "tensioned"
            is_parity_broken = True
        else:
            status = "success"
            label = "stable"
            is_parity_broken = False

        return cls(
            check_in=first.check_in,
            check_out=first.check_out,
            guests=first.guests,
            currency=first.currency,
            provider_count=provider_count,
            lowest_price=lowest,
            highest_price=highest,
            average_price=average,
            spread_amount=spread_amount,
            spread_percent=spread_percent,
            is_parity_broken=is_parity_broken,
            status=status,
            label=label,
        )


class HotelParityService:
    """Computes parity signals from hotel rate snapshots."""

    @staticmethod
    def compute_parity(rates: list[HotelRateSnapshot]) -> list[ParitySignal]:
        """Group rates by stay parameters and compute a parity signal per group.

        Returns signals sorted by check_in descending (most recent first).
        """
        groups: dict[tuple[datetime.date, datetime.date, int, str], list[HotelRateSnapshot]] = {}
        for rate in rates:
            if rate.availability_status in {"unavailable", "stale"}:
                continue
            key = (rate.check_in, rate.check_out, rate.guests, rate.currency)
            groups.setdefault(key, []).append(rate)

        signals: list[ParitySignal] = []
        for group_rates in groups.values():
            signal = ParitySignal.from_rates(group_rates)
            if signal is not None:
                signals.append(signal)

        signals.sort(key=lambda s: (s.check_in, s.check_out), reverse=True)
        return signals

    @staticmethod
    def latest_parity(rates: list[HotelRateSnapshot]) -> ParitySignal | None:
        """Return the most recent parity signal, or None if no rates."""
        signals = HotelParityService.compute_parity(rates)
        return signals[0] if signals else None
