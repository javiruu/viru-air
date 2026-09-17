from app.infrastructure.db.models import Base

def test_flight_operational_snapshot_schema_invariant() -> None:
    assert 'flight_operational_snapshot' in Base.metadata.tables, 'Table flight_operational_snapshot must exist in canonical schema metadata'
    table = Base.metadata.tables['flight_operational_snapshot']
    assert len(table.columns) > 0
