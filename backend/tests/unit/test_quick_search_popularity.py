import datetime as dt

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models import Base, QuickSearchPopularityCounter
from app.services.quick_search_popularity import QuickSearchPopularitySignal, record_quick_search_popularity


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = testing_session_local()
    session._test_engine = engine  # type: ignore[attr-defined]
    return session


def test_record_quick_search_popularity_increments_anonymous_route_counter() -> None:
    db = _db()
    try:
        signal = QuickSearchPopularitySignal(
            origin_iata=" lei ",
            destination_iata="dub",
            travel_date=dt.date(2026, 12, 14),
            currency="eur",
            searched_at=dt.datetime(2026, 7, 11, 10, 0),
        )

        first = record_quick_search_popularity(db, signal)
        second = record_quick_search_popularity(
            db,
            QuickSearchPopularitySignal(
                origin_iata="LEI",
                destination_iata="DUB",
                travel_date=dt.date(2026, 12, 14),
                currency="EUR",
                searched_at=dt.datetime(2026, 7, 11, 11, 30),
            ),
        )

        rows = db.query(QuickSearchPopularityCounter).all()
        assert len(rows) == 1
        assert first.id == second.id
        assert second.origin_iata == "LEI"
        assert second.destination_iata == "DUB"
        assert second.currency == "EUR"
        assert second.search_count == 2
        assert second.first_searched_at == dt.datetime(2026, 7, 11, 10, 0)
        assert second.last_searched_at == dt.datetime(2026, 7, 11, 11, 30)
    finally:
        db.close()
        db._test_engine.dispose()  # type: ignore[attr-defined]


def test_quick_search_popularity_counter_is_cross_user_and_anonymous() -> None:
    column_names = {column.name for column in QuickSearchPopularityCounter.__table__.columns}
    foreign_key_targets = {
        f"{foreign_key.column.table.name}.{foreign_key.column.name}"
        for foreign_key in QuickSearchPopularityCounter.__table__.foreign_keys
    }

    assert "user_id" not in column_names
    assert not any(target.startswith("users.") for target in foreign_key_targets)
