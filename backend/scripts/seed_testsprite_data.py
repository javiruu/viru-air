from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.infrastructure.db.models import AlertRule, FlightWatch, NotificationEvent, PriceSnapshot, User
from app.infrastructure.db.seed import ensure_seed_users
from app.infrastructure.db.session import SessionLocal


@dataclass(frozen=True)
class SeedRoute:
    origin: str
    destination: str
    travel_date: date
    target_price: Decimal
    base_price: Decimal


def _ensure_watch(db, user_id: str, route: SeedRoute) -> tuple[FlightWatch, bool]:
    existing = db.scalar(
        select(FlightWatch).where(
            FlightWatch.user_id == user_id,
            FlightWatch.origin_iata == route.origin,
            FlightWatch.destination_iata == route.destination,
            FlightWatch.travel_date_local == route.travel_date,
        )
    )
    if existing:
        return existing, False
    watch = FlightWatch(
        user_id=user_id,
        origin_iata=route.origin,
        destination_iata=route.destination,
        travel_date_local=route.travel_date,
        target_price=route.target_price,
        status="active",
    )
    db.add(watch)
    db.flush()
    return watch, True


def _ensure_snapshots(db, watch_id: str, base_price: Decimal) -> int:
    existing = list(db.scalars(select(PriceSnapshot).where(PriceSnapshot.watch_id == watch_id)))
    if len(existing) >= 5:
        return 0
    created = 0
    now = datetime.now(timezone.utc)
    for idx in range(5):
        captured_at = now - timedelta(days=5 - idx, hours=idx)
        price = base_price + Decimal(idx * 3) - Decimal(4)
        db.add(
            PriceSnapshot(
                watch_id=watch_id,
                captured_at_utc=captured_at,
                departure_time_local=f"{7 + idx:02d}:30",
                raw_price=price,
                raw_currency="EUR",
                provider="seed-testsprite",
                is_stale=False,
            )
        )
        created += 1
    return created


def _ensure_rules_and_events(db, watch_id: str) -> int:
    existing_rules = list(db.scalars(select(AlertRule).where(AlertRule.watch_id == watch_id)))
    if existing_rules:
        return 0
    rules = [
        AlertRule(
            watch_id=watch_id,
            rule_type="threshold_low",
            threshold_value=Decimal("49.90"),
            notify_on_every_change=False,
            cooldown_minutes=60,
            enabled=True,
        ),
        AlertRule(
            watch_id=watch_id,
            rule_type="threshold_high",
            threshold_value=Decimal("120.00"),
            notify_on_every_change=False,
            cooldown_minutes=120,
            enabled=True,
        ),
        AlertRule(
            watch_id=watch_id,
            rule_type="every_change",
            threshold_value=None,
            notify_on_every_change=True,
            cooldown_minutes=30,
            enabled=True,
        ),
    ]
    for rule in rules:
        db.add(rule)
    db.flush()
    for rule in rules:
        db.add(
            NotificationEvent(
                rule_id=rule.id,
                channel="in_app",
                delivery_status="queued",
                message=f"Seed event for {rule.rule_type}",
                created_at=datetime.now(timezone.utc) - timedelta(hours=1),
            )
        )
    return len(rules)


def main() -> None:
    ensure_seed_users()
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == "user@viru.local"))
        if not user:
            raise RuntimeError("User user@viru.local not found after seed.")

        today = date.today()
        routes = [
            SeedRoute("MAD", "BCN", today + timedelta(days=14), Decimal("45.00"), Decimal("58.00")),
            SeedRoute("MAD", "DUB", today + timedelta(days=21), Decimal("59.00"), Decimal("72.00")),
            SeedRoute("LHR", "MAD", today + timedelta(days=28), Decimal("69.00"), Decimal("84.00")),
        ]

        created_watches = 0
        created_snapshots = 0
        created_rules = 0

        for route in routes:
            watch, was_created = _ensure_watch(db, user.id, route)
            if was_created:
                created_watches += 1
            created_snapshots += _ensure_snapshots(db, watch.id, route.base_price)
            created_rules += _ensure_rules_and_events(db, watch.id)

        db.commit()
        print(
            "Seed complete:",
            f"watches={created_watches}",
            f"snapshots={created_snapshots}",
            f"rules={created_rules}",
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
