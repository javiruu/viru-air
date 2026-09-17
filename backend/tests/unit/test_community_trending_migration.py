from app.infrastructure.db.models import Base

def test_community_trending_snapshot_schema_invariant() -> None:
    assert 'community_trending_snapshot' in Base.metadata.tables, 'Table community_trending_snapshot must exist in canonical schema metadata'
    table = Base.metadata.tables['community_trending_snapshot']
    assert len(table.columns) > 0
