from app.infrastructure.db.models import Base

def test_hotel_provider_alias_schema_invariant() -> None:
    assert 'hotel_provider_alias' in Base.metadata.tables, 'Table hotel_provider_alias must exist in canonical schema metadata'
    table = Base.metadata.tables['hotel_provider_alias']
    assert len(table.columns) > 0
