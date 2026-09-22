from pathlib import Path
from app.infrastructure.db.models import Base

REPO_ROOT = Path(__file__).resolve().parents[3]

def test_canonical_supabase_baseline_exists() -> None:
    migration_file = REPO_ROOT / 'supabase' / 'migrations' / '20260912000001_canonical_baseline_schema.sql'
    assert migration_file.exists(), 'Canonical Supabase baseline migration file is missing'
    sql = migration_file.read_text(encoding='utf-8')
    assert 'CREATE TABLE' in sql

def test_all_sqlalchemy_tables_represented_in_metadata() -> None:
    assert len(Base.metadata.tables) == 61, f'Expected 61 application tables, found {len(Base.metadata.tables)}'

def test_alembic_retired_from_runtime_dependencies() -> None:
    pyproject = (REPO_ROOT / 'backend' / 'pyproject.toml').read_text(encoding='utf-8')
    assert 'alembic' not in pyproject, 'Alembic must not be present in backend dependencies'
