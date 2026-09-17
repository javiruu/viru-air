from app.infrastructure.db.models import Base

def test_hotel_provider_latency_aggregate_schema_invariant() -> None:
    assert 'hotel_provider_latency_aggregate' in Base.metadata.tables, 'Table hotel_provider_latency_aggregate must exist in canonical schema metadata'
    table = Base.metadata.tables['hotel_provider_latency_aggregate']
    assert len(table.columns) > 0
