from app.infrastructure.db.models import Base

def test_hotel_provider_run_schema_invariant() -> None:
    assert 'hotel_provider_run' in Base.metadata.tables, 'Table hotel_provider_run must exist in canonical schema metadata'
    table = Base.metadata.tables['hotel_provider_run']
    assert len(table.columns) > 0
