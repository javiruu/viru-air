from app.infrastructure.db.models import Base

def test_hotel_tracked_offer_lifecycle_event_schema_invariant() -> None:
    assert 'hotel_tracked_offer_lifecycle_event' in Base.metadata.tables, 'Table hotel_tracked_offer_lifecycle_event must exist in canonical schema metadata'
    table = Base.metadata.tables['hotel_tracked_offer_lifecycle_event']
    assert len(table.columns) > 0
