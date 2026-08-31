import logging
from datetime import timedelta

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.time import as_utc_aware, utc_now, utc_now_naive
from app.domain.entities import ProviderFetchResult
from app.domain.schemas import AlertRuleIn, AlertRuleUpdateIn
from app.domain.vocabulary import DELIVERY_STATUS_QUEUED
from app.infrastructure.db.models import AlertRule, FlightWatch, NotificationEvent, PriceSnapshot
from app.infrastructure.providers.flight_provider import MultiSourceFlightProvider
from app.services.watchlist_snapshots import select_canonical_refresh_flight

_ALERT_REVALIDATION_TIMEOUT_MS = 8000
_provider = MultiSourceFlightProvider()
logger = logging.getLogger(__name__)


def create_rule(db: Session, payload: AlertRuleIn) -> AlertRule:
    rule = AlertRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def list_rules(db: Session, watch_id: str) -> list[AlertRule]:
    return list(db.scalars(select(AlertRule).where(AlertRule.watch_id == watch_id)))


def update_rule(db: Session, rule: AlertRule, payload: AlertRuleUpdateIn) -> AlertRule:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def delete_rule(db: Session, rule: AlertRule) -> None:
    db.delete(rule)
    db.commit()


def list_events(
    db: Session,
    user_id: str,
    watch_id: str | None = None,
    limit: int = 50,
) -> list[tuple[NotificationEvent, AlertRule, FlightWatch]]:
    query = (
        select(NotificationEvent, AlertRule, FlightWatch)
        .join(AlertRule, NotificationEvent.rule_id == AlertRule.id)
        .join(FlightWatch, AlertRule.watch_id == FlightWatch.id)
        .where(FlightWatch.user_id == user_id)
        .order_by(desc(NotificationEvent.created_at), desc(NotificationEvent.id))
        .limit(limit)
    )
    if watch_id:
        query = query.where(AlertRule.watch_id == watch_id)
    return list(db.execute(query).tuples().all())


def _latest_snapshots(db: Session, watch_id: str, limit: int = 2) -> list[PriceSnapshot]:
    rows = db.scalars(
        select(PriceSnapshot)
        .where(PriceSnapshot.watch_id == watch_id)
        .order_by(desc(PriceSnapshot.captured_at_utc), desc(PriceSnapshot.id))
        .limit(limit)
    ).all()
    return list(rows)


def _cooldown_active(db: Session, rule_id: str, cooldown_minutes: int) -> bool:
    last_event = db.scalar(
        select(NotificationEvent)
        .where(NotificationEvent.rule_id == rule_id)
        .order_by(desc(NotificationEvent.created_at), desc(NotificationEvent.id))
        .limit(1)
    )
    if not last_event:
        return False
    cutoff = as_utc_aware(last_event.created_at + timedelta(minutes=cooldown_minutes))
    return utc_now() < cutoff


def _build_deduped_event(
    db: Session,
    *,
    watch_id: str,
    rule_id: str,
    channel: str,
    group_reason: str,
    message: str,
) -> NotificationEvent:
    group_bucket = utc_now_naive().strftime("%Y%m%d%H%M")
    dedupe_key = f"{watch_id}:{rule_id}:{group_reason}:{channel}:{group_bucket}"
    existing = db.scalar(
        select(NotificationEvent)
        .where(NotificationEvent.dedupe_key == dedupe_key)
        .order_by(desc(NotificationEvent.created_at), desc(NotificationEvent.id))
        .limit(1)
    )
    if existing:
        existing.grouped_count = max(1, existing.grouped_count) + 1
        existing.is_digest = existing.grouped_count > 1
        existing.group_reason = group_reason
        existing.message = f"Resumen de {existing.grouped_count} avisos ({group_reason})."
        db.add(existing)
        return existing

    event = NotificationEvent(
        rule_id=rule_id,
        channel=channel,
        delivery_status=DELIVERY_STATUS_QUEUED,
        attempts=0,
        next_attempt_at=utc_now_naive(),
        dedupe_key=dedupe_key,
        group_key=f"{watch_id}:{rule_id}:{group_reason}:{group_bucket}",
        group_reason=group_reason,
        is_digest=False,
        grouped_count=1,
        message=message,
    )
    db.add(event)
    return event


def _revalidate_latest_snapshot(
    db: Session,
    *,
    watch: FlightWatch,
    provider_client: MultiSourceFlightProvider | None = None,
) -> tuple[PriceSnapshot | None, str | None]:
    provider_client = provider_client or _provider
    try:
        provider_result = provider_client.get_flights(
            watch.origin_iata,
            watch.destination_iata,
            str(watch.travel_date_local),
            timeout_ms=_ALERT_REVALIDATION_TIMEOUT_MS,
        )
    except Exception:
        return None, "provider_error"

    flights = provider_result.flights if isinstance(provider_result, ProviderFetchResult) else provider_result
    canonical_flight = select_canonical_refresh_flight(flights)
    if canonical_flight is None:
        return None, "no_flights"

    snapshot = PriceSnapshot(
        watch_id=watch.id,
        captured_at_utc=utc_now_naive().replace(microsecond=0),
        departure_time_local=canonical_flight.departure_time_local,
        raw_price=canonical_flight.price,
        raw_currency=canonical_flight.currency,
        provider=canonical_flight.source,
        is_stale=False,
    )
    db.add(snapshot)
    db.flush()
    return snapshot, None


def evaluate_rules_for_watch(
    db: Session,
    watch_id: str,
    *,
    attempt_revalidation: bool = True,
    provider_client: MultiSourceFlightProvider | None = None,
) -> list[NotificationEvent]:
    watch = db.get(FlightWatch, watch_id)
    if watch is None:
        return []

    snapshots = _latest_snapshots(db, watch_id)
    if not snapshots:
        return []
    latest = snapshots[0]
    previous = snapshots[1] if len(snapshots) > 1 else None
    rules = list_rules(db, watch_id)
    created: list[NotificationEvent] = []

    if latest.is_stale:
        if not attempt_revalidation:
            return []

        stale_snapshot_price = float(latest.raw_price)
        revalidated_snapshot, revalidation_error = _revalidate_latest_snapshot(
            db,
            watch=watch,
            provider_client=provider_client,
        )
        if revalidated_snapshot is None:
            if revalidation_error == "provider_error":
                logger.warning(
                    "alert_revalidation_failed watch_id=%s revalidation_success_count=0 "
                    "revalidation_price_changed_count=0 provider_error_count=1",
                    watch_id,
                )
                for rule in rules:
                    if not rule.enabled:
                        continue
                    if _cooldown_active(db, rule.id, rule.cooldown_minutes):
                        continue
                    created.append(
                        _build_deduped_event(
                            db,
                            watch_id=watch_id,
                            rule_id=rule.id,
                            channel="in_app",
                            group_reason="revalidation_failed",
                            message="No disparamos la alerta: no pudimos revalidar el precio actual.",
                        )
                    )
                if created:
                    db.commit()
                    for event in created:
                        db.refresh(event)
            return created

        revalidated_price = float(revalidated_snapshot.raw_price)
        logger.info(
            "alert_revalidation_completed watch_id=%s revalidation_success_count=1 "
            "revalidation_price_changed_count=%d provider_error_count=0",
            watch_id,
            int(revalidated_price != stale_snapshot_price),
        )
        previous = latest
        latest = revalidated_snapshot

    for rule in rules:
        if not rule.enabled:
            continue
        if _cooldown_active(db, rule.id, rule.cooldown_minutes):
            continue

        trigger = False
        message = ""
        previous_price = (
            float(previous.raw_price)
            if previous is not None and previous.raw_price is not None
            else None
        )
        latest_price = float(latest.raw_price)

        min_change_pct = rule.min_change_pct
        if min_change_pct is not None and previous_price is not None and previous_price != 0:
            delta_pct = abs((latest_price - previous_price) / previous_price) * 100.0
            if delta_pct < float(min_change_pct):
                continue

        if rule.rule_type == "threshold_low" and rule.threshold_value is not None:
            if latest_price <= float(rule.threshold_value) and (
                previous_price is None or previous_price > float(rule.threshold_value)
            ):
                trigger = True
                message = (
                    f"Precio bajo: {latest_price:.2f} {latest.raw_currency} "
                    f"(umbral {float(rule.threshold_value):.2f})."
                )
        elif rule.rule_type == "threshold_high" and rule.threshold_value is not None:
            if latest_price >= float(rule.threshold_value) and (
                previous_price is None or previous_price < float(rule.threshold_value)
            ):
                trigger = True
                message = (
                    f"Precio alto: {latest_price:.2f} {latest.raw_currency} "
                    f"(umbral {float(rule.threshold_value):.2f})."
                )
        elif (
            rule.rule_type == "every_change"
            and previous_price is not None
            and previous_price != latest_price
        ):
            delta = latest_price - previous_price
            trigger = True
            message = (
                f"Cambio de precio: {previous_price:.2f} -> {latest_price:.2f} "
                f"{latest.raw_currency} ({delta:+.2f})."
            )

        if not trigger:
            continue

        channels = ["in_app"]
        if rule.notify_on_every_change and rule.rule_type != "every_change":
            channels.append("email")

        for channel in channels:
            created.append(
                _build_deduped_event(
                    db,
                    watch_id=watch_id,
                    rule_id=rule.id,
                    channel=channel,
                    group_reason=rule.rule_type,
                    message=message,
                )
            )

    if created:
        db.commit()
        for event in created:
            db.refresh(event)
    return created
