from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sys
import tempfile
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Iterator
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from passlib.context import CryptContext
from sqlalchemy import and_, column, delete, func, inspect, or_, select, table, text, update
from sqlalchemy.orm import Session, sessionmaker

# Support both ``python scripts/hotel_demo_seed.py`` and module/test imports.
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.hotels.ingestion import HotelIngestionService  # noqa: E402
from app.infrastructure.db.models import (  # noqa: E402
    HotelAlertEvent,
    HotelAlertRule,
    HotelNotificationDelivery,
    HotelProviderAlias,
    HotelProviderLatencyAggregate,
    HotelProviderRun,
    HotelProperty,
    HotelRateSnapshot,
    HotelStayOffer,
    HotelTrackedOffer,
    HotelUserStayWatch,
    HotelWatchlistItem,
    RefreshToken,
    SecurityActivity,
    User,
    UserNotificationState,
    UserSession,
)
from app.services.hotels_service import create_hotel_delivery_intent  # noqa: E402


MANIFEST_PATH = Path(__file__).resolve().parents[1] / "app" / "hotels" / "fixtures" / "hoteles_demo_manifest.json"
PASSWORD_CONTEXT = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
SAFE_APP_ENVS = frozenset({"test", "demo", "local_fixture"})
DATASET_ID = "hoteles-demo-v1"
SEED_REVISION = "hotel-demo-seed-v1"
FIXED_CHECK_IN = date(2026, 7, 10)
FIXED_CHECK_OUT = date(2026, 7, 12)
DEMO_PASSWORD = "ViruDemoOnly-2026"
MARKER_SUFFIX = ".h44-demo.json"


def _marker_path(db_path: Path) -> Path:
    return db_path.with_name(db_path.name + MARKER_SUFFIX)


def _load_marker(db_path: Path) -> dict[str, object] | None:
    marker = _marker_path(db_path)
    if not marker.exists():
        return None
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DemoSeedConfigurationError("hotel_demo_marker_invalid") from exc
    if not isinstance(payload, dict):
        raise DemoSeedConfigurationError("hotel_demo_marker_invalid")
    if payload.get("dataset_id") != DATASET_ID or payload.get("seed_revision") != SEED_REVISION:
        raise DemoSeedConfigurationError("hotel_demo_marker_mismatch")
    ids = payload.get("ids")
    required_keys = {
        "users",
        "hotels",
        "aliases",
        "snapshots",
        "stay_offers",
        "watchlists",
        "tracked_offers",
        "alert_rules",
        "alert_events",
        "deliveries",
        "notification_states",
        "provider_runs",
        "latency_aggregates",
    }
    if payload.get("status", "complete") not in {"in_progress", "complete"}:
        raise DemoSeedConfigurationError("hotel_demo_marker_status_invalid")
    if not isinstance(ids, dict) or set(ids) != required_keys:
        raise DemoSeedConfigurationError("hotel_demo_marker_scope_missing")
    if any(not isinstance(value, list) or any(not isinstance(item, str) for item in value) for value in ids.values()):
        raise DemoSeedConfigurationError("hotel_demo_marker_scope_invalid")
    return payload


@contextmanager
def _offline_network_guard() -> Iterator[dict[str, int]]:
    observed = {"attempts": 0}

    def blocked(*_args: object, **_kwargs: object) -> None:
        observed["attempts"] += 1
        raise DemoSeedConfigurationError("hotel_demo_external_network_blocked")

    with (
        patch.object(socket, "create_connection", blocked),
        patch.object(socket, "getaddrinfo", blocked),
        patch.object(socket.socket, "connect", blocked),
        patch.object(socket.socket, "connect_ex", blocked),
    ):
        yield observed


def _write_marker(db_path: Path, marker: dict[str, object]) -> None:
    path = _marker_path(db_path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(marker, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


class DemoSeedConfigurationError(ValueError):
    pass


def _load_manifest() -> dict[str, object]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig"))
    if manifest.get("dataset_id") != DATASET_ID or manifest.get("seed_revision") != SEED_REVISION:
        raise DemoSeedConfigurationError("hotel_demo_manifest_mismatch")
    if manifest.get("provider_mode") != "mock" or manifest.get("expected_external_calls") != 0:
        raise DemoSeedConfigurationError("hotel_demo_manifest_provider_contract_invalid")
    return manifest


def _db_path(db_url: str) -> Path:
    if not db_url.startswith("sqlite:///") or db_url in {"sqlite:///:memory:", "sqlite:///./viru.db", "sqlite:///viru.db"}:
        raise DemoSeedConfigurationError("hotel_demo_requires_explicit_sqlite_db")
    raw_path = db_url.removeprefix("sqlite:///")
    path = Path(raw_path)
    if not path.is_absolute():
        raise DemoSeedConfigurationError("hotel_demo_requires_absolute_db")
    try:
        path.resolve().relative_to(Path(tempfile.gettempdir()).resolve())
    except ValueError as exc:
        raise DemoSeedConfigurationError("hotel_demo_requires_temp_workspace") from exc
    if not path.parent.exists():
        raise DemoSeedConfigurationError("hotel_demo_db_parent_missing")
    return path


def _validate_environment(*, reset: bool = False) -> str:
    app_env = os.getenv("APP_ENV", "").strip().lower()
    if app_env not in SAFE_APP_ENVS:
        raise DemoSeedConfigurationError("hotel_demo_requires_safe_app_env")
    if reset and os.getenv("HOTEL_PROVIDER", "mock").strip().lower() not in {"", "mock"}:
        raise DemoSeedConfigurationError("hotel_demo_reset_requires_mock_provider")
    return app_env


def _alembic_config(db_url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(_BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", db_url)
    return config


def _run_migrations(db_url: str) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "DB_URL": db_url,
            "RUN_DB_INIT": "false",
            "RUN_SEED_USERS": "false",
            "WATCHLIST_STARTUP_REFRESH_ENABLED": "false",
            "FARE_MEMORY_BOOT_WARMUP_ENABLED": "false",
            "FARE_MEMORY_REVALIDATION_WORKER_ENABLED": "false",
            "HOTEL_PROFILE": "local_fixture",
            "HOTEL_FEATURE_ENABLED": "false",
            "HOTEL_SWEEP_ENABLED": "false",
            "HOTEL_GEOCODER_ENABLED": "false",
        }
    )
    try:
        with patch.dict(os.environ, environment, clear=False):
            command.upgrade(_alembic_config(db_url), "head")
    except Exception as exc:
        raise DemoSeedConfigurationError("hotel_demo_migration_failed") from exc


@contextmanager
def _session(db_url: str, *, require_existing: bool = False) -> Iterator[Session]:
    path = _db_path(db_url)
    if require_existing and not path.exists():
        raise DemoSeedConfigurationError("hotel_demo_db_does_not_exist")
    from sqlalchemy import create_engine

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def _assert_schema_at_head(db: Session, db_url: str) -> None:
    try:
        current = {
            str(version)
            for (version,) in db.execute(text("SELECT version_num FROM alembic_version"))
        }
        expected = set(ScriptDirectory.from_config(_alembic_config(db_url)).get_heads())
    except Exception as exc:
        raise DemoSeedConfigurationError("hotel_demo_schema_revision_unknown") from exc
    if current != expected:
        raise DemoSeedConfigurationError("hotel_demo_schema_not_at_head")


def _count(db: Session, model: type, criterion=None) -> int:
    statement = select(func.count()).select_from(model)
    if criterion is not None:
        statement = statement.where(criterion)
    return int(db.scalar(statement) or 0)


def _ensure_user(db: Session, email: str, created: dict[str, int]) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is not None:
        created["users_reused"] += 1
        return user
    user = User(
        email=email,
        password_hash=PASSWORD_CONTEXT.hash(DEMO_PASSWORD),
        is_verified=True,
        is_admin=False,
        locale="es",
        timezone="Europe/Madrid",
    )
    db.add(user)
    db.flush()
    created["users_created"] += 1
    return user


def _ensure_watchlist(db: Session, *, user_id: str, hotel_id: str, label: str, created: dict[str, int]) -> None:
    existing = db.scalar(
        select(HotelWatchlistItem).where(
            HotelWatchlistItem.user_id == user_id,
            HotelWatchlistItem.hotel_id == hotel_id,
        )
    )
    if existing is not None:
        created["watchlists_reused"] += 1
        return
    db.add(HotelWatchlistItem(user_id=user_id, hotel_id=hotel_id, label=label))
    created["watchlists_created"] += 1


def _ensure_tracked_offer(db: Session, *, user_id: str, hotel_id: str, amount: float, created: dict[str, int]) -> HotelTrackedOffer:
    offer = db.scalar(
        select(HotelTrackedOffer).where(
            HotelTrackedOffer.user_id == user_id,
            HotelTrackedOffer.hotel_id == hotel_id,
            HotelTrackedOffer.check_in == FIXED_CHECK_IN,
            HotelTrackedOffer.check_out == FIXED_CHECK_OUT,
            HotelTrackedOffer.guests == 2,
            HotelTrackedOffer.provider == "mock",
        )
    )
    if offer is not None:
        created["tracked_offers_reused"] += 1
        return offer
    offer = HotelTrackedOffer(
        user_id=user_id,
        hotel_id=hotel_id,
        area_label="Madrid demo",
        origin_query="Madrid",
        check_in=FIXED_CHECK_IN,
        check_out=FIXED_CHECK_OUT,
        guests=2,
        room_label="Doble estandar",
        meal_plan="solo alojamiento",
        cancellation_policy="flexible",
        provider="mock",
        initial_price=amount,
        current_price=amount,
        target_price=170,
        currency="EUR",
        is_active=True,
    )
    db.add(offer)
    db.flush()
    db.add(
        HotelRateSnapshot(
            hotel_id=hotel_id,
            tracked_offer_id=offer.id,
            provider="mock",
            check_in=FIXED_CHECK_IN,
            check_out=FIXED_CHECK_OUT,
            guests=2,
            room_label="Doble estandar",
            meal_plan="solo alojamiento",
            cancellation_policy="flexible",
            currency="EUR",
            amount=amount,
            availability_status="available",
        )
    )
    created["tracked_offers_created"] += 1
    created["tracked_offer_snapshots_created"] += 1
    return offer


def _ensure_alert(db: Session, *, user_id: str, hotel_id: str, tracked_offer_id: str | None, created: dict[str, int]) -> HotelAlertEvent:
    rule_query = select(HotelAlertRule).where(
        HotelAlertRule.user_id == user_id,
        HotelAlertRule.hotel_id == hotel_id,
        HotelAlertRule.rule_type == "price_below",
    )
    if tracked_offer_id is None:
        rule_query = rule_query.where(HotelAlertRule.tracked_offer_id.is_(None))
    else:
        rule_query = rule_query.where(HotelAlertRule.tracked_offer_id == tracked_offer_id)
    rule = db.scalar(rule_query)
    if rule is None:
        rule = HotelAlertRule(
            user_id=user_id,
            hotel_id=hotel_id,
            tracked_offer_id=tracked_offer_id,
            rule_type="price_below",
            threshold_amount=220,
            threshold_percent=None,
            compare_against="snapshot_previous",
            is_active=True,
        )
        db.add(rule)
        db.flush()
        created["alert_rules_created"] += 1
    else:
        created["alert_rules_reused"] += 1

    event = db.scalar(
        select(HotelAlertEvent).where(
            HotelAlertEvent.user_id == user_id,
            HotelAlertEvent.rule_id == rule.id,
            HotelAlertEvent.event_type == "price_below",
        )
    )
    if event is None:
        event = HotelAlertEvent(
            user_id=user_id,
            rule_id=rule.id,
            hotel_id=hotel_id,
            event_type="price_below",
            message="DEMO_NO_LIVE_AVAILABILITY: precio sintético por debajo del umbral",
            trigger_value=189.5,
        )
        db.add(event)
        db.flush()
        created["alert_events_created"] += 1
    else:
        created["alert_events_reused"] += 1
    delivery = create_hotel_delivery_intent(db, event_id=event.id, user_id=user_id)
    if delivery is not None and getattr(delivery, "_created_by_call", False):
        created["deliveries_created"] += 1
    else:
        created["deliveries_reused"] += 1
    return event


def _scope_counts(db: Session, manifest: dict[str, object]) -> dict[str, int]:
    emails = list(manifest["demo_users"])
    provider_ids = list(manifest["provider_hotel_ids"])
    user_ids = select(User.id).where(User.email.in_(emails))
    hotel_ids = select(HotelProviderAlias.hotel_id).where(
        HotelProviderAlias.provider == "mock",
        HotelProviderAlias.provider_hotel_id.in_(provider_ids),
    )
    return {
        "users": _count(db, User, User.email.in_(emails)),
        "hotels": _count(db, HotelProperty, HotelProperty.id.in_(hotel_ids)),
        "aliases": _count(db, HotelProviderAlias, and_(HotelProviderAlias.provider == "mock", HotelProviderAlias.provider_hotel_id.in_(provider_ids))),
        "snapshots": _count(db, HotelRateSnapshot, HotelRateSnapshot.hotel_id.in_(hotel_ids)),
        "stay_offers": _count(
            db,
            HotelStayOffer,
            HotelStayOffer.id.in_(
                select(HotelRateSnapshot.stay_offer_id).where(
                    HotelRateSnapshot.hotel_id.in_(hotel_ids),
                    HotelRateSnapshot.stay_offer_id.is_not(None),
                )
            ),
        ),
        "watchlists": _count(db, HotelWatchlistItem, HotelWatchlistItem.user_id.in_(user_ids)),
        "tracked_offers": _count(db, HotelTrackedOffer, HotelTrackedOffer.user_id.in_(user_ids)),
        "alert_rules": _count(db, HotelAlertRule, HotelAlertRule.user_id.in_(user_ids)),
        "alert_events": _count(db, HotelAlertEvent, HotelAlertEvent.user_id.in_(user_ids)),
        "deliveries": _count(db, HotelNotificationDelivery, HotelNotificationDelivery.recipient_user_id.in_(user_ids)),
        "notification_states": _count(db, UserNotificationState, UserNotificationState.user_id.in_(user_ids)),
        "provider_runs": _count(db, HotelProviderRun, HotelProviderRun.id.in_(select(HotelRateSnapshot.provider_run_id).where(HotelRateSnapshot.hotel_id.in_(hotel_ids)))),
        "latency_aggregates": _count(db, HotelProviderLatencyAggregate, HotelProviderLatencyAggregate.provider_run_id.in_(select(HotelProviderRun.id).where(HotelProviderRun.id.in_(select(HotelRateSnapshot.provider_run_id).where(HotelRateSnapshot.hotel_id.in_(hotel_ids)))))),
    }


def _collect_scope_ids(db: Session, manifest: dict[str, object]) -> dict[str, list[str]]:
    emails = list(manifest["demo_users"])
    provider_ids = list(manifest["provider_hotel_ids"])
    user_ids = list(db.scalars(select(User.id).where(User.email.in_(emails))))
    hotel_ids = list(db.scalars(select(HotelProviderAlias.hotel_id).where(
        HotelProviderAlias.provider == "mock",
        HotelProviderAlias.provider_hotel_id.in_(provider_ids),
    )))
    hotel_id_filter = HotelRateSnapshot.hotel_id.in_(hotel_ids or ["__none__"])
    provider_run_ids = list(db.scalars(select(HotelRateSnapshot.provider_run_id).where(
        hotel_id_filter,
        HotelRateSnapshot.provider_run_id.is_not(None),
    )))
    stay_offer_ids = list(db.scalars(select(HotelRateSnapshot.stay_offer_id).where(
        hotel_id_filter,
        HotelRateSnapshot.stay_offer_id.is_not(None),
    )))
    return {
        "users": user_ids,
        "hotels": hotel_ids,
        "aliases": list(db.scalars(select(HotelProviderAlias.id).where(
            HotelProviderAlias.provider == "mock",
            HotelProviderAlias.provider_hotel_id.in_(provider_ids),
        ))),
        "snapshots": list(db.scalars(select(HotelRateSnapshot.id).where(hotel_id_filter))),
        "stay_offers": stay_offer_ids,
        "watchlists": list(db.scalars(select(HotelWatchlistItem.id).where(HotelWatchlistItem.user_id.in_(user_ids or ["__none__"])))),
        "tracked_offers": list(db.scalars(select(HotelTrackedOffer.id).where(HotelTrackedOffer.user_id.in_(user_ids or ["__none__"])))),
        "alert_rules": list(db.scalars(select(HotelAlertRule.id).where(HotelAlertRule.user_id.in_(user_ids or ["__none__"])))),
        "alert_events": list(db.scalars(select(HotelAlertEvent.id).where(HotelAlertEvent.user_id.in_(user_ids or ["__none__"])))),
        "deliveries": list(db.scalars(select(HotelNotificationDelivery.id).where(HotelNotificationDelivery.recipient_user_id.in_(user_ids or ["__none__"])))),
        "notification_states": list(db.scalars(select(UserNotificationState.id).where(UserNotificationState.user_id.in_(user_ids or ["__none__"])))),
        "provider_runs": provider_run_ids,
        "latency_aggregates": list(db.scalars(select(HotelProviderLatencyAggregate.id).where(HotelProviderLatencyAggregate.provider_run_id.in_(provider_run_ids or ["__none__"])))),
    }


def _assert_marker_scope_unchanged(
    db: Session,
    scope: dict[str, list[str]],
    manifest: dict[str, object] | None = None,
) -> None:
    marker_ids = {key: set(value) for key, value in scope.items()}
    if manifest is not None:
        observed_users = set(db.scalars(select(User.id).where(User.email.in_(list(manifest["demo_users"])))) )
        if observed_users != marker_ids["users"]:
            raise DemoSeedConfigurationError("hotel_demo_scope_changed:users")
        observed_hotels = set(db.scalars(select(HotelProviderAlias.hotel_id).where(
            HotelProviderAlias.provider == "mock",
            HotelProviderAlias.provider_hotel_id.in_(list(manifest["provider_hotel_ids"])),
        )))
        if observed_hotels != marker_ids["hotels"]:
            raise DemoSeedConfigurationError("hotel_demo_scope_changed:hotels")
    checks = {
        "users": select(User.id).where(User.id.in_(marker_ids["users"] or ["__none__"])),
        "hotels": select(HotelProperty.id).where(HotelProperty.id.in_(marker_ids["hotels"] or ["__none__"])),
        "aliases": select(HotelProviderAlias.id).where(HotelProviderAlias.hotel_id.in_(marker_ids["hotels"] or ["__none__"])),
        "snapshots": select(HotelRateSnapshot.id).where(HotelRateSnapshot.hotel_id.in_(marker_ids["hotels"] or ["__none__"])),
        "stay_offers": select(HotelStayOffer.id).where(HotelStayOffer.id.in_(marker_ids["stay_offers"] or ["__none__"])),
        "watchlists": select(HotelWatchlistItem.id).where(or_(HotelWatchlistItem.user_id.in_(marker_ids["users"] or ["__none__"]), HotelWatchlistItem.hotel_id.in_(marker_ids["hotels"] or ["__none__"]))),
        "tracked_offers": select(HotelTrackedOffer.id).where(or_(HotelTrackedOffer.user_id.in_(marker_ids["users"] or ["__none__"]), HotelTrackedOffer.hotel_id.in_(marker_ids["hotels"] or ["__none__"]))),
        "alert_rules": select(HotelAlertRule.id).where(or_(HotelAlertRule.user_id.in_(marker_ids["users"] or ["__none__"]), HotelAlertRule.hotel_id.in_(marker_ids["hotels"] or ["__none__"]))),
        "alert_events": select(HotelAlertEvent.id).where(or_(HotelAlertEvent.user_id.in_(marker_ids["users"] or ["__none__"]), HotelAlertEvent.hotel_id.in_(marker_ids["hotels"] or ["__none__"]))),
        "deliveries": select(HotelNotificationDelivery.id).where(HotelNotificationDelivery.recipient_user_id.in_(marker_ids["users"] or ["__none__"])),
        "notification_states": select(UserNotificationState.id).where(UserNotificationState.user_id.in_(marker_ids["users"] or ["__none__"])),
    }
    checks.update(
        {
            "provider_runs": select(HotelProviderRun.id).where(
                HotelProviderRun.id.in_(select(HotelRateSnapshot.provider_run_id).where(
                    HotelRateSnapshot.hotel_id.in_(marker_ids["hotels"] or ["__none__"]),
                    HotelRateSnapshot.provider_run_id.is_not(None),
                ))
            ),
            "latency_aggregates": select(HotelProviderLatencyAggregate.id).where(
                HotelProviderLatencyAggregate.provider_run_id.in_(marker_ids["provider_runs"] or ["__none__"])
            ),
        }
    )
    for name, statement in checks.items():
        observed = set(db.scalars(statement))
        if observed != marker_ids[name]:
            raise DemoSeedConfigurationError(f"hotel_demo_scope_changed:{name}")


def _assert_no_external_hotel_refs(
    db: Session,
    hotel_ids: list[str],
    stay_offer_ids: list[str],
) -> None:
    allowed_tables = {
        "hotel_provider_alias",
        "hotel_rate_snapshot",
        "hotel_stay_offer",
        "hotel_watchlist_item",
        "hotel_tracked_offer",
        "hotel_alert_rule",
        "hotel_alert_event",
    }
    # Comp sets are deliberately not in the allowed list: an external
    # comparison set must block reset instead of being adopted or deleted.
    inspector = inspect(db.bind)
    for table_name in inspector.get_table_names():
        if table_name in allowed_tables:
            continue
        for foreign_key in inspector.get_foreign_keys(table_name):
            if foreign_key.get("referred_table") != "hotel_property":
                continue
            columns = foreign_key.get("constrained_columns") or []
            if not columns:
                continue
            column_name = columns[0]
            table_expr = table(table_name, column(column_name))
            found = db.execute(
                select(func.count())
                .select_from(table_expr)
                .where(table_expr.c[column_name].in_(hotel_ids or ["__none__"]))
            ).scalar()
            if found:
                raise DemoSeedConfigurationError(f"hotel_demo_hotel_has_external_refs:{table_name}")
    external_stay_offer = db.scalar(
        select(HotelStayOffer.id).where(
            HotelStayOffer.canonical_hotel_id.in_(hotel_ids or ["__none__"]),
            HotelStayOffer.id.not_in(stay_offer_ids or ["__none__"]),
        ).limit(1)
    )
    if external_stay_offer is not None:
        raise DemoSeedConfigurationError("hotel_demo_hotel_has_external_refs:hotel_stay_offer")


def _assert_no_external_stay_offer_refs(
    db: Session,
    stay_offer_ids: list[str],
    user_ids: list[str],
) -> None:
    allowed_tables = {"hotel_rate_snapshot", "hotel_user_stay_watch"}
    inspector = inspect(db.bind)
    for table_name in inspector.get_table_names():
        if table_name in allowed_tables:
            continue
        for foreign_key in inspector.get_foreign_keys(table_name):
            if foreign_key.get("referred_table") != "hotel_stay_offer":
                continue
            columns = foreign_key.get("constrained_columns") or []
            if not columns:
                continue
            column_name = columns[0]
            table_expr = table(table_name, column(column_name))
            found = db.execute(
                select(func.count())
                .select_from(table_expr)
                .where(table_expr.c[column_name].in_(stay_offer_ids or ["__none__"]))
            ).scalar()
            if found:
                raise DemoSeedConfigurationError(f"hotel_demo_stay_offer_has_external_refs:{table_name}")
    external_watch = db.scalar(
        select(HotelUserStayWatch.id).where(
            HotelUserStayWatch.stay_offer_id.in_(stay_offer_ids or ["__none__"]),
            HotelUserStayWatch.user_id.not_in(user_ids or ["__none__"]),
        ).limit(1)
    )
    if external_watch is not None:
        raise DemoSeedConfigurationError("hotel_demo_stay_offer_has_external_refs:hotel_user_stay_watch")


def _assert_no_external_user_refs(db: Session, user_ids: list[str]) -> None:
    allowed_tables = {
        "hotel_watchlist_item",
        "hotel_tracked_offer",
        "hotel_alert_rule",
        "hotel_alert_event",
        "hotel_notification_delivery",
        "user_notification_state",
        "hotel_user_stay_watch",
    }
    inspector = inspect(db.bind)
    for table_name in inspector.get_table_names():
        if table_name in allowed_tables or table_name == "users":
            continue
        for foreign_key in inspector.get_foreign_keys(table_name):
            if foreign_key.get("referred_table") != "users":
                continue
            columns = foreign_key.get("constrained_columns") or []
            if not columns:
                continue
            column_name = columns[0]
            table_expr = table(table_name, column(column_name))
            found = db.execute(
                select(func.count())
                .select_from(table_expr)
                .where(table_expr.c[column_name].in_(user_ids or ["__none__"]))
            ).scalar()
            if found:
                raise DemoSeedConfigurationError(f"hotel_demo_user_has_external_refs:{table_name}")


def _report(*, operation: str, app_env: str, manifest: dict[str, object], counts: dict[str, int], created: dict[str, int], warnings: list[str] | None = None, external_calls_observed: int = 0) -> dict[str, object]:
    return {
        "result": "passed",
        "operation": operation,
        "dataset_id": manifest["dataset_id"],
        "fixture_version": manifest["fixture_version"],
        "seed_revision": manifest["seed_revision"],
        "app_env": app_env,
        "db_isolation_kind": "sqlite_temp_workspace",
        "user_scope": "synthetic_demo_users_only",
        "provider_mode": "mock",
        "external_calls_expected": 0,
        "external_calls_observed": external_calls_observed,
        "rows_created_or_reused": {key: value for key, value in sorted(created.items())},
        "rows_by_table": {key: value for key, value in sorted(counts.items())},
        "rows_rejected": 0,
        "warnings": warnings or [],
        "synthetic_label": manifest["synthetic_label"],
    }


def run_seed(db_url: str) -> dict[str, object]:
    app_env = _validate_environment()
    manifest = _load_manifest()
    path = _db_path(db_url)
    was_new = not path.exists()
    marker = _load_marker(path) if path.exists() else None
    if path.exists() and marker is None and not was_new:
        raise DemoSeedConfigurationError("hotel_demo_requires_marked_db")
    if marker is not None and marker.get("status", "complete") == "in_progress":
        raise DemoSeedConfigurationError("hotel_demo_seed_in_progress")
    network_observed = {"attempts": 0}
    with _offline_network_guard() as migration_network_observed:
        if was_new:
            _write_marker(
                path,
                {
                    "dataset_id": DATASET_ID,
                    "seed_revision": SEED_REVISION,
                    "status": "in_progress",
                    "ids": {
                        key: []
                        for key in {
                            "users", "hotels", "aliases", "snapshots", "watchlists",
                            "stay_offers",
                            "tracked_offers", "alert_rules", "alert_events", "deliveries",
                            "notification_states", "provider_runs", "latency_aggregates",
                        }
                    },
                },
            )
            _run_migrations(db_url)
        network_observed["attempts"] += migration_network_observed["attempts"]
    created = {
        "users_created": 0,
        "users_reused": 0,
        "watchlists_created": 0,
        "watchlists_reused": 0,
        "tracked_offers_created": 0,
        "tracked_offers_reused": 0,
        "tracked_offer_snapshots_created": 0,
        "alert_rules_created": 0,
        "alert_rules_reused": 0,
        "alert_events_created": 0,
        "alert_events_reused": 0,
        "deliveries_created": 0,
        "deliveries_reused": 0,
        "hotel_rows_created_by_mock_ingestion": 0,
        "hotel_rows_reused_by_mock_ingestion": 0,
    }
    with _offline_network_guard() as session_network_observed, _session(db_url) as db:
        network_observed["attempts"] += session_network_observed["attempts"]
        if marker is not None:
            marker_ids = marker.get("ids")
            if not isinstance(marker_ids, dict):
                raise DemoSeedConfigurationError("hotel_demo_marker_scope_missing")
            _assert_marker_scope_unchanged(
                db,
                {key: [str(item) for item in value] for key, value in marker_ids.items() if isinstance(value, list)},
                manifest,
            )
        from unittest.mock import patch

        with patch.dict(
            os.environ,
            {
                "APP_ENV": app_env,
                "HOTEL_PROFILE": "local_fixture",
                "HOTEL_PROVIDER": "mock",
                "HOTEL_FEATURE_ENABLED": "true",
                "HOTEL_SWEEP_ENABLED": "false",
                "HOTEL_GEOCODER_ENABLED": "false",
            },
            clear=False,
        ):
            provider_ids = list(manifest["provider_hotel_ids"])
            existing_aliases = _count(
                db,
                HotelProviderAlias,
                and_(HotelProviderAlias.provider == "mock", HotelProviderAlias.provider_hotel_id.in_(provider_ids)),
            )
            if existing_aliases < len(provider_ids):
                before = _count(db, HotelProperty)
                HotelIngestionService(db).ingest()
                created["hotel_rows_created_by_mock_ingestion"] = max(0, _count(db, HotelProperty) - before)
            else:
                created["hotel_rows_reused_by_mock_ingestion"] = existing_aliases

        aliases = list(
            db.scalars(
                select(HotelProviderAlias).where(
                    HotelProviderAlias.provider == "mock",
                    HotelProviderAlias.provider_hotel_id.in_(list(manifest["provider_hotel_ids"])),
                )
            )
        )
        hotels_by_provider_id = {
            alias.provider_hotel_id: db.get(HotelProperty, alias.hotel_id)
            for alias in aliases
        }
        if len(hotels_by_provider_id) != len(manifest["provider_hotel_ids"]) or any(value is None for value in hotels_by_provider_id.values()):
            raise DemoSeedConfigurationError("hotel_demo_fixture_scope_incomplete")

        user_a = _ensure_user(db, "demo-user-a@viru.local", created)
        user_b = _ensure_user(db, "demo-user-b@viru.local", created)
        hotel_sol = hotels_by_provider_id["mock-sol-001"]
        hotel_luna = hotels_by_provider_id["mock-luna-002"]
        assert hotel_sol is not None and hotel_luna is not None
        _ensure_watchlist(db, user_id=user_a.id, hotel_id=hotel_sol.id, label="DEMO Madrid", created=created)
        _ensure_watchlist(db, user_id=user_b.id, hotel_id=hotel_luna.id, label="DEMO compartido", created=created)
        offer = _ensure_tracked_offer(db, user_id=user_a.id, hotel_id=hotel_sol.id, amount=189.5, created=created)
        _ensure_alert(db, user_id=user_a.id, hotel_id=hotel_sol.id, tracked_offer_id=offer.id, created=created)
        _ensure_alert(db, user_id=user_b.id, hotel_id=hotel_luna.id, tracked_offer_id=None, created=created)
        db.commit()
        counts = _scope_counts(db, manifest)
        scope = _collect_scope_ids(db, manifest)
    _write_marker(
        path,
        {
            "dataset_id": DATASET_ID,
            "seed_revision": SEED_REVISION,
            "status": "complete",
            "ids": scope,
        },
    )
    return _report(
        operation="seed",
        app_env=app_env,
        manifest=manifest,
        counts=counts,
        created=created,
        external_calls_observed=network_observed["attempts"],
    )


def run_abort(db_url: str, *, confirm_demo_db: bool) -> dict[str, object]:
    _validate_environment(reset=True)
    manifest = _load_manifest()
    if not confirm_demo_db:
        raise DemoSeedConfigurationError("hotel_demo_abort_requires_confirmation")
    path = _db_path(db_url)
    marker = _load_marker(path)
    if marker is None or marker.get("status") != "in_progress":
        raise DemoSeedConfigurationError("hotel_demo_abort_requires_in_progress_marker")
    path.unlink(missing_ok=True)
    for suffix in ("-wal", "-shm", "-journal"):
        path.with_name(path.name + suffix).unlink(missing_ok=True)
    _marker_path(path).unlink(missing_ok=True)
    return _report(
        operation="abort",
        app_env=os.getenv("APP_ENV", "").strip().lower(),
        manifest=manifest,
        counts={},
        created={"database_removed": 1, "marker_removed": 1},
        warnings=["in_progress_demo_db_removed_after_explicit_confirmation"],
    )


def run_reset(db_url: str, *, confirm_demo_db: bool, dataset_id: str = DATASET_ID) -> dict[str, object]:
    app_env = _validate_environment(reset=True)
    manifest = _load_manifest()
    if dataset_id != DATASET_ID:
        raise DemoSeedConfigurationError("hotel_demo_dataset_mismatch")
    if not confirm_demo_db:
        raise DemoSeedConfigurationError("hotel_demo_reset_requires_confirmation")
    path = _db_path(db_url)
    if not path.exists():
        raise DemoSeedConfigurationError("hotel_demo_db_does_not_exist")
    marker = _load_marker(path)
    if marker is None:
        raise DemoSeedConfigurationError("hotel_demo_requires_marked_db")
    if marker.get("status", "complete") != "complete":
        raise DemoSeedConfigurationError("hotel_demo_seed_in_progress")
    marker_ids = marker["ids"]
    if not isinstance(marker_ids, dict):
        raise DemoSeedConfigurationError("hotel_demo_marker_scope_missing")

    with _session(db_url, require_existing=True) as db:
        _assert_schema_at_head(db, db_url)
        scope = {key: [str(item) for item in value] for key, value in marker_ids.items() if isinstance(value, list)}
        user_ids = scope.get("users", [])
        hotel_ids = scope.get("hotels", [])
        stay_offer_ids = scope.get("stay_offers", [])
        run_ids = scope.get("provider_runs", [])
        event_ids = scope.get("alert_events", [])
        _assert_marker_scope_unchanged(db, scope, manifest)
        # Authentication artifacts created by the isolated demo logins are not
        # part of the hotel dataset marker. Remove only artifacts owned by the
        # marked demo users before checking for genuinely external references.
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id.in_(user_ids or ["__none__"]))
            .values(replaced_by_token_id=None)
        )
        db.execute(delete(RefreshToken).where(RefreshToken.user_id.in_(user_ids or ["__none__"])))
        db.execute(delete(UserSession).where(UserSession.user_id.in_(user_ids or ["__none__"])))
        db.execute(delete(SecurityActivity).where(SecurityActivity.user_id.in_(user_ids or ["__none__"])))
        _assert_no_external_user_refs(db, user_ids)
        _assert_no_external_hotel_refs(db, hotel_ids, stay_offer_ids)
        _assert_no_external_stay_offer_refs(db, stay_offer_ids, user_ids)
        deleted: dict[str, int] = {}

        def remove(name: str, model: type, criterion) -> None:
            result = db.execute(delete(model).where(criterion))
            deleted[name] = int(result.rowcount or 0)

        remove("deliveries", HotelNotificationDelivery, HotelNotificationDelivery.id.in_(scope.get("deliveries", []) or ["__none__"]))
        remove("notification_states", UserNotificationState, UserNotificationState.id.in_(scope.get("notification_states", []) or ["__none__"]))
        remove("alert_events", HotelAlertEvent, HotelAlertEvent.id.in_(event_ids or ["__none__"]))
        remove("alert_rules", HotelAlertRule, HotelAlertRule.id.in_(scope.get("alert_rules", []) or ["__none__"]))
        remove("stay_watches", HotelUserStayWatch, HotelUserStayWatch.user_id.in_(user_ids or ["__none__"]))
        remove("snapshots", HotelRateSnapshot, HotelRateSnapshot.id.in_(scope.get("snapshots", []) or ["__none__"]))
        remove("tracked_offers", HotelTrackedOffer, HotelTrackedOffer.id.in_(scope.get("tracked_offers", []) or ["__none__"]))
        remove("watchlists", HotelWatchlistItem, HotelWatchlistItem.id.in_(scope.get("watchlists", []) or ["__none__"]))
        remove("stay_offers", HotelStayOffer, HotelStayOffer.id.in_(stay_offer_ids or ["__none__"]))
        remove("latency_aggregates", HotelProviderLatencyAggregate, HotelProviderLatencyAggregate.provider_run_id.in_(run_ids or ["__none__"]))
        remove("provider_runs", HotelProviderRun, HotelProviderRun.id.in_(run_ids or ["__none__"]))
        remove("aliases", HotelProviderAlias, HotelProviderAlias.id.in_(scope.get("aliases", []) or ["__none__"]))
        remove("hotels", HotelProperty, HotelProperty.id.in_(hotel_ids or ["__none__"]))
        remove("users", User, User.id.in_(user_ids or ["__none__"]))
        db.commit()
        remaining = _scope_counts(db, manifest)
    if any(remaining.values()):
        raise DemoSeedConfigurationError("hotel_demo_reset_scope_not_empty")
    _marker_path(path).unlink(missing_ok=True)
    return _report(operation="reset", app_env=app_env, manifest=manifest, counts=remaining, created=deleted)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed or reset an isolated H44 hotel Mock dataset")
    subparsers = parser.add_subparsers(dest="operation", required=True)
    seed = subparsers.add_parser("seed")
    seed.add_argument("--db-url", required=True)
    reset = subparsers.add_parser("reset")
    reset.add_argument("--db-url", required=True)
    reset.add_argument("--dataset-id", default=DATASET_ID)
    reset.add_argument("--confirm-demo-db", action="store_true")
    abort = subparsers.add_parser("abort")
    abort.add_argument("--db-url", required=True)
    abort.add_argument("--confirm-demo-db", action="store_true")
    return parser


def _safe_error_reason(exc: Exception) -> str:
    reason = str(exc).strip()
    if reason and len(reason) <= 120 and re.fullmatch(r"[a-z0-9_:-]+", reason):
        return reason
    return type(exc).__name__


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.operation == "seed":
            report = run_seed(args.db_url)
        elif args.operation == "reset":
            report = run_reset(args.db_url, confirm_demo_db=args.confirm_demo_db, dataset_id=args.dataset_id)
        else:
            report = run_abort(args.db_url, confirm_demo_db=args.confirm_demo_db)
    except (DemoSeedConfigurationError, OSError, ValueError) as exc:
        print(json.dumps({"result": "blocked", "reason": _safe_error_reason(exc)}, sort_keys=True))
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
