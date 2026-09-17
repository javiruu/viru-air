from app.infrastructure.db.models import Base

def test_hotel_stay_offer_schema_invariant() -> None:
    assert 'hotel_stay_offer' in Base.metadata.tables, 'Table hotel_stay_offer must exist in canonical schema metadata'
    table = Base.metadata.tables['hotel_stay_offer']
    assert len(table.columns) > 0
