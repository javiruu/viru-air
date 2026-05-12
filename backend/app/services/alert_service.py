from datetime import timedelta

from app.core.time import as_utc_aware, utc_now, utc_now_naive

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.domain.schemas import AlertRuleIn, AlertRuleUpdateIn
from app.domain.vocabulary import DELIVERY_STATUS_QUEUED
from app.infrastructure.db.models import AlertRule, FlightWatch, NotificationEvent, PriceSnapshot


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
    return list(db.execute(query).all())


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


def evaluate_rules_for_watch(db: Session, watch_id: str) -> list[NotificationEvent]:
    snapshots = _latest_snapshots(db, watch_id)
    if not snapshots:
        return []
    latest = snapshots[0]
    previous = snapshots[1] if len(snapshots) > 1 else None
    rules = list_rules(db, watch_id)
    created: list[NotificationEvent] = []

    for rule in rules:
        if not rule.enabled:
            continue
        if _cooldown_active(db, rule.id, rule.cooldown_minutes):
            continue

        trigger = False
        message = ""
        previous_price = float(previous.raw_price) if previous else None
        latest_price = float(latest.raw_price)

        if rule.min_change_pct is not None and previous_price not in (None, 0):
            delta_pct = abs((latest_price - previous_price) / previous_price) * 100.0
            if delta_pct < float(rule.min_change_pct):
                continue

        if rule.rule_type == "threshold_low" and rule.threshold_value is not None:
            if latest_price <= float(rule.threshold_value) and (
                not previous or previous_price > float(rule.threshold_value)
            ):
                trigger = True
                message = (
                    f"Precio bajo: {latest_price:.2f} {latest.raw_currency} "
                    f"(umbral {float(rule.threshold_value):.2f})."
                )
        elif rule.rule_type == "threshold_high" and rule.threshold_value is not None:
            if latest_price >= float(rule.threshold_value) and (
                not previous or previous_price < float(rule.threshold_value)
            ):
                trigger = True
                message = (
                    f"Precio alto: {latest_price:.2f} {latest.raw_currency} "
                    f"(umbral {float(rule.threshold_value):.2f})."
                )
        elif rule.rule_type == "every_change":
            if previous and previous_price != latest_price:
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
            group_reason = rule.rule_type
            group_bucket = utc_now_naive().strftime("%Y%m%d%H%M")
            dedupe_key = f"{watch_id}:{rule.id}:{group_reason}:{channel}:{group_bucket}"
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
                created.append(existing)
                continue

            event = NotificationEvent(
                rule_id=rule.id,
                channel=channel,
                delivery_status=DELIVERY_STATUS_QUEUED,
                attempts=0,
                next_attempt_at=utc_now_naive(),
                dedupe_key=dedupe_key,
                group_key=f"{watch_id}:{rule.id}:{group_reason}:{group_bucket}",
                group_reason=group_reason,
                is_digest=False,
                grouped_count=1,
                message=message,
            )
            db.add(event)
            created.append(event)

    if created:
        db.commit()
        for event in created:
            db.refresh(event)
    return created
