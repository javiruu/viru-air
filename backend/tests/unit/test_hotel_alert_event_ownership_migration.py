from app.infrastructure.db.models import Base

def test_hotel_alert_event_schema_invariant() -> None:
    assert 'hotel_alert_event' in Base.metadata.tables, 'Table hotel_alert_event must exist in canonical schema metadata'
    table = Base.metadata.tables['hotel_alert_event']
    assert len(table.columns) > 0
