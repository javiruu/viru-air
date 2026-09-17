from app.infrastructure.db.models import Base

def test_community_price_report_schema_invariant() -> None:
    assert 'community_price_report' in Base.metadata.tables, 'Table community_price_report must exist in canonical schema metadata'
    table = Base.metadata.tables['community_price_report']
    assert len(table.columns) > 0
