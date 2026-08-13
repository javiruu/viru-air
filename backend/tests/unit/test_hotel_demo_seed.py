from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.infrastructure.db.models import HotelCompSet, HotelProperty, HotelStayOffer, User
from scripts.hotel_demo_seed import (
    DATASET_ID,
    DemoSeedConfigurationError,
    main,
    run_abort,
    run_reset,
    run_seed,
)


def _db_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'hotel-demo.db').as_posix()}"


@pytest.fixture(autouse=True)
def _safe_demo_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "local_fixture")
    monkeypatch.setenv("HOTEL_PROVIDER", "mock")


def test_manifest_is_versioned_and_mock_only() -> None:
    manifest_path = Path(__file__).resolve().parents[2] / "app" / "hotels" / "fixtures" / "hoteles_demo_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["dataset_id"] == DATASET_ID
    assert manifest["fixture_version"] == 1
    assert manifest["synthetic_label"] == "DEMO_NO_LIVE_AVAILABILITY"
    assert manifest["provider_mode"] == "mock"
    assert manifest["expected_external_calls"] == 0


def test_seed_is_idempotent_and_reports_redacted_scope(tmp_path: Path) -> None:
    first = run_seed(_db_url(tmp_path))
    second = run_seed(_db_url(tmp_path))

    assert first["result"] == "passed"
    assert first["external_calls_expected"] == 0
    assert first["external_calls_observed"] == 0
    assert first["rows_by_table"]["users"] == 2
    assert first["rows_by_table"]["aliases"] == 3
    assert first["rows_by_table"]["tracked_offers"] == 1
    assert first["rows_by_table"]["alert_events"] == 2
    assert second["rows_created_or_reused"]["users_created"] == 0
    assert second["rows_created_or_reused"]["users_reused"] == 2
    assert second["rows_created_or_reused"]["tracked_offers_created"] == 0
    serialized = json.dumps(first)
    for private in ("password_hash", "provider_run_id", "hotel_id", "user_id", "api_key"):
        assert private not in serialized


def test_seed_rejects_non_temp_db_and_unsafe_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(DemoSeedConfigurationError, match="safe_app_env"):
        run_seed(_db_url(tmp_path))

    monkeypatch.setenv("APP_ENV", "local_fixture")
    with pytest.raises(DemoSeedConfigurationError, match="temp_workspace"):
        run_seed("sqlite:///C:/production-like/hotel.db")


def test_seed_rejects_existing_unmarked_db(tmp_path: Path) -> None:
    url = _db_url(tmp_path)
    Path(tmp_path / "hotel-demo.db").write_bytes(b"not-a-demo-db")
    with pytest.raises(DemoSeedConfigurationError, match="marked_db"):
        run_seed(url)


def test_abort_requires_confirmation_for_in_progress_demo(tmp_path: Path) -> None:
    url = _db_url(tmp_path)
    db_path = tmp_path / "hotel-demo.db"
    db_path.write_bytes(b"partial-demo")
    marker = Path(f"{db_path}.h44-demo.json")
    marker.write_text(json.dumps({
        "dataset_id": DATASET_ID,
        "seed_revision": "hotel-demo-seed-v1",
        "status": "in_progress",
        "ids": {key: [] for key in {
            "users", "hotels", "aliases", "snapshots", "stay_offers", "watchlists", "tracked_offers",
            "alert_rules", "alert_events", "deliveries", "notification_states",
            "provider_runs", "latency_aggregates",
        }},
    }), encoding="utf-8")
    with pytest.raises(DemoSeedConfigurationError, match="abort_requires_confirmation"):
        run_abort(url, confirm_demo_db=False)
    report = run_abort(url, confirm_demo_db=True)
    assert report["operation"] == "abort"
    assert not db_path.exists()
    assert not marker.exists()


def test_reset_rejects_marked_db_not_at_alembic_head(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    url = _db_url(tmp_path)
    run_seed(url)
    monkeypatch.setattr("scripts.hotel_demo_seed.ScriptDirectory.from_config", lambda _config: type("Scripts", (), {"get_heads": lambda self: ["not-current"]})())
    with pytest.raises(DemoSeedConfigurationError, match="schema_not_at_head"):
        run_reset(url, confirm_demo_db=True)


def test_reset_requires_explicit_confirmation(tmp_path: Path) -> None:
    url = _db_url(tmp_path)
    run_seed(url)
    with pytest.raises(DemoSeedConfigurationError, match="confirmation"):
        run_reset(url, confirm_demo_db=False)


def test_reset_removes_only_demo_scope_and_preserves_sentinel(tmp_path: Path) -> None:
    url = _db_url(tmp_path)
    run_seed(url)
    engine = create_engine(url, connect_args={"check_same_thread": False})
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with factory() as db:
        sentinel = HotelProperty(
            canonical_name="Outside scope sentinel",
            normalized_name="outside scope sentinel",
            city="Valencia",
            normalized_city="valencia",
            country_code="ES",
        )
        db.add(sentinel)
        db.commit()
        sentinel_id = sentinel.id

    report = run_reset(url, confirm_demo_db=True)
    assert report["result"] == "passed"
    assert all(value == 0 for value in report["rows_by_table"].values())
    assert not (Path(f"{tmp_path / 'hotel-demo.db'}.h44-demo.json")).exists()
    with factory() as db:
        assert db.get(HotelProperty, sentinel_id) is not None
        assert db.scalar(select(HotelProperty.canonical_name).where(HotelProperty.id == sentinel_id)) == "Outside scope sentinel"
        assert db.scalar(select(HotelStayOffer.id)) is None
    engine.dispose()


def test_reset_rejects_marker_scope_drift(tmp_path: Path) -> None:
    url = _db_url(tmp_path)
    run_seed(url)
    engine = create_engine(url, connect_args={"check_same_thread": False})
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with factory() as db:
        db.add(HotelProperty(
            canonical_name="Outside scope sentinel",
            normalized_name="outside scope sentinel",
            city="Valencia",
            normalized_city="valencia",
            country_code="ES",
        ))
        db.commit()
    engine.dispose()
    marker = Path(f"{tmp_path / 'hotel-demo.db'}.h44-demo.json")
    payload = json.loads(marker.read_text(encoding="utf-8"))
    payload["ids"]["hotels"] = payload["ids"]["hotels"][:-1]
    marker.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(DemoSeedConfigurationError, match="scope_changed"):
        run_reset(url, confirm_demo_db=True)


def test_reset_blocks_external_comparison_set_without_deleting_scope(tmp_path: Path) -> None:
    url = _db_url(tmp_path)
    run_seed(url)
    engine = create_engine(url, connect_args={"check_same_thread": False})
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    marker = Path(f"{tmp_path / 'hotel-demo.db'}.h44-demo.json")
    payload = json.loads(marker.read_text(encoding="utf-8"))
    demo_hotel_id = payload["ids"]["hotels"][0]
    with factory() as db:
        outsider = User(
            email="external-owner@viru.local",
            password_hash="test-only",
            is_verified=True,
            is_admin=False,
            locale="es",
            timezone="Europe/Madrid",
        )
        db.add(outsider)
        db.flush()
        outsider_id = outsider.id
        db.add(HotelCompSet(user_id=outsider_id, name="External comparison", anchor_hotel_id=demo_hotel_id))
        db.commit()
    with pytest.raises(DemoSeedConfigurationError, match="external_refs"):
        run_reset(url, confirm_demo_db=True)
    with factory() as db:
        assert db.get(User, outsider_id) is not None
        assert db.get(HotelProperty, demo_hotel_id) is not None
    engine.dispose()


def test_cli_blocks_reset_without_confirmation(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    url = _db_url(tmp_path)
    assert main(["seed", "--db-url", url]) == 0
    assert main(["reset", "--db-url", url]) == 2
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["result"] == "blocked"
